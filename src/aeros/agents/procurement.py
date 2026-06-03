"""Agentic Procurement Agent — multi-step reasoning with TOON-formatted tool calls.

Inspired by memo.sbs MemoAgent architecture:
1. Gather user context (inventory, RFx state, vendors)
2. Deterministic intent detection (no LLM for common patterns)
3. Agentic loop: select tools → execute → respond → check → continue
4. TOON format for tool catalogs (40% token savings vs JSON)
"""

import contextlib
import json
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlmodel import Session, select
from toon_format import encode as toon_encode

from aeros.agents.base import AgentContext, AgentResult, BaseAgent
from aeros.agents.executor import execute_tool
from aeros.agents.tools import (
    ToolResult,
    filter_tools_by_keywords,
    get_tools_for_role,
    tools_to_toon,
)
from aeros.ai.base import ChatMessage
from aeros.ai.labels import step_label
from aeros.ai.ui_blocks import build_blocks_from_results
from aeros.models.user_defaults import UserDefaults

logger = structlog.get_logger()

AGENT_CONFIG = {
    "max_llm_calls": 6,
    "max_iterations": 3,
    "llm_calls_per_iteration": 2,
}

STAGE_TOKEN_LIMITS = {
    "tool_selection": {"max_output": 8192, "input_pct": 0.40},
    "greeting": {"max_output": 4096, "input_pct": 0.25},
    "response": {"max_output": 16384, "input_pct": 0.50},
}

CONTEXT_LIMITS = {
    "skus": 30,
    "vendors": 20,
    "rfx": 10,
    "history_messages": 8,
    "history_char_limit": 150,
}

_INJECTION_RE = re.compile(
    r"(?:ignore\s+(?:previous|above|all)\s+instructions|"
    r"you\s+are\s+now|act\s+as|system\s*:|"
    r"forget\s+(?:everything|your\s+instructions)|"
    r"new\s+instructions\s*:)",
    re.IGNORECASE,
)


def _sanitize_for_prompt(text: str) -> str:
    return _INJECTION_RE.sub("[redacted]", text)


@dataclass
class PipelineStep:
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "pending"
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


# ============================================
# DETERMINISTIC INTENT DETECTION
# ============================================

_QTY = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"twenty|thirty|forty|fifty|hundred|thousand)"
)
_UNIT = (
    r"(?:kg|kgs|g|gm|gram|grams|ltr|ltrs|litre|litres|liter|liters|ml|"
    r"pcs|pieces|dozen|doz|units?|ton|tons|tonne|quintal|quintals|"
    r"packet|packets|box|boxes|carton|cartons|bag|bags|sack|sacks|"
    r"bottle|bottles|can|cans|pair|pairs|set|sets|roll|rolls)"
)

PROCUREMENT_PATTERNS = [
    # Bare quantity + unit (most natural: "Ashirwad aata 5kg 10 pcs")
    (rf"{_QTY}\s*{_UNIT}\b", "create_rfx"),
    # Trigger word + quantity
    (
        rf"(?:i need|we need|mujhe|chahiye|order|kharid|mangwao|bhejdo).*{_QTY}\s*{_UNIT}",
        "create_rfx",
    ),
    # Reverse: quantity before chahiye
    (rf"{_QTY}\s*{_UNIT}.*(?:chahiye|chaiye|mangwao)", "create_rfx"),
    # Trigger word + known items (no quantity needed)
    (
        r"(?:i need|we need|mujhe|chahiye|buy|purchase|procure).*"
        r"(?:rice|wheat|dal|atta|aata|oil|sugar|flour|vegetable|"
        r"onion|tomato|potato|salt|masala|milk|ghee|paneer|curd)",
        "create_rfx",
    ),
    # Dispatch
    (
        r"\b(?:dispatch|send\s+(?:out|to|this|rfx)|bhejo|bhejdo)\b",
        "dispatch_rfx",
    ),
    # Cancel
    (r"\b(?:cancel|withdraw|abort|band karo)\b.*\b(?:rfx?|order)", "cancel_rfx"),
    # Evaluate
    (
        r"\b(?:compare|evaluate|best price|sabse sasta|cheapest|"
        r"lowest|who\s+(?:gave|quoted|offered))\b",
        "evaluate_offers",
    ),
    # Award
    (r"\b(?:award|finalize|select vendor|accept quote)\b", "award_rfx"),
    # Decline
    (
        r"\b(?:decline|reject|can'?t supply|nahi de sakte|"
        r"out of stock|not available)\b",
        "decline_rfx",
    ),
    # Quote
    (rf"\b(?:quote|bid|submit price|daam|rate)\b.*{_QTY}", "submit_quote"),
    # List RFx
    (
        r"\b(?:show|list|mere|my|kya|status)\b.*\b(?:rfx?|orders?|requests?)\b",
        "list_rfx",
    ),
    # List vendors
    (r"\b(?:show|list)\b.*\b(?:vendors?|suppliers?)", "list_vendors"),
    # Summary (only when it's the primary intent, not embedded in other context)
    (r"\b(?:summary|overview|dashboard)\b", "daily_summary"),
    (r"(?:^|\.\s*)(?:aaj|today)(?:\s+(?:kya|what)|\?)", "daily_summary"),
]

