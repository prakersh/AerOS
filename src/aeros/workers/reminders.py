"""Reminder worker -- sends multi-slot reminders to vendors per RFx deadline."""

import json
from datetime import datetime, timedelta

import structlog
from sqlmodel import Session, select

from aeros.db import engine
from aeros.models.rfx import (
    RFxRun,
    RFxStatus,
    RFxVendor,
    RFxVendorStatus,
)
from aeros.models.vendor import Vendor

logger = structlog.get_logger()

REMINDER_SLOTS = [
    {"name": "T-24h", "hours_before": 24},
    {"name": "T-2h", "hours_before": 2},
    {"name": "final", "hours_before": 0.5},
]


async def check_and_send_reminders() -> int:
    """Check all active RFx runs and send due reminders to vendors.

    Returns:
        Number of reminders sent.
    """
    sent_count = 0
    with Session(engine) as session:
        active_rfx = list(
            session.exec(
                select(RFxRun).where(
                    RFxRun.status.in_(
                        [RFxStatus.DISPATCHED, RFxStatus.COLLECTING]
                    ),
                    RFxRun.response_deadline.is_not(None),
                )
            ).all()
        )

        now = datetime.utcnow()

        for rfx in active_rfx:
            if not rfx.response_deadline:
                continue

            vendors = list(
                session.exec(
                    select(RFxVendor).where(
                        RFxVendor.rfx_id == rfx.id,
                        RFxVendor.status.in_(
                            [RFxVendorStatus.INVITED, RFxVendorStatus.VIEWED]
                        ),
                    )
                ).all()
            )

            for rv in vendors:
                sent_slots = json.loads(rv.reminders_sent_json or "[]")

                for slot in REMINDER_SLOTS:
                    if slot["name"] in sent_slots:
                        continue

                    trigger_time = rfx.response_deadline - timedelta(
                        hours=slot["hours_before"]
                    )
                    if now >= trigger_time:
                        vendor = session.get(Vendor, rv.vendor_id)
                        if not vendor:
                            continue

                        try:
                            from aeros.channels.notifications import notify_vendor

                            hours_left = max(
                                0,
                                (rfx.response_deadline - now).total_seconds()
                                / 3600,
                            )
                            await notify_vendor(
                                session,
                                vendor,
                                event_type="reminder",
                                subject=f"Reminder: {rfx.title}",
                                body=(
                                    f"Your quote for '{rfx.title}' is due in "
                                    f"{hours_left:.0f} hours. Please submit "
                                    f"your response."
                                ),
                                rfx_title=rfx.title,
                            )
                            sent_slots.append(slot["name"])
                            rv.reminders_sent_json = json.dumps(sent_slots)
                            session.add(rv)
                            session.commit()
                            sent_count += 1
                            logger.info(
                                "reminder.sent",
                                slot=slot["name"],
                                vendor_id=vendor.id,
                                rfx_id=rfx.id,
                            )
                        except Exception as e:
                            logger.error(
                                "reminder.failed",
                                error=str(e),
                                vendor_id=vendor.id,
                            )

    return sent_count
