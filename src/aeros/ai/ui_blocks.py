"""Agent UI blocks — typed, render-safe visual elements an agent can return.

The agent (or a deterministic builder over tool results) emits a list of blocks
under ``AgentResult.data["blocks"]``. The frontend renders each block with a
trusted component, so the agent can reply visually (tables, cards, key-value
panels, action buttons) without ever emitting raw HTML.

Block shapes
------------
text     {"type":"text", "markdown": str}
table    {"type":"table", "title"?, "columns":[{"key","label","align"?}],
          "rows":[{<col-key>: cell}], "note"?}   cell = scalar | {"value","highlight","sub"}
card     {"type":"card", "title", "subtitle"?, "accent"?, "fields":[{"label","value","emphasis"?}]}
keyvalue {"type":"keyvalue", "title"?, "items":[{"label","value"}]}
list     {"type":"list", "title"?, "ordered"?, "items":[str]}
actions  {"type":"actions", "actions":[{"id","label","style"?,"kind","path"?,
          "endpoint"?,"payload"?,"confirm"?}]}   kind = "navigate" | "post"
"""

from typing import Any

import structlog

from aeros.ai.labels import channel_label, status_label

logger = structlog.get_logger()

Block = dict[str, Any]


def _text(markdown: str) -> Block:
    return {"type": "text", "markdown": markdown}


def _card(
    title: str,
    fields: list[dict[str, Any]],
    subtitle: str | None = None,
    accent: str = "indigo",
) -> Block:
    block: Block = {"type": "card", "title": title, "accent": accent, "fields": fields}
    if subtitle:
        block["subtitle"] = subtitle
    return block


def _keyvalue(items: list[dict[str, Any]], title: str | None = None) -> Block:
    block: Block = {"type": "keyvalue", "items": items}
    if title:
        block["title"] = title
    return block


def _actions(actions: list[dict[str, Any]]) -> Block:
    return {"type": "actions", "actions": actions}


def _money(value: Any, currency: str = "INR") -> str:
    symbol = {"INR": "₹", "USD": "$", "EUR": "€"}.get(currency, "")
    try:
        return f"{symbol}{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value) if value not in (None, "") else "—"


# ── per-tool block builders ──────────────────────────────────────────────────


def _blocks_for_create_rfx(data: dict[str, Any]) -> list[Block]:
    rfx_id = data.get("rfx_id")
    fields = [
        {"label": "Title", "value": data.get("title", "—"), "emphasis": True},
        {"label": "Reference", "value": f"#{rfx_id}"},
        {"label": "Status", "value": status_label(data.get("status", "drafting"))},
    ]
    blocks: list[Block] = [_card("Request drafted", fields, accent="indigo")]

    line_items = data.get("line_items") or []
    if line_items:

        def _qty(value: Any) -> str:
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value)

        rows = [
            {
                "item": li.get("sku_name") or li.get("sku_code") or "—",
                "qty": f"{_qty(li.get('qty'))} {li.get('unit') or ''}".strip(),
                "target": _money(li.get("target_price")) if li.get("target_price") else "—",
            }
            for li in line_items
        ]
        blocks.append(
            {
                "type": "table",
                "title": "Requested items",
                "columns": [
                    {"key": "item", "label": "Item"},
                    {"key": "qty", "label": "Qty", "align": "right"},
                    {"key": "target", "label": "Target price", "align": "right"},
                ],
                "rows": rows,
            }
        )

    if rfx_id:
        blocks.append(
            _actions(
                [
                    {
                        "id": "open_rfx",
                        "label": "Open request",
                        "style": "primary",
                        "kind": "navigate",
                        "path": f"/buyer/rfx/{rfx_id}",
                    }
                ]
            )
        )
    return blocks


def _blocks_for_add_line_items(data: dict[str, Any]) -> list[Block]:
    count = data.get("count", 0)
    return [_text(f"Added **{count}** item{'s' if count != 1 else ''} to your request.")]