_GREETING_RE = re.compile(
    r"^\s*(?:hi|hello|hey|namaste|good\s+(?:morning|afternoon|evening)|howdy|sup)\b",
    re.IGNORECASE,
)


def detect_intent(message: str) -> list[str]:
    msg_lower = message.lower()
    if _GREETING_RE.match(msg_lower):
        return ["__greeting__"]
    intents: list[str] = []
    seen: set[str] = set()
    for pattern, tool_name in PROCUREMENT_PATTERNS:
        if tool_name not in seen and re.search(pattern, msg_lower):
            intents.append(tool_name)
            seen.add(tool_name)
    return intents


# Read-only tools we can run straight from deterministic intent detection when
# the LLM selection step returns nothing. Some chat models are unreliable at
# emitting tool calls for phrasings like "evaluate the offers for RFx #1" — they
# sometimes reply "please share the offers" instead of calling the tool. These
# are all non-destructive and need at most an rfx_id we can resolve from text.
_FALLBACK_TOOLS = {"evaluate_offers", "list_vendors", "list_rfx", "daily_summary"}
_RFX_ID_RE = re.compile(r"(?:rfx|rfq)\s*#?\s*(\d+)|#\s*(\d+)", re.IGNORECASE)


def _resolve_rfx_id(message: str, ctx: AgentContext) -> int | None:
    """Find the RFx an intent refers to: explicit number, ctx, else most recent."""
    m = _RFX_ID_RE.search(message)
    if m:
        return int(m.group(1) or m.group(2))
    if ctx.rfx_id:
        return ctx.rfx_id
    from aeros.services import rfx_service

    try:
        rfx_list = rfx_service.list_rfx_for_buyer(ctx.session, ctx.caller.user_id)
    except Exception:
        return None
    if not rfx_list:
        return None
    with_offers = [r for r in rfx_list if r.get("vendor_count")]
    chosen = with_offers[0] if with_offers else rfx_list[0]
    return chosen.get("id")


# Read-only RFx tools that need an rfx_id. If the model selects one but forgets
# the id (a common LLM slip), we resolve it from the message rather than letting
# the tool hard-fail with "missing RFx ID".
_RFX_ID_TOOLS = {"evaluate_offers", "get_rfx_details", "get_vendor_suggestions"}

# Mutating tools that must run at most once per user turn. The agentic loop
# re-runs tool *selection* on the same message each iteration, so without this
# guard a single "create an RFx" request fires create_rfx on every iteration
# (max_iterations=3 → three duplicate RFx). We drop any of these that already
# succeeded earlier in the same turn.
_ONESHOT_TOOLS = {"create_rfx", "dispatch_rfx"}


def _resolve_dispatch_rfx_id(message: str, ctx: AgentContext) -> int | None:
    """Resolve which RFx to dispatch: explicit #, then context, then newest draft."""
    m = _RFX_ID_RE.search(message)
    if m:
        return int(m.group(1) or m.group(2))
    if ctx.rfx_id:
        return ctx.rfx_id
    from aeros.services import rfx_service

    try:
        rfx_list = rfx_service.list_rfx_for_buyer(ctx.session, ctx.caller.user_id)
    except Exception:
        return None
    drafting = [r for r in rfx_list if r.get("status") == "drafting"]
    if drafting:
        return drafting[0].get("id")
    return None


def _backfill_rfx_id(
    selected: list[tuple[str, dict[str, Any]]], message: str, ctx: AgentContext
) -> list[tuple[str, dict[str, Any]]]:
    """Fill in a missing rfx_id for read-only RFx tools the model under-specified."""
    patched: list[tuple[str, dict[str, Any]]] = []
    for tool_name, params in selected:
        if tool_name in _RFX_ID_TOOLS and not params.get("rfx_id"):
            rid = _resolve_rfx_id(message, ctx)
            if rid is not None:
                params = {**params, "rfx_id": rid}
        elif tool_name == "dispatch_rfx" and not params.get("rfx_id"):
            rid = _resolve_dispatch_rfx_id(message, ctx)
            if rid is not None:
                params = {**params, "rfx_id": rid}
        patched.append((tool_name, params))
    return patched


# Pull "<qty> <unit> [of] <item name>" clauses out of a free-text request so we
# can attach real, SKU-matched line items to a drafted RFx. The model creates the
# RFx shell but routinely skips add_line_items, leaving an empty draft — we fill
# it in deterministically instead.
_ITEM_CLAUSE_RE = re.compile(
    rf"(\d+(?:\.\d+)?)\s*({_UNIT})\b\s*(?:of\s+)?([a-z][a-z ]*)",
    re.IGNORECASE,
)
# Words that end an item name (connectors and scheduling tails).
_ITEM_TAIL_RE = re.compile(
    r"\b(?:and|with|plus|by|before|after|delivered|deliver|delivery|due|within|"
    r"tomorrow|today|tonight|morning|evening|afternoon|asap|please|create|raise|order)\b.*$",
    re.IGNORECASE,
)


def _find_sku(session: Session, org_id: int, name: str) -> Any:
    from aeros.services import inventory_service

    name = name.strip()
    candidates = [name]
    if name.endswith("es"):
        candidates.append(name[:-2])
    if name.endswith("s"):
        candidates.append(name[:-1])
    tokens = name.split()
    if len(tokens) > 1:
        candidates.append(tokens[-1])  # e.g. "full cream milk" -> "milk"
    for query in candidates:
        if not query:
            continue
        matches = inventory_service.search_skus(session, org_id, query)
        if matches:
            return matches[0]
    return None


