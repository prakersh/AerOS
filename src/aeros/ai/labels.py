"""Human-facing labels — the single place that turns internal enums, status
codes, channel names, and pipeline-step names into plain business language.

Nothing here is procurement jargon: a buyer who has never heard "RFx" should
still understand every string the copilot shows.
"""

from __future__ import annotations

# Request lifecycle status (RFxStatus values + a few transient agent states).
_STATUS_LABELS = {
    "drafting": "Draft",
    "draft": "Draft",
    "created": "Draft",
    "awaiting_approval": "Awaiting approval",
    "dispatching": "Sending to vendors",
    "dispatched": "Sent to vendors",
    "collecting": "Collecting quotes",
    "comparing": "Comparing quotes",
    "awarded": "Awarded",
    "closed": "Closed",
    "cancelled": "Cancelled",
    "confirming_dispatch": "Ready to send",
}

# Per-vendor invitation status (RFxVendorStatus).
_VENDOR_STATUS_LABELS = {
    "invited": "Invited",
    "viewed": "Viewed",
    "quoted": "Quoted",
    "declined": "Declined",
    "expired": "Expired",
}

# Document extraction status (ExtractionStatus).
_EXTRACTION_STATUS_LABELS = {
    "pending": "Processing",
    "extracted": "Ready",
    "failed": "Couldn't read",
}

# How a vendor is reached.
_CHANNEL_LABELS = {
    "in_app": "Portal",
    "email": "Email",
    "telegram": "Chat",
}

# Pipeline step -> what the user sees while the copilot works.
_STEP_LABELS = {
    "context": "Reading your request",
    "greeting": "Saying hello",
    "select_tools": "Working out the steps",
    "execute": "Working on it",
    "respond": "Writing a reply",
}

# Tool -> friendly progress copy, shown during the matching execute step.
_TOOL_STEP_LABELS = {
    "create_rfx": "Drafting your request",
    "add_line_items": "Adding items",
    "list_vendors": "Finding vendors",
    "get_vendor_suggestions": "Finding vendors",
    "evaluate_offers": "Comparing quotes",
    "dispatch_rfx": "Sending to vendors",
    "submit_quote": "Submitting your quote",
    "view_rfx_thread": "Opening the request",
    "daily_summary": "Pulling your summary",
}


def humanize(field: str) -> str:
    """Turn a snake_case field name into a readable label: ``payment_terms`` -> ``Payment terms``."""
    text = str(field).replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else text


def status_label(value: object) -> str:
    key = str(value or "").lower()
    return _STATUS_LABELS.get(key, humanize(key))


def vendor_status_label(value: object) -> str:
    key = str(value or "").lower()
    return _VENDOR_STATUS_LABELS.get(key, humanize(key))


def extraction_status_label(value: object) -> str:
    key = str(value or "").lower()
    return _EXTRACTION_STATUS_LABELS.get(key, humanize(key))


def channel_label(value: object) -> str:
    key = str(value or "").lower()
    return _CHANNEL_LABELS.get(key, humanize(key))


def step_label(step_name: str, tool: str | None = None) -> str:
    """Friendly progress copy for a pipeline step.

    ``step_name`` may carry an iteration suffix (``select_tools_1``); the base
    name is used for lookup. A ``tool`` hint refines ``execute`` steps.
    """
    base = str(step_name or "").rsplit("_", 1)
    name = base[0] if len(base) == 2 and base[1].isdigit() else str(step_name or "")
    if tool and tool in _TOOL_STEP_LABELS:
        return _TOOL_STEP_LABELS[tool]
    return _STEP_LABELS.get(name, "Working on it")
