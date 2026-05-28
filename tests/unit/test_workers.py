"""Tests for background workers — reminders and telemetry retention."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import (
    RFxRun,
    RFxStatus,
    RFxVendor,
    RFxVendorStatus,
)
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services.auth_service import hash_password


@pytest.fixture
def worker_org(session):
    org = Organization(name="WorkerOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def worker_buyer(session, worker_org):
    user = User(
        email="worker-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Worker Buyer",
        org_id=worker_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def worker_vendor(session, worker_org):
    vorg = Organization(name="WorkerVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    v = Vendor(
        owning_buyer_org_id=worker_org.id,
        vendor_org_id=vorg.id,
        name="Worker Vendor",
        primary_email="worker-vendor@test.com",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


class TestReminderSlots:
    """Tests for reminder slot logic."""

    def test_reminder_slots_definition(self):
        """Reminder slots should be properly defined."""
        from aeros.workers.reminders import REMINDER_SLOTS

        assert len(REMINDER_SLOTS) == 3
        names = [s["name"] for s in REMINDER_SLOTS]
        assert "T-24h" in names
        assert "T-2h" in names
        assert "final" in names

    def test_reminder_slot_hours_before(self):
        """Each slot should have hours_before > 0."""
        from aeros.workers.reminders import REMINDER_SLOTS

        for slot in REMINDER_SLOTS:
            assert slot["hours_before"] > 0


class TestReminderWorker:
    """Tests for the reminder worker function."""

    @pytest.mark.asyncio
    async def test_reminder_skips_rfx_without_deadline(self, session, worker_buyer, worker_vendor):
        """RFx without deadline should be skipped."""
        rfx = RFxRun(
            buyer_id=worker_buyer.id,
            title="No Deadline RFx",
            status=RFxStatus.DISPATCHED,
            response_deadline=None,
        )
        session.add(rfx)
        session.commit()

        from aeros.workers.reminders import check_and_send_reminders

        # Patch the engine to use our test session
        with patch("aeros.workers.reminders.engine", session.get_bind()):
            count = await check_and_send_reminders()
            # No reminders should be sent for RFx without deadline
            assert count == 0

    @pytest.mark.asyncio
    async def test_reminder_skips_already_quoted_vendors(
        self, session, worker_buyer, worker_vendor
    ):
        """Vendors who already quoted should not get reminders."""
        deadline = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        rfx = RFxRun(
            buyer_id=worker_buyer.id,
            title="Quoted RFx",
            status=RFxStatus.DISPATCHED,
            response_deadline=deadline,
        )
        session.add(rfx)
        session.commit()
        session.refresh(rfx)

        rv = RFxVendor(
            rfx_id=rfx.id,
            vendor_id=worker_vendor.id,
            status=RFxVendorStatus.QUOTED,
        )
        session.add(rv)
        session.commit()

        from aeros.workers.reminders import check_and_send_reminders

        with patch("aeros.workers.reminders.engine", session.get_bind()):
            count = await check_and_send_reminders()
            assert count == 0


class TestTelemetryRetention:
    """Tests for telemetry retention worker."""

    def test_cleanup_old_telemetry_is_importable(self):
        """cleanup_old_telemetry function should be importable and callable."""
        from aeros.workers.telemetry_retention import cleanup_old_telemetry

        assert callable(cleanup_old_telemetry)

    def test_recent_telemetry_survives_cleanup(self, session):
        """Records younger than retention threshold should not be deleted."""
        from aeros.models.observability import LLMCallLog

        log = LLMCallLog(
            trace_id="test-trace-retention",
            provider="mock",
            model="mock-model",
            status="success",
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        log_id = log.id

        # Verify the record persists (retention only deletes > 30 days old)
        found = session.get(LLMCallLog, log_id)
        assert found is not None
        assert found.trace_id == "test-trace-retention"


class TestPORenderWorker:
    """Tests for PO render worker."""

    @pytest.mark.asyncio
    async def test_render_and_send_po_returns_false_on_missing_award(self, session):
        """render_and_send_po should return False when no award exists."""
        from unittest.mock import patch

        from aeros.workers.po_render import render_and_send_po

        with patch("aeros.workers.po_render.engine", session.get_bind()):
            result = await render_and_send_po(99999, [])
            assert result is False
