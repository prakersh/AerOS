"""Multi-attachment fusion — combines extraction results from multiple files into a single offer."""

from typing import Any

import structlog

logger = structlog.get_logger()


def fuse_extractions(extractions: list[dict], rfx_line_items: list[dict]) -> dict:
    """Merge extraction results from multiple attachments into one unified offer.

    Strategy:
    - For each line item, take the extraction with highest confidence.
    - If same item appears in multiple files, prefer the one with higher confidence.
    - Merge supplementary data (delivery terms, validity, etc.) from all sources.

    Args:
        extractions: List of extraction result dicts from individual attachments.
        rfx_line_items: RFx line items for matching extracted items.

    Returns:
        Fused result dict with line_items and metadata.
    """
    fused_items: dict[str, dict] = {}
    meta: dict[str, Any] = {
        "payment_terms": None,
        "delivery_terms": None,
        "validity_days": None,
        "currency": None,
        "notes": [],
        "source_count": len(extractions),
    }

    for extraction in extractions:
        items = extraction.get("line_items", extraction.get("items", []))
        for item in items:
            item_key = _match_key(item, rfx_line_items)
            if not item_key:
                item_key = item.get("name", item.get("sku", "unknown"))

            existing = fused_items.get(item_key)
            new_confidence = item.get("confidence", 0.5)

            if not existing or new_confidence > existing.get("confidence", 0):
                fused_items[item_key] = item

        if not meta["payment_terms"] and extraction.get("payment_terms"):
            meta["payment_terms"] = extraction["payment_terms"]
        if not meta["delivery_terms"] and extraction.get("delivery_terms"):
            meta["delivery_terms"] = extraction["delivery_terms"]
        if not meta["validity_days"] and extraction.get("validity_days"):
            meta["validity_days"] = extraction["validity_days"]
        if not meta["currency"] and extraction.get("currency"):
            meta["currency"] = extraction["currency"]
        if extraction.get("notes"):
            meta["notes"].append(extraction["notes"])

    return {
        "line_items": list(fused_items.values()),
        **meta,
    }


def _match_key(item: dict, rfx_line_items: list[dict]) -> str | None:
    """Match an extracted item to an RFx line item by code or name.

    Args:
        item: Extracted item dict with name/sku_code/code fields.
        rfx_line_items: RFx line items with name/code fields.

    Returns:
        Matched key string, or None if no match found.
    """
    item_name = (item.get("name") or item.get("sku_name") or "").lower().strip()
    item_code = (item.get("sku_code") or item.get("code") or "").lower().strip()

    for rfx_item in rfx_line_items:
        rfx_name = (rfx_item.get("name") or "").lower().strip()
        rfx_code = (rfx_item.get("code") or "").lower().strip()

        if item_code and rfx_code and item_code == rfx_code:
            return rfx_code
        names_match = item_name == rfx_name or item_name in rfx_name or rfx_name in item_name
        if item_name and rfx_name and names_match:
            return rfx_name

    return None