def _vendor_rows(vendors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for v in vendors:
        score = v.get("score")
        rows.append(
            {
                "vendor": v.get("vendor_name") or v.get("name") or "—",
                "categories": v.get("categories") or "—",
                "score": {"value": f"{score:.0f}" if isinstance(score, (int, float)) else "—"},
                "channel": channel_label(
                    v.get("recommended_channel") or v.get("channel") or "in_app"
                ),
            }
        )
    return rows


def _blocks_for_vendors(data: Any) -> list[Block]:
    vendors = data if isinstance(data, list) else data.get("vendors", [])
    if not vendors:
        return [_text("No matching vendors found.")]
    return [
        {
            "type": "table",
            "title": "Suggested vendors",
            "columns": [
                {"key": "vendor", "label": "Vendor"},
                {"key": "categories", "label": "Categories"},
                {"key": "score", "label": "Match", "align": "right"},
                {"key": "channel", "label": "Reach via"},
            ],
            "rows": _vendor_rows(vendors),
        }
    ]


def _blocks_for_evaluate(data: dict[str, Any]) -> list[Block]:
    line_items = data.get("line_items", [])
    offers = data.get("offers", [])
    if not offers:
        return [_text("No quotes have come in yet.")]

    # price lookup: line_item_id -> {vendor_id: unit_price}
    price_by_item: dict[Any, dict[Any, float]] = {}
    for off in offers:
        for li in off.get("line_items", []):
            lid = li.get("line_item_id")
            if lid is None:
                continue
            price_by_item.setdefault(lid, {})[off.get("vendor_id")] = li.get("unit_price")

    columns = [{"key": "item", "label": "Item"}]
    for off in offers:
        columns.append(
            {
                "key": f"v{off.get('vendor_id')}",
                "label": off.get("vendor_name", "Vendor"),
                "align": "right",
            }
        )

    rows: list[dict[str, Any]] = []
    for li in line_items:
        lid = li.get("id")
        prices = price_by_item.get(lid, {})
        numeric = [p for p in prices.values() if isinstance(p, (int, float))]
        lowest = min(numeric) if numeric else None
        item_label = f"{li.get('sku_name', '')} ({li.get('qty')} {li.get('unit', '')})"
        row: dict[str, Any] = {"item": item_label}
        for off in offers:
            vid = off.get("vendor_id")
            price = prices.get(vid)
            if price is None:
                row[f"v{vid}"] = {"value": "—", "highlight": "muted"}
            else:
                row[f"v{vid}"] = {
                    "value": _money(price),
                    "highlight": "good" if lowest is not None and price == lowest else None,
                }
        rows.append(row)

    blocks: list[Block] = [
        {
            "type": "table",
            "title": "Quote comparison",
            "columns": columns,
            "rows": rows,
            "note": "Lowest price for each item is highlighted.",
        }
    ]
    rfx_id = data.get("rfx_id")
    if rfx_id:
        blocks.append(
            _actions(
                [
                    {
                        "id": "open_comparison",
                        "label": "Compare & award",
                        "style": "primary",
                        "kind": "navigate",
                        "path": f"/buyer/rfx/{rfx_id}",
                    }
                ]
            )
        )
    return blocks


def _blocks_for_dispatch(data: dict[str, Any]) -> list[Block]:
    rfx_id = data.get("rfx_id")
    vendors = data.get("vendors") or []
    fields = [
        {"label": "Reference", "value": f"#{rfx_id}"},
        {"label": "Status", "value": status_label(data.get("status", "dispatched"))},
    ]
    if vendors:
        fields.append({"label": "Vendors", "value": ", ".join(vendors)})
    blocks: list[Block] = [_card("Sent to vendors", fields, accent="green")]
    if rfx_id:
        blocks.append(
            _actions(
                [
                    {
                        "id": "open_rfx",
                        "label": "Open request",
                        "style": "primary",
                        "kind": "navigate",
                        "path": f"/buyer/rfx/{rfx_id}",
                    }
                ]
            )
        )
    return blocks


def _blocks_for_submit_quote(data: dict[str, Any]) -> list[Block]:
    return [
        _card(
            "Quote submitted",
            [
                {"label": "Quote", "value": f"#{data.get('offer_id')}"},
                {"label": "Revision", "value": str(data.get("revision", 1))},
            ],
            subtitle="The buyer can now see your quote alongside the others.",
            accent="green",
        )
    ]


def _blocks_for_view_thread(data: dict[str, Any]) -> list[Block]:
    line_items = data.get("line_items", [])
    blocks: list[Block] = [
        _card(
            data.get("title", "Request"),
            [
                {"label": "Status", "value": status_label(data.get("status", ""))},
                {"label": "Deadline", "value": data.get("deadline") or "—"},
            ],
            accent="indigo",
        )
    ]
    if line_items:
        blocks.append(
            {
                "type": "table",
                "title": "Requested items",
                "columns": [
                    {"key": "item", "label": "Item"},
                    {"key": "qty", "label": "Qty", "align": "right"},
                    {"key": "target", "label": "Target", "align": "right"},
                ],
                "rows": [
                    {
                        "item": li.get("sku_name", ""),
                        "qty": f"{li.get('qty')} {li.get('unit', '')}",
                        "target": _money(li.get("target_price")) if li.get("target_price") else "—",
                    }
                    for li in line_items
                ],
            }
        )
    return blocks


def _blocks_for_daily_summary(data: dict[str, Any]) -> list[Block]:
    return [
        _keyvalue(
            [
                {"label": "Total requests", "value": str(data.get("total_rfx", 0))},
                {"label": "Drafts", "value": str(data.get("drafting", 0))},
                {"label": "Sent to vendors", "value": str(data.get("dispatched", 0))},
                {"label": "Awarded", "value": str(data.get("awarded", 0))},
            ],
            title="Today at a glance",
        )
    ]


_BUILDERS = {
    "create_rfx": _blocks_for_create_rfx,
    "add_line_items": _blocks_for_add_line_items,
    "list_vendors": _blocks_for_vendors,
    "get_vendor_suggestions": _blocks_for_vendors,
    "evaluate_offers": _blocks_for_evaluate,
    "dispatch_rfx": _blocks_for_dispatch,
    "submit_quote": _blocks_for_submit_quote,
    "view_rfx_thread": _blocks_for_view_thread,
    "daily_summary": _blocks_for_daily_summary,
}


def build_blocks_from_results(results: list[dict[str, Any]]) -> list[Block]:
    """Map successful tool results into a flat list of UI blocks.

    ``results`` is a list of ``{"tool": str, "success": bool, "data": Any}``.
    """
    blocks: list[Block] = []
    for r in results:
        if not r.get("success"):
            continue
        builder = _BUILDERS.get(r.get("tool", ""))
        if not builder:
            continue
        data = r.get("data")
        try:
            blocks.extend(builder(data if data is not None else {}))
        except Exception as e:
            # A malformed tool payload must never break the chat response.
            logger.warning("ui_blocks.builder_failed", tool=r.get("tool"), error=str(e))
            continue
    return blocks