def _resolve_line_items(message: str, session: Session, org_id: int) -> list[dict[str, Any]]:
    """Resolve '200kg tomatoes, 300 litres of milk' into SKU-backed line items."""
    items: list[dict[str, Any]] = []
    seen: set[int] = set()
    for match in _ITEM_CLAUSE_RE.finditer(message):
        qty = float(match.group(1))
        unit = match.group(2).lower()
        name = _ITEM_TAIL_RE.sub("", match.group(3)).strip()
        if not name:
            continue
        sku = _find_sku(session, org_id, name)
        if not sku or sku.id in seen:
            continue
        seen.add(sku.id)
        items.append(
            {
                "sku_id": sku.id,
                "qty": qty,
                "unit_override": unit,
                "target_price": sku.last_price,
                "sku_name": sku.name,
            }
        )
    return items


# Explicit "add to this request" cues — when the buyer is already viewing an
# RFx, these mean "append a line item here", not "start a new request".
_ADD_CUE_RE = re.compile(
    r"\b(?:add|include|append|attach|jodo|jod do|daal do|daaldo|daldo|add\s*kar)\b",
    re.IGNORECASE,
)
# Explicit "start a fresh request" cues — these override the sticky-draft
# behaviour and force a brand-new RFx even when one is already active.
_NEW_RFX_CUE_RE = re.compile(
    r"\b(?:new|another|separate|different|fresh)\s+"
    r"(?:rfx|rfq|request|requisition|order|po|procurement)\b"
    r"|\bstart\s+over\b|\bstart\s+(?:a\s+)?new\b|\bnaya\s+(?:order|request)\b",
    re.IGNORECASE,
)
# "<name> <qty><unit>" — name BEFORE quantity ("bisleri 1L 100 pcs",
# "ashirwad aata 10 pcs"). Complements _ITEM_CLAUSE_RE which expects the
# quantity first.
_NAME_QTY_RE = re.compile(
    rf"([a-z][a-z0-9 ]*?)\s+(\d+(?:\.\d+)?)\s*({_UNIT})\b",
    re.IGNORECASE,
)
# A bare SKU code, optionally followed by a quantity ("PF001 qty 10",
# "add PF001 x 10").
_CODE_QTY_RE = re.compile(
    r"\b([a-z]{1,5}\d{2,6})\b(?:[^0-9]{0,18}?(\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)


def _parse_item_refs(message: str) -> list[dict[str, Any]]:
    """Extract ``{sku_id: <ref>, qty, unit_override}`` from free text.

    ``sku_id`` is left as the raw name/code the user typed; the executor's
    ``resolve_sku_ref`` turns it into a real SKU (or surfaces candidates).
    """
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(ref: str, qty: float, unit: str | None) -> None:
        key = ref.lower()
        if not ref or key in seen:
            return
        seen.add(key)
        items.append({"sku_id": ref, "qty": qty, "unit_override": unit})

    # qty-first: "10 pcs ashirwad aata"
    for m in _ITEM_CLAUSE_RE.finditer(message):
        name = _ITEM_TAIL_RE.sub("", m.group(3)).strip()
        if name:
            add(name, float(m.group(1)), m.group(2).lower())

    # name-first: "bisleri 1L 100 pcs"
    for m in _NAME_QTY_RE.finditer(message):
        name = _ITEM_TAIL_RE.sub("", m.group(1)).strip()
        # Drop a leading add-cue verb caught by the greedy name group.
        name = _ADD_CUE_RE.sub("", name).strip()
        if name and not name.isdigit():
            add(name, float(m.group(2)), m.group(3).lower())

    # explicit SKU codes: "PF001 qty 10"
    for m in _CODE_QTY_RE.finditer(message):
        code, qty = m.group(1), m.group(2)
        add(code, float(qty) if qty else 1.0, None)

    # Loose single-item fallback for phrasings the structured patterns miss:
    # unit-less quantities ("60 bananas") and "quantity/qty N" ("milk qty 5").
    if not items:
        loose = _loose_single_item(message)
        if loose:
            add(*loose)

    return items


# Filler stripped from a loose single-item phrase to isolate the item name.
_FILLER_RE = re.compile(
    r"\b(?:add|include|append|attach|line\s*items?|item|to|this|the|that|"
    r"rfx|rfq|request|requisition|order|po|with|of|a|an|please|qty|quantity|"
    r"jodo|daal\s*do|daaldo)\b",
    re.IGNORECASE,
)
_QTY_HINT_RE = re.compile(r"(?:qty|quantity|x|×|\*)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)  # noqa: RUF001
_NUM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\b")


def _loose_single_item(message: str) -> tuple[str, float, None] | None:
    """Best-effort '<item> ... <qty>' parse for a single add request.

    Handles "add 60 bananas", "add line item milk with quantity 5",
    "add zzznope qty 3" — anything with one clear quantity and a leftover
    item phrase. Returns ``(ref, qty, None)`` or None when too ambiguous.
    """
    qty_match = _QTY_HINT_RE.search(message) or _NUM_RE.search(message)
    if not qty_match:
        return None
    qty = float(qty_match.group(1))
    # Drop the quantity token and any unit immediately after it, then filler.
    without_qty = re.sub(
        rf"\b{re.escape(qty_match.group(1))}\s*(?:{_UNIT})?\b", " ", message, count=1, flags=re.I
    )
    name = _FILLER_RE.sub(" ", without_qty)
    name = re.sub(r"[^a-z0-9 ]", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) < 2:
        return None
    return name, qty, None


def _derive_rfx_title(items: list[dict[str, Any]]) -> str:
    names = [it["sku_name"] for it in items][:3]
    if not names:
        return "New procurement request"
    head = ", ".join(names)
    suffix = "" if len(items) <= 3 else f" +{len(items) - 3} more"
    return f"Procurement: {head}{suffix}"


def _active_draft_id(ctx: AgentContext) -> int | None:
    """Return ``ctx.rfx_id`` only when it's an editable draft.

    The chat carries the most recent draft's id across turns so follow-up
    items fold into it. But once that RFx is dispatched (or otherwise past
    drafting), the next item must start a *fresh* request — so we stop
    treating it as the active draft. Best-effort: if there's no usable
    session (unit tests), trust ``ctx.rfx_id`` as-is.
    """
    rid: int | None = getattr(ctx, "rfx_id", None)
    if not rid:
        return None
    try:
        from aeros.models.rfx import RFxRun, RFxStatus

        rfx = ctx.session.get(RFxRun, rid)
    except Exception:
        return rid
    if rfx is None:
        return None
    return rid if rfx.status == RFxStatus.DRAFTING else None


def _active_rfx_add_calls(
    message: str, ctx: AgentContext, detected: Sequence[str] = ()
) -> list[tuple[str, dict[str, Any]]]:
    """Deterministic add_line_items when the buyer is working inside a draft.

    Buyers expect a single draft to keep growing until they clear the chat or
    explicitly start a new request, so any procurement-intent message folds
    into the active draft rather than spawning a new RFx. We append when the
    message either carries an explicit add cue OR reads as a procurement need
    (``create_rfx`` in ``detected``). We bail when:

    * there's no active draft (``_active_draft_id`` — covers post-dispatch),
    * the buyer explicitly asks for a new/separate request, or
    * no line items can be parsed out.

    The chat model is an unreliable tool-caller — it frequently narrates
    "added!" without emitting add_line_items, or spawns a brand-new RFx
    instead of appending — so we build the call ourselves for predictability.
    Ambiguous/unknown refs are still resolved (and surfaced) by the executor.
    """
    draft_id = _active_draft_id(ctx)
    if not draft_id or _NEW_RFX_CUE_RE.search(message):
        return []
    append_intent = bool(_ADD_CUE_RE.search(message)) or ("create_rfx" in detected)
    if not append_intent:
        return []
    items = _parse_item_refs(message)
    if not items:
        return []
    return [("add_line_items", {"rfx_id": draft_id, "items": items})]


def _deterministic_tool_calls(
    detected: list[str], message: str, ctx: AgentContext
) -> list[tuple[str, dict[str, Any]]]:
    """Build tool calls from detected intent when the LLM picks nothing."""
    calls: list[tuple[str, dict[str, Any]]] = []
    for tool_name in detected:
        if tool_name == "create_rfx":
            # Build a titled create from the request itself; line items are
            # attached deterministically after execution.
            items = _resolve_line_items(message, ctx.session, ctx.caller.org_id or 0)
            calls.append((tool_name, {"title": _derive_rfx_title(items)}))
            continue
        if tool_name == "dispatch_rfx":
            rid = _resolve_dispatch_rfx_id(message, ctx)
            if rid is not None:
                calls.append((tool_name, {"rfx_id": rid}))
            continue
        if tool_name not in _FALLBACK_TOOLS:
            continue
        if tool_name == "evaluate_offers":
            rid = _resolve_rfx_id(message, ctx)
            if rid is None:
                continue
            calls.append((tool_name, {"rfx_id": rid}))
        else:
            calls.append((tool_name, {}))
    return calls


# ============================================
# CONTEXT BUILDER
# ============================================


def _build_user_context(session: Session, caller: Any, message: str = "") -> str:
    from aeros.services import inventory_service, rfx_service, vendor_service

    org_id = caller.org_id or 0
    parts = []

    skus = inventory_service.list_skus(session, org_id)
    if skus:
        sku_data = [
            {"id": s.id, "code": s.code, "name": s.name, "unit": s.unit, "price": s.last_price}
            for s in skus[: CONTEXT_LIMITS["skus"]]
        ]
        parts.append(f"<inventory>\n{toon_encode(sku_data)}\n</inventory>")

    vendors = vendor_service.list_vendors(session, org_id)
    if vendors:
        v_data = [
            {
                "id": v.id,
                "name": v.name,
                "categories": v.category_ids_csv or "",
                "score": v.performance_score,
                "channel": (
                    "portal" if v.vendor_user_id else "email" if v.primary_email else "telegram"
                ),
            }
            for v in vendors[: CONTEXT_LIMITS["vendors"]]
        ]
        parts.append(f"<vendors>\n{toon_encode(v_data)}\n</vendors>")

    rfx_list = rfx_service.list_rfx_for_buyer(session, caller.user_id)
    if rfx_list:
        rfx_data = [
            {
                "id": r["id"],
                "title": r["title"],
                "status": r["status"],
                "vendors": r.get("vendor_count", 0),
            }
            for r in rfx_list[: CONTEXT_LIMITS["rfx"]]
        ]
        parts.append(f"<active_rfx>\n{toon_encode(rfx_data)}\n</active_rfx>")

    defaults = session.exec(
        select(UserDefaults).where(UserDefaults.user_id == caller.user_id)
    ).first()
    if defaults:
        d = {
            "payment": defaults.payment_terms_default,
            "delivery": defaults.delivery_terms_default,
            "currency": defaults.currency_default,
        }
        parts.append(f"<defaults>\n{toon_encode(d)}\n</defaults>")

    return "\n\n".join(parts) if parts else "No data yet."


def _build_vendor_context(session: Session, caller: Any, rfx_id: int | None) -> str:
    if not rfx_id:
        return "No RFx context."

    from aeros.models.rfx import RFxLineItem, RFxRun
    from aeros.models.sku import SKU

    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        return "RFx not found."

    items = list(session.exec(select(RFxLineItem).where(RFxLineItem.rfx_id == rfx_id)).all())
    item_data = []
    for li in items:
        sku = session.get(SKU, li.sku_id)
        item_data.append(
            {
                "id": li.id,
                "item": sku.name if sku else f"SKU#{li.sku_id}",
                "qty": li.qty,
                "unit": li.unit_override or (sku.unit if sku else ""),
                "target": li.target_price,
            }
        )

    rfx_info = {
        "title": rfx.title,
        "status": str(rfx.status),
        "deadline": str(rfx.response_deadline) if rfx.response_deadline else "none",
        "payment": rfx.payment_terms_for_this_rfx,
        "delivery": rfx.delivery_terms_for_this_rfx,
        "currency": rfx.currency_for_this_rfx,
    }

    parts = [
        f"RFx Details:\n{toon_encode(rfx_info)}",
        f"Line Items:\n{toon_encode(item_data)}",
    ]
    return "\n\n".join(parts)


# ============================================
# AGENTIC PROCUREMENT AGENT
# ============================================

TOOL_SELECTION_PROMPT = """\
You are AEROS procurement AI. Select the best tool(s) for this request.

Current time: {now}

<user_data>
{context}
</user_data>

Chat History:
{history}

User's Message: "{message}"

{intent_hints}

Available Tools (TOON):
{tools_toon}

RULES:
1. Greetings (hi, hello, hey) → Return EMPTY {{}}
2. Procurement need ("I need X") → create_rfx with title; add_line_items if quantities given
3. "send/dispatch" → dispatch_rfx
4. "compare/evaluate" → evaluate_offers
5. Match item names to <inventory> SKUs — use exact IDs
6. Multiple actions → multiple tools in one array
7. ALWAYS reference user's existing IDs from <user_data>
8. When "Current RFx ID" is given in hints, use it as rfx_id param
9. Support English, Hindi, Hinglish

Return ONLY a JSON array — no wrapper keys, no "thoughts", no explanation:
[{{"tool": "name", "params": {{...}}}}]
Or {{}} for greetings. Do NOT wrap in {{"tool_calls": ...}} or {{"thoughts": ...}}.
"""

RESPONSE_PROMPT = """\
You are AEROS procurement AI. Respond based ONLY on these tool results.

<tool_results>
{results_toon}
</tool_results>

User: "{message}"
History: {history}

RULES:
1. Be CONCISE — 1-2 sentences for confirmations. Never explain what you did.
2. On tool failure, say what went wrong in one line.
3. RFx created → mention ID + one next step.
4. SAME language as user (English/Hindi/Hinglish).
5. NEVER draw tables, lists, or repeat the raw rows — the UI renders the
   structured results below your text. Give a one-line takeaway instead
   (e.g. which vendor is cheapest, how many vendors quoted).
6. Suggest ONE logical next action, not a list.
7. Never start with "Sure!" / "Of course!" / "Great news!". Be direct.
8. Max 3 sentences. Never reply with an empty message.
"""


class ProcurementAgent(BaseAgent):
    name = "procurement"

    async def run(self, ctx: AgentContext, user_input: str) -> AgentResult:
        start_time = time.monotonic()

        async def emit(name: str, tool: str | None = None) -> None:
            """Tell a streaming listener what the agent is doing right now."""
            if ctx.on_step is None:
                return
            with contextlib.suppress(Exception):
                await ctx.on_step({"label": step_label(name, tool=tool)})

        steps: list[PipelineStep] = []
        llm_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0
        all_tool_results: list[ToolResult] = []
        all_tools_called: list[str] = []

        safe_input = _sanitize_for_prompt(user_input)
        role = ctx.caller.role.value if hasattr(ctx.caller.role, "value") else str(ctx.caller.role)
        history = ctx.metadata.get("history", [])
        climit = CONTEXT_LIMITS["history_char_limit"]
        history_str = (
            "\n".join(
                f"- {h['role'].title()}: {_sanitize_for_prompt(h['content'][:climit])}"
                for h in history[-CONTEXT_LIMITS["history_messages"] :]
            )
            if history
            else "(none)"
        )

        # Step 1: Gather context
        await emit("context")
        step = PipelineStep(name="context", start_time=time.monotonic())
        try:
            if role == "vendor":
                context_str = _build_vendor_context(ctx.session, ctx.caller, ctx.rfx_id)
            else:
                context_str = _build_user_context(ctx.session, ctx.caller, safe_input)
        except Exception as e:
            logger.warning("agent.context.error", error=str(e))
            context_str = "Context unavailable."
        step.end_time = time.monotonic()
        step.status = "success"
        steps.append(step)

        # Step 2: Deterministic intent detection
        detected = detect_intent(safe_input)

        # Fast-path: pure greeting — skip tool selection LLM call entirely
        if detected == ["__greeting__"]:
            await emit("greeting")
            step = PipelineStep(name="greeting", start_time=time.monotonic())
            try:
                greeting_resp = await ctx.chat_provider.chat(
                    [
                        ChatMessage(
                            role="system",
                            content=(
                                "You are AEROS, a procurement AI. "
                                "Keep greetings under 20 words. Be warm but direct. "
                                "Respond in the user's language."
                            ),
                        ),
                        *[
                            ChatMessage(role=h["role"], content=h["content"][:100])
                            for h in history[-4:]
                        ],
                        ChatMessage(role="user", content=safe_input),
                    ],
                    temperature=0.8,
                    max_tokens=int(STAGE_TOKEN_LIMITS["greeting"]["max_output"]),
                )
                llm_calls += 1
                total_input_tokens += greeting_resp.input_tokens
                total_output_tokens += greeting_resp.output_tokens
                final_response = greeting_resp.content
            except Exception:
                final_response = "Hello! How can I help with your procurement today?"
            step.end_time = time.monotonic()
            step.status = "success"
            steps.append(step)

            return self._build_result(
                final_response,
                all_tools_called,
                all_tool_results,
                steps,
                start_time,
                llm_calls,
                total_input_tokens,
                total_output_tokens,
            )

        intent_hints = ""
        if detected:
            intent_hints = "HINTS: " + ", ".join(detected)

        # Inject current rfx_id if available (vendor context)
        if ctx.rfx_id:
            if intent_hints:
                intent_hints += f"\nCurrent RFx ID: {ctx.rfx_id}"
            else:
                intent_hints = f"Current RFx ID: {ctx.rfx_id}"

        # Step 3: Get role-appropriate tools
        available_tools = get_tools_for_role(role)
        keyword_filtered = filter_tools_by_keywords(safe_input, available_tools)
        tools_toon = tools_to_toon(keyword_filtered)

        # When the buyer is inside an RFx and asks to add items, resolve the
        # call deterministically rather than trusting the model to emit it.
        deterministic_add = _active_rfx_add_calls(safe_input, ctx, detected)

        logger.info(
            "agent.intent.detected",
            role=role,
            detected=detected,
            active_rfx_id=ctx.rfx_id,
            deterministic_add=bool(deterministic_add),
            add_item_count=(len(deterministic_add[0][1]["items"]) if deterministic_add else 0),
            candidate_tools=[t.name for t in keyword_filtered],
        )

        # Agentic loop
        iteration = 0
        final_response = ""
        executed_oneshot: set[str] = set()

        while (
            iteration < AGENT_CONFIG["max_iterations"] and llm_calls < AGENT_CONFIG["max_llm_calls"]
        ):
            iteration += 1

            # Step 4: select tools
            await emit("select_tools")
            step = PipelineStep(name=f"select_tools_{iteration}", start_time=time.monotonic())

            # Deterministic add-to-active-RFx bypasses the LLM entirely on the
            # first iteration — the model is too unreliable at emitting
            # add_line_items with the right rfx_id and items.
            if iteration == 1 and deterministic_add:
                selected = deterministic_add
                step.end_time = time.monotonic()
                step.status = "success"
                step.details = {"source": "deterministic_add"}
                steps.append(step)
                logger.info(
                    "agent.tools.selected",
                    source="deterministic_add",
                    iteration=iteration,
                    tools=[t for t, _ in selected],
                )
            else:
                selection_prompt = TOOL_SELECTION_PROMPT.format(
                    now=datetime.now(UTC).strftime("%A, %Y-%m-%d %H:%M UTC"),
                    context=context_str,
                    history=history_str,
                    message=safe_input,
                    intent_hints=intent_hints,
                    tools_toon=tools_toon,
                )

                try:
                    selection_resp = await ctx.chat_provider.chat(
                        [ChatMessage(role="user", content=selection_prompt)],
                        temperature=0.2,
                        max_tokens=int(STAGE_TOKEN_LIMITS["tool_selection"]["max_output"]),
                        response_format={"type": "json_object"},
                    )
                    llm_calls += 1
                    total_input_tokens += selection_resp.input_tokens
                    total_output_tokens += selection_resp.output_tokens
                except Exception as e:
                    logger.error("agent.select.error", error=str(e))
                    step.end_time = time.monotonic()
                    step.status = "error"
                    steps.append(step)
                    final_response = "I had trouble understanding that. Could you rephrase?"
                    break

                step.end_time = time.monotonic()
                step.status = "success"
                step.details = {
                    "input_tokens": selection_resp.input_tokens,
                    "output_tokens": selection_resp.output_tokens,
                }
                steps.append(step)

                # Parse tool selections
                selected = _parse_tool_selections(selection_resp.content)
                selected = _backfill_rfx_id(selected, safe_input, ctx)

                # The chat model can be an unreliable tool-caller: for the same
                # "create an RFx for ..." prompt it emits the call only ~half the
                # time and sometimes truncates mid-JSON. Whenever it gives us
                # nothing usable but the deterministic detector saw a clear
                # intent, build the tool calls ourselves. This is what makes
                # create/dispatch/compare reliable.
                selection_source = "llm"
                if not selected and detected:
                    selected = _deterministic_tool_calls(detected, safe_input, ctx)
                    selection_source = "deterministic_fallback"

                # Truncated AND no intent we can act on — ask the user to simplify.
                if not selected and selection_resp.finish_reason == "length":
                    logger.warning("agent.select.truncated", iteration=iteration)
                    final_response = (
                        "There's a lot in that one. Could you break it into smaller steps so "
                        "I can get each part right?"
                    )
                    break

                logger.info(
                    "agent.tools.selected",
                    source=selection_source,
                    iteration=iteration,
                    tools=[t for t, _ in selected],
                    finish_reason=selection_resp.finish_reason,
                )

            # Drop one-shot mutating tools (e.g. create_rfx) that already ran this
            # turn so a continued loop can't duplicate them.
            if executed_oneshot:
                selected = [(t, p) for (t, p) in selected if t not in executed_oneshot]

            if not selected:
                # No tools needed — generate conversational response
                await emit("respond")
                step = PipelineStep(name=f"converse_{iteration}", start_time=time.monotonic())
                try:
                    converse_resp = await ctx.chat_provider.chat(
                        [
                            ChatMessage(
                                role="system",
                                content=(
                                    "You are AEROS, a procurement AI. "
                                    "Be concise (1-2 sentences max). "
                                    "Respond in the user's language."
                                ),
                            ),
                            *[
                                ChatMessage(role=h["role"], content=h["content"][:100])
                                for h in history[-4:]
                            ],
                            ChatMessage(role="user", content=safe_input),
                        ],
                        temperature=0.7,
                        max_tokens=int(STAGE_TOKEN_LIMITS["greeting"]["max_output"]),
                    )
                    llm_calls += 1
                    total_input_tokens += converse_resp.input_tokens
                    total_output_tokens += converse_resp.output_tokens
                    final_response = converse_resp.content
                except Exception:
                    final_response = (
                        "I can help you raise requests, find vendors, and compare quotes. "
                        "What do you need?"
                    )
                step.end_time = time.monotonic()
                step.status = "success"
                steps.append(step)
                break

            # Step 5: Execute tools
            for tool_name, _ in selected:
                await emit("execute", tool=tool_name)
            step = PipelineStep(name=f"execute_{iteration}", start_time=time.monotonic())
            iteration_results: list[ToolResult] = []
            for tool_name, params in selected:
                result = execute_tool(tool_name, params, ctx.session, ctx.caller)
                iteration_results.append(result)
                all_tool_results.append(result)
                all_tools_called.append(tool_name)
                if tool_name in _ONESHOT_TOOLS and result.success:
                    executed_oneshot.add(tool_name)
                log_fields: dict[str, Any] = {
                    "tool": tool_name,
                    "success": result.success,
                    "latency_ms": round(result.latency_ms, 1),
                    "iteration": iteration,
                }
                if not result.success:
                    log_fields["error"] = result.message
                if tool_name == "add_line_items" and isinstance(result.data, dict):
                    log_fields["added"] = result.data.get("count")
                    log_fields["needs_clarification"] = [
                        c.get("ref") for c in (result.data.get("needs_clarification") or [])
                    ]
                    log_fields["not_found"] = result.data.get("not_found")
                logger.info("agent.tool.executed", **log_fields)
            step.end_time = time.monotonic()
            step.status = "success"
            step.details = {
                "executed": len(iteration_results),
                "successful": sum(1 for r in iteration_results if r.success),
            }
            steps.append(step)

            # A freshly created RFx is just a titled shell — the model rarely
            # follows up with add_line_items. Resolve the items from the request
            # and attach them so the draft is real and renders a details table.
            self._populate_draft_line_items(ctx, safe_input, iteration_results)

            # Step 6: Generate response from results
            await emit("respond")
            step = PipelineStep(name=f"respond_{iteration}", start_time=time.monotonic())
            results_for_prompt = _format_results_for_prompt(iteration_results)

            try:
                results_toon = toon_encode(results_for_prompt)
            except Exception:
                results_toon = json.dumps(results_for_prompt, default=str)

            response_prompt = RESPONSE_PROMPT.format(
                results_toon=results_toon,
                message=safe_input,
                history=history_str,
            )

            try:
                response_resp = await ctx.chat_provider.chat(
                    [ChatMessage(role="user", content=response_prompt)],
                    temperature=0.4,
                    max_tokens=int(STAGE_TOKEN_LIMITS["response"]["max_output"]),
                )
                llm_calls += 1
                total_input_tokens += response_resp.input_tokens
                total_output_tokens += response_resp.output_tokens
                final_response = response_resp.content
            except Exception as e:
                logger.error("agent.respond.error", error=str(e))
                ok = [r for r in iteration_results if r.success]
                if ok:
                    final_response = f"Done. Tools executed: {', '.join(r.tool for r in ok)}."
                else:
                    final_response = "Something went wrong processing your request."

            step.end_time = time.monotonic()
            step.status = "success"
            step.details = {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
            }
            steps.append(step)

            # Step 7: Check if we need continuation
            if not _check_continuation(iteration_results, final_response):
                break

        return self._build_result(
            final_response,
            all_tools_called,
            all_tool_results,
            steps,
            start_time,
            llm_calls,
            total_input_tokens,
            total_output_tokens,
        )

    def _populate_draft_line_items(
        self, ctx: AgentContext, message: str, results: list[ToolResult]
    ) -> None:
        from aeros.services import rfx_service

        created = next(
            (r for r in results if r.tool == "create_rfx" and r.success and r.data.get("rfx_id")),
            None,
        )
        if not created:
            return
        rfx_id = created.data["rfx_id"]
        org_id = ctx.caller.org_id or 0

        details = rfx_service.get_rfx_with_details(ctx.session, rfx_id) or {}
        existing = details.get("line_items", [])

        if not existing:
            resolved = _resolve_line_items(message, ctx.session, org_id)
            if resolved:
                rfx_service.add_line_items(
                    ctx.session,
                    rfx_id,
                    [{k: v for k, v in it.items() if k != "sku_name"} for it in resolved],
                )
                details = rfx_service.get_rfx_with_details(ctx.session, rfx_id) or {}
                existing = details.get("line_items", [])

        # Surface the items on the result so the UI renders a details table.
        created.data["line_items"] = [
            {
                "sku_name": li.get("sku_name"),
                "sku_code": li.get("sku_code"),
                "qty": li.get("qty"),
                "unit": li.get("unit") or li.get("unit_override"),
                "target_price": li.get("target_price"),
            }
            for li in existing
        ]

    def _build_result(
        self,
        message: str,
        tools_called: list[str],
        tool_results: list[ToolResult],
        steps: list[PipelineStep],
        start_time: float,
        llm_calls: int,
        input_tokens: int,
        output_tokens: int,
    ) -> AgentResult:
        total_ms = (time.monotonic() - start_time) * 1000
        iterations = sum(1 for s in steps if s.name.startswith("select_tools_"))

        logger.info(
            "agent.complete",
            iterations=iterations,
            llm_calls=llm_calls,
            tools=tools_called,
            total_ms=round(total_ms),
            tokens=input_tokens + output_tokens,
        )

        tool_result_dicts = [
            {
                "tool": r.tool,
                "success": r.success,
                "data": r.data,
                "ms": round(r.latency_ms),
            }
            for r in tool_results
        ]

        blocks = build_blocks_from_results(tool_result_dicts)

        # Safety net: never return a blank bubble. The response LLM occasionally
        # returns an empty string; pair it with a lead-in (or a clarification when
        # there are no structured blocks to show either).
        if not (message or "").strip():
            message = (
                "Here's what I found:"
                if blocks
                else (
                    "I didn't catch a clear action there. I can list your RFx, "
                    "find vendors, or compare offers — what would you like?"
                )
            )

        return AgentResult(
            message=message,
            data={
                "tools_called": tools_called,
                "tool_results": tool_result_dicts,
                "blocks": blocks,
                "performance": {
                    "iterations": iterations,
                    "llm_calls": llm_calls,
                    "total_ms": round(total_ms),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            },
            tool_calls=[{"tool": t, "params": {}} for t in tools_called],
            success=True,
        )


def _format_results_for_prompt(results: list[ToolResult]) -> list[dict[str, Any]]:
    formatted = []
    for r in results:
        if r.success:
            formatted.append({"tool": r.tool, "status": "ok", "data": r.data})
        else:
            formatted.append({"tool": r.tool, "status": "error", "message": r.message})
    return formatted


def _parse_tool_selections(content: str) -> list[tuple[str, dict[str, Any]]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r"[\[{].*[}\]]", content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
            except json.JSONDecodeError:
                return []
        else:
            return []

    if isinstance(parsed, dict):
        if not parsed:
            return []
        if "tool" in parsed:
            return [(parsed["tool"], parsed.get("params", {}))]
        # Handle {"thoughts": "...", "tool_calls": [...]} wrapper format
        if "tool_calls" in parsed and isinstance(parsed["tool_calls"], list):
            parsed = parsed["tool_calls"]
        elif "tools" in parsed and isinstance(parsed["tools"], list):
            parsed = parsed["tools"]
        else:
            return []

    if isinstance(parsed, list):
        results = []
        seen = set()
        for item in parsed:
            if isinstance(item, dict) and "tool" in item:
                key = (item["tool"], json.dumps(item.get("params", {}), sort_keys=True))
                if key not in seen:
                    seen.add(key)
                    results.append((item["tool"], item.get("params", {})))
        return results

    return []


def _check_continuation(_results: list[ToolResult], _response: str) -> bool:
    # The loop currently has no follow-up step to take after a one-shot tool, and
    # re-running selection on the same message only risks repeating work. Stop
    # after any successful execution; the response already summarizes it.
    return False
