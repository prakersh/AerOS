"""Service-level reminder management for RFx vendor reminders."""

import json

from sqlmodel import Session, select

from aeros.models.rfx import RFxVendor


def get_reminders_sent(rv: RFxVendor) -> list[str]:
    """Get the list of reminder slot names already sent for an RFxVendor.

    Args:
        rv: The RFxVendor record.

    Returns:
        List of slot name strings (e.g. ["T-24h", "T-2h"]).
    """
    try:
        return json.loads(rv.reminders_sent_json or "[]")
    except json.JSONDecodeError:
        return []


def mark_reminder_sent(
    session: Session,
    rv_id: int,
    slot_name: str,
) -> None:
    """Mark a reminder slot as sent for an RFxVendor.

    Args:
        session: Active database session.
        rv_id: RFxVendor record ID.
        slot_name: Reminder slot name (e.g. "T-24h").
    """
    rv = session.get(RFxVendor, rv_id)
    if not rv:
        return
    sent = get_reminders_sent(rv)
    if slot_name not in sent:
        sent.append(slot_name)
        rv.reminders_sent_json = json.dumps(sent)
        session.add(rv)
        session.commit()


def get_pending_reminders(
    session: Session,
    rfx_id: int,
) -> list[dict]:
    """Get reminder status for all vendors in an RFx.

    Args:
        session: Active database session.
        rfx_id: RFx ID to query.

    Returns:
        List of dicts with vendor_id, status, and reminders_sent.
    """
    vendors = list(
        session.exec(
            select(RFxVendor).where(RFxVendor.rfx_id == rfx_id)
        ).all()
    )
    result: list[dict] = []
    for rv in vendors:
        sent = get_reminders_sent(rv)
        result.append({
            "vendor_id": rv.vendor_id,
            "status": rv.status.value if rv.status else "unknown",
            "reminders_sent": sent,
        })
    return result
