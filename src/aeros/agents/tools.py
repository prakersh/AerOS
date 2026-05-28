"""Procurement tool registry — declarative tool definitions with TOON serialization."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from toon_format import encode as toon_encode


class ToolType(StrEnum):
    INVENTORY = "inventory"
    RFX = "rfx"
    VENDOR = "vendor"
    OFFER = "offer"
    DISPATCH = "dispatch"
    AWARD = "award"
    ANALYTICS = "analytics"
    UTILITY = "utility"


@dataclass
class ToolParam:
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None


@dataclass
class ToolDef:
    name: str
    description: str
    tool_type: ToolType
    parameters: list[ToolParam] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    buyer_only: bool = False
    vendor_only: bool = False

    def to_compact(self) -> str:
        params = ", ".join(
            f"{p.name}:{p.type}{'*' if p.required else '?'}" for p in self.parameters
        )
        return f"{self.name}: {self.description} [{params or 'none'}]"

    def to_catalog_row(self) -> dict:
        params = ", ".join(f"{p.name}:{p.type}{'*' if p.required else ''}" for p in self.parameters)
        return {
            "name": self.name,
            "desc": self.description,
            "params": params,
        }


@dataclass
class ToolResult:
    tool: str
    success: bool
    data: Any = None
    message: str = ""
    latency_ms: float = 0.0


def _build_catalog() -> dict[str, ToolDef]:
    tools: dict[str, ToolDef] = {}

    # ========== INVENTORY ==========

    tools["search_inventory"] = ToolDef(
        name="search_inventory",
        description="Search SKUs by name, code, or fuzzy match",
        tool_type=ToolType.INVENTORY,
        parameters=[
            ToolParam("query", "str", "Search text", required=True),
        ],
        keywords=["search", "find", "sku", "item", "product", "inventory"],
        examples=["Find rice", "Search for tomato", "What SKUs do we have?"],
        buyer_only=True,
    )

    tools["list_categories"] = ToolDef(
        name="list_categories",
        description="List all product categories",
        tool_type=ToolType.INVENTORY,
        parameters=[],
        keywords=["categories", "types", "groups"],
        examples=["What categories?", "Show product types"],
        buyer_only=True,
    )

    # ========== RFX ==========

    tools["create_rfx"] = ToolDef(
        name="create_rfx",
        description="Create a new RFx procurement request",
        tool_type=ToolType.RFX,
        parameters=[
            ToolParam("title", "str", "RFx title", required=True),
            ToolParam("response_deadline", "date", "Vendor response deadline"),
            ToolParam("delivery_window_start", "date", "Delivery start"),
            ToolParam("delivery_window_end", "date", "Delivery end"),
            ToolParam("payment_terms", "str", "Payment terms", default="NET30"),
            ToolParam("delivery_terms", "str", "Delivery terms", default="doorstep"),
            ToolParam("currency", "str", "Currency code", default="INR"),
            ToolParam("notes_for_vendors", "str", "Notes for vendors"),
        ],
        keywords=["create", "new", "rfx", "rfq", "purchase", "procurement", "order", "buy", "need"],
        examples=[
            "Create an RFx for vegetables",
            "I need to buy rice and dal",
            "New purchase request",
        ],
        buyer_only=True,
    )

    tools["add_line_items"] = ToolDef(
        name="add_line_items",
        description="Add line items to an RFx",
        tool_type=ToolType.RFX,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
            ToolParam(
                "items",
                "array",
                "Array of {sku_id, qty, unit_override?, target_price?}",
                required=True,
            ),
        ],
        keywords=["add items", "line items", "add products"],
        examples=["Add 100kg rice to this RFx", "Add items"],
        buyer_only=True,
    )

    tools["list_rfx"] = ToolDef(
        name="list_rfx",
        description="List all RFx for the buyer with status and vendor counts",
        tool_type=ToolType.RFX,
        parameters=[
            ToolParam("status", "str", "Filter: drafting, dispatched, awarded, cancelled"),
        ],
        keywords=["list", "show", "my rfx", "rfqs", "orders", "requests"],
        examples=["Show my RFx", "List active orders", "What's pending?"],
        buyer_only=True,
    )

    tools["get_rfx_details"] = ToolDef(
        name="get_rfx_details",
        description="Get full RFx details — line items, vendor offers, status, comparison",
        tool_type=ToolType.RFX,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
        ],
        keywords=["details", "show rfx", "rfx status", "what's happening"],
        examples=["Show RFx #5", "Details of my rice order", "Check status"],
    )

    tools["cancel_rfx"] = ToolDef(
        name="cancel_rfx",
        description="Cancel an RFx with a reason",
        tool_type=ToolType.RFX,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
            ToolParam("reason", "str", "Cancellation reason", required=True),
        ],
        keywords=["cancel", "withdraw", "abort"],
        examples=["Cancel RFx #3", "Withdraw the rice order"],
        buyer_only=True,
    )

    # ========== VENDOR ==========

    tools["list_vendors"] = ToolDef(
        name="list_vendors",
        description="List all vendors with scores and channels",
        tool_type=ToolType.VENDOR,
        parameters=[],
        keywords=["vendors", "suppliers", "who can supply"],
        examples=["Show vendors", "Who supplies rice?", "List suppliers"],
        buyer_only=True,
    )

    tools["get_vendor_suggestions"] = ToolDef(
        name="get_vendor_suggestions",
        description="AI-matched vendor suggestions for an RFx based on categories",
        tool_type=ToolType.VENDOR,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
        ],
        keywords=["suggest vendors", "recommend", "best vendors", "who should I invite"],
        examples=["Suggest vendors for RFx #5", "Who should I send this to?"],
        buyer_only=True,
    )

    # ========== DISPATCH ==========

    tools["invite_vendor"] = ToolDef(
        name="invite_vendor",
        description="Invite a specific vendor to quote on an RFx",
        tool_type=ToolType.DISPATCH,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
            ToolParam("vendor_id", "int", "Vendor ID", required=True),
        ],
        keywords=["invite", "send to vendor"],
        examples=["Invite vendor #2 to RFx #5"],
        buyer_only=True,
    )

    tools["dispatch_rfx"] = ToolDef(
        name="dispatch_rfx",
        description="Dispatch RFx to all invited vendors via email/telegram/in-app",
        tool_type=ToolType.DISPATCH,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
        ],
        keywords=["dispatch", "send", "send out", "notify vendors"],
        examples=["Dispatch RFx #5", "Send it to vendors", "Notify all vendors"],
        buyer_only=True,
    )

    # ========== OFFER / EVALUATION ==========

    tools["evaluate_offers"] = ToolDef(
        name="evaluate_offers",
        description="Get side-by-side comparison of all vendor offers for an RFx",
        tool_type=ToolType.OFFER,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
        ],
        keywords=["compare", "evaluate", "offers", "quotes", "who quoted", "best price"],
        examples=[
            "Compare quotes for RFx #5",
            "Who gave the best price?",
            "Evaluate offers",
        ],
        buyer_only=True,
    )

    # ========== AWARD ==========

    tools["award_rfx"] = ToolDef(
        name="award_rfx",
        description="Award vendors based on evaluation — generates POs",
        tool_type=ToolType.AWARD,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
            ToolParam(
                "decisions",
                "array",
                "Award decisions: [{vendor_id, items: [line_item_ids]}]",
                required=True,
            ),
        ],
        keywords=["award", "select vendor", "finalize", "accept quote"],
        examples=["Award RFx #5 to vendor #2", "Accept the best quote"],
        buyer_only=True,
    )

    # ========== VENDOR-SIDE TOOLS ==========

    tools["view_rfx_thread"] = ToolDef(
        name="view_rfx_thread",
        description="View RFx details, line items, and message thread as a vendor",
        tool_type=ToolType.RFX,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
        ],
        keywords=["view", "rfx", "details", "what do they need"],
        examples=["Show the RFx", "What items are requested?"],
        vendor_only=True,
    )

    tools["submit_quote"] = ToolDef(
        name="submit_quote",
        description="Submit a structured price quote for an RFx",
        tool_type=ToolType.OFFER,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
            ToolParam(
                "line_items",
                "array",
                "Quote items: [{line_item_id, unit_price, lead_time_days?, notes?}]",
                required=True,
            ),
            ToolParam("payment_terms", "str", "Offered payment terms"),
            ToolParam("delivery_terms", "str", "Offered delivery terms"),
            ToolParam("vendor_remarks", "str", "Additional remarks"),
        ],
        keywords=["quote", "submit", "price", "offer", "bid"],
        examples=["Quote 78/kg for rice", "Submit my prices", "I want to bid"],
        vendor_only=True,
    )

    tools["decline_rfx"] = ToolDef(
        name="decline_rfx",
        description="Decline an RFx invitation with reason",
        tool_type=ToolType.OFFER,
        parameters=[
            ToolParam("rfx_id", "int", "RFx ID", required=True),
            ToolParam("reason", "str", "Decline reason", required=True),
        ],
        keywords=["decline", "reject", "pass", "can't supply"],
        examples=["Decline this RFx", "I can't supply this"],
        vendor_only=True,
    )

    # ========== ANALYTICS ==========

    tools["daily_summary"] = ToolDef(
        name="daily_summary",
        description="Get daily procurement activity summary — new RFx, quotes, awards",
        tool_type=ToolType.ANALYTICS,
        parameters=[],
        keywords=["summary", "today", "activity", "what happened", "overview"],
        examples=["What happened today?", "Give me a summary", "Daily report"],
    )

    # ========== UTILITY ==========

    tools["clear_context"] = ToolDef(
        name="clear_context",
        description="Clear conversation context and start fresh",
        tool_type=ToolType.UTILITY,
        parameters=[],
        keywords=["clear", "reset", "start over", "new conversation"],
        examples=["Clear chat", "Start fresh"],
    )

    return tools


TOOL_CATALOG: dict[str, ToolDef] = _build_catalog()


def get_tools_for_role(role: str) -> list[ToolDef]:
    if role == "buyer":
        return [t for t in TOOL_CATALOG.values() if not t.vendor_only]
    elif role == "vendor":
        return [t for t in TOOL_CATALOG.values() if not t.buyer_only]
    return list(TOOL_CATALOG.values())


def tools_to_toon(tools: list[ToolDef]) -> str:
    rows = [t.to_catalog_row() for t in tools]
    return toon_encode(rows)


def filter_tools_by_keywords(
    message: str,
    tools: list[ToolDef],
    max_tools: int = 6,
) -> list[ToolDef]:
    msg_lower = message.lower()
    msg_words = set(msg_lower.split())
    scored: list[tuple[float, ToolDef]] = []
    for tool in tools:
        score = 0.0
        for kw in tool.keywords:
            if " " in kw:
                if kw in msg_lower:
                    score += 3.0
            elif kw in msg_words:
                score += 2.0
        if score > 0:
            scored.append((score, tool))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return tools[:max_tools]
    return [t for _, t in scored[:max_tools]]
