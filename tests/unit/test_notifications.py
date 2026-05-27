"""Tests for notifications channel — fan-out to vendor channels."""

from unittest.mock import AsyncMock, patch

import pytest

from aeros.channels.notifications import notify_vendor
from aeros.models.organization import Organization, OrgType
from aeros.models.vendor import Vendor


@pytest.fixture
def buyer_org(session):
    org = Organization(name="NotifBuyer", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def vendor_record(session, buyer_org):
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        name="Notif Vendor",
        primary_email="notif-vendor@test.com",
        telegram_chat_id="12345",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


class TestNotifyVendor:
    async def test_email_notification(self, session, vendor_record):
        """Should send email notification when email pref is on."""
        # Patch at the source module since import is local
        with patch("aeros.channels.email_out.send_rfx_invitation", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await notify_vendor(
                session,
                vendor_record,
                event_type="rfq",
                subject="New RFQ",
                body="You have a new RFQ",
                portal_url="http://localhost",
                rfx_title="Q3 Vegetables",
            )
            assert result.get("email") is True
            mock_send.assert_called_once()

    async def test_email_failure(self, session, vendor_record):
        """Should return False when email send fails."""
        with patch("aeros.channels.email_out.send_rfx_invitation", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            result = await notify_vendor(
                session,
                vendor_record,
                event_type="rfq",
                subject="Test",
                body="Body",
            )
            assert result.get("email") is False

    async def test_email_exception(self, session, vendor_record):
        """Should catch email exception and return False."""
        with patch("aeros.channels.email_out.send_rfx_invitation", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("SMTP down")
            result = await notify_vendor(
                session,
                vendor_record,
                event_type="rfq",
                subject="Test",
                body="Body",
            )
            assert result.get("email") is False

    async def test_in_app_notification_with_thread(self, session, vendor_record):
        """Should send in-app notification when thread_id is provided."""
        with patch("aeros.channels.in_app.deliver_in_app", new_callable=AsyncMock) as mock_deliver:
            result = await notify_vendor(
                session,
                vendor_record,
                event_type="rfq",
                subject="Test",
                body="Body",
                thread_id=1,
            )
            assert result.get("in_app") is True
            mock_deliver.assert_called_once()

    async def test_in_app_skipped_without_thread(self, session, vendor_record):
        """Should skip in-app notification when thread_id is None."""
        with patch("aeros.channels.in_app.deliver_in_app", new_callable=AsyncMock) as mock_deliver:
            result = await notify_vendor(
                session,
                vendor_record,
                event_type="rfq",
                subject="Test",
                body="Body",
                thread_id=None,
            )
            mock_deliver.assert_not_called()

    async def test_no_email_when_no_primary_email(self, session, buyer_org):
        """Should skip email when vendor has no primary_email."""
        vendor = Vendor(
            owning_buyer_org_id=buyer_org.id,
            name="No Email Vendor",
            primary_email="",
        )
        session.add(vendor)
        session.commit()
        session.refresh(vendor)

        with patch("aeros.channels.email_out.send_rfx_invitation", new_callable=AsyncMock) as mock_send:
            result = await notify_vendor(
                session,
                vendor,
                event_type="rfq",
                subject="Test",
                body="Body",
            )
            mock_send.assert_not_called()
