"""Tests for new channels, agents, workers, and services.

Covers:
- channels/in_app.py
- channels/email_in.py
- channels/telegram_bot.py
- channels/notifications.py
- agents/vendor_copilot.py
- agents/_stubs/__init__.py
- workers/extract_offer.py
- workers/po_render.py
- workers/reminders.py
- services/reminder_service.py
- api/inbound_telegram.py
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

from aeros.models.organization import Organization, OrgType
from aeros.models.user import User, Role
from aeros.models.user_defaults import UserDefaults
from aeros.models.vendor import Vendor
from aeros.models.rfx import (
    RFxRun,
    RFxStatus,
    RFxLineItem,
    RFxVendor,
    RFxVendorStatus,
    Thread,
    Message,
    Attachment,
    ExtractionStatus,
)
from aeros.models.sku import Category, SKU
from aeros.models.offer import Offer
from aeros.models.award import Award, PurchaseOrder
from aeros.models.audit import AuditLog
from aeros.models.notification import Notification
from aeros.models.llm_cache import LLMCache
from aeros.services.auth_service import hash_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def buyer_org(session: Session) -> Organization:
    org = Organization(name="ChanTestOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def buyer(session: Session, buyer_org: Organization) -> User:
    user = User(
        email="chan-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Chan Buyer",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_user(session: Session, buyer_org: Organization) -> User:
    vorg = Organization(name="ChanVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    user = User(
        email="chan-vendor@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Chan Vendor",
        org_id=vorg.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_record(session: Session, buyer_org: Organization, vendor_user: User) -> Vendor:
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        name="Chan Vendor Co",
        primary_email="chan-vendor@test.com",
        vendor_user_id=vendor_user.id,
        telegram_chat_id="12345",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def rfx(session: Session, buyer: User) -> RFxRun:
    r = RFxRun(
        buyer_id=buyer.id,
        title="Channel Test RFx",
        status=RFxStatus.DISPATCHED,
        response_deadline=datetime.utcnow() + timedelta(hours=3),
    )
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


@pytest.fixture
def thread(session: Session, rfx: RFxRun, vendor_record: Vendor) -> Thread:
    t = Thread(rfx_id=rfx.id, vendor_id=vendor_record.id)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def rfx_vendor(session: Session, rfx: RFxRun, vendor_record: Vendor) -> RFxVendor:
    rv = RFxVendor(
        rfx_id=rfx.id,
        vendor_id=vendor_record.id,
        status=RFxVendorStatus.INVITED,
        dispatched_at=datetime.utcnow(),
    )
    session.add(rv)
    session.commit()
    session.refresh(rv)
    return rv


# ===========================================================================
# channels/in_app.py
# ===========================================================================


class TestInAppChannel:
    """Tests for the in-app message delivery channel."""

    def test_deliver_in_app_creates_message(self, session: Session, thread: Thread) -> None:
        """Should create a Message with channel='in_app' and persist it."""
        from aeros.channels.in_app import deliver_in_app

        msg = asyncio.run(
            deliver_in_app(session, thread.id, "Hello from in-app")
        )

        assert msg.id is not None
        assert msg.thread_id == thread.id
        assert msg.channel == "in_app"
        assert msg.body_text == "Hello from in-app"
        assert msg.sender_kind == "system"

    def test_deliver_in_app_with_sender(self, session: Session, thread: Thread, buyer: User) -> None:
        """Should set sender_user_id and sender_kind when provided."""
        from aeros.channels.in_app import deliver_in_app

        msg = asyncio.run(
            deliver_in_app(session, thread.id, "Buyer message", sender_kind="buyer", sender_user_id=buyer.id)
        )

        assert msg.sender_user_id == buyer.id
        assert msg.sender_kind == "buyer"

    def test_deliver_in_app_with_html(self, session: Session, thread: Thread) -> None:
        """Should store body_html when provided."""
        from aeros.channels.in_app import deliver_in_app

        msg = asyncio.run(
            deliver_in_app(session, thread.id, "plain", body_html="<p>rich</p>")
        )

        assert msg.body_html == "<p>rich</p>"

    def test_send_rfx_notification_in_app(self, session: Session, thread: Thread) -> None:
        """Should create a system message with RFQ notification text."""
        from aeros.channels.in_app import send_rfx_notification_in_app

        msg = asyncio.run(
            send_rfx_notification_in_app(session, thread.id, "Steel RFQ", "Need 100 tons")
        )

        assert "Steel RFQ" in msg.body_text
        assert "Need 100 tons" in msg.body_text
        assert msg.sender_kind == "system"

    def test_get_unread_count_zero(self, session: Session, thread: Thread) -> None:
        """Should return 0 when there are no messages."""
        from aeros.channels.in_app import get_unread_count

        count = get_unread_count(session, thread.id)
        assert count == 0

    def test_get_unread_count_after_messages(self, session: Session, thread: Thread) -> None:
        """Should count messages after last_seen_message_id."""
        from aeros.channels.in_app import deliver_in_app, get_unread_count

        m1 = asyncio.run(
            deliver_in_app(session, thread.id, "msg1")
        )
        asyncio.run(
            deliver_in_app(session, thread.id, "msg2")
        )
        asyncio.run(
            deliver_in_app(session, thread.id, "msg3")
        )

        assert get_unread_count(session, thread.id) == 3
        assert get_unread_count(session, thread.id, last_seen_message_id=m1.id) == 2


# ===========================================================================
# channels/email_in.py
# ===========================================================================


class TestEmailInChannel:
    """Tests for inbound email parsing."""

    def test_extract_correlation_token_valid(self) -> None:
        """Should extract token from procurement+TOKEN@domain."""
        from aeros.channels.email_in import extract_correlation_token

        token = extract_correlation_token("procurement+abc123@aeros.local")
        assert token == "abc123"

    def test_extract_correlation_token_none(self) -> None:
        """Should return None when address has no token."""
        from aeros.channels.email_in import extract_correlation_token

        assert extract_correlation_token("vendor@example.com") is None

    def test_parse_email_plain_text(self) -> None:
        """Should parse a plain text email."""
        from aeros.channels.email_in import parse_email_message

        raw = (
            b"From: vendor@example.com\r\n"
            b"To: procurement+tok123@aeros.local\r\n"
            b"Subject: Quote for RFQ\r\n"
            b"Content-Type: text/plain\r\n"
            b"\r\n"
            b"Here is my quote: $100 per unit.\r\n"
        )
        result = parse_email_message(raw)

        assert result["from"] == "vendor@example.com"
        assert result["to"] == "procurement+tok123@aeros.local"
        assert result["subject"] == "Quote for RFQ"
        assert "100 per unit" in result["body_text"]
        assert result["attachments"] == []

    def test_parse_email_html(self) -> None:
        """Should parse an HTML-only email."""
        from aeros.channels.email_in import parse_email_message

        raw = (
            b"From: vendor@example.com\r\n"
            b"To: buyer@aeros.local\r\n"
            b"Subject: HTML Quote\r\n"
            b"Content-Type: text/html\r\n"
            b"\r\n"
            b"<p>My quote is $200</p>\r\n"
        )
        result = parse_email_message(raw)

        assert result["body_text"] == ""
        assert "<p>My quote is $200</p>" in result["body_html"]

    def test_parse_email_multipart(self) -> None:
        """Should parse multipart email with text and attachment."""
        from aeros.channels.email_in import parse_email_message
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart()
        msg["From"] = "vendor@test.com"
        msg["To"] = "procurement+xyz@aeros.local"
        msg["Subject"] = "Multipart Quote"

        msg.attach(MIMEText("Text body here", "plain"))

        att = MIMEBase("application", "pdf")
        att.set_payload(b"%PDF-1.4 fake content")
        encoders.encode_base64(att)
        att.add_header("Content-Disposition", "attachment", filename="quote.pdf")
        msg.attach(att)

        raw = msg.as_bytes()
        result = parse_email_message(raw)

        assert result["body_text"] == "Text body here"
        assert len(result["attachments"]) == 1
        assert result["attachments"][0]["filename"] == "quote.pdf"
        assert result["attachments"][0]["mime_type"] == "application/pdf"

    def test_save_attachments(self, tmp_path) -> None:
        """Should save attachment data to disk and return metadata."""
        from aeros.channels.email_in import save_attachments

        with patch("aeros.channels.email_in.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            attachments = [
                {
                    "filename": "rates.xlsx",
                    "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "data": b"fake excel content here",
                }
            ]
            saved = save_attachments(attachments, rfx_id=1, vendor_id=2)

        assert len(saved) == 1
        assert saved[0]["filename"] == "rates.xlsx"
        assert saved[0]["size_bytes"] == len(b"fake excel content here")
        assert len(saved[0]["sha256"]) == 64
        import os
        assert os.path.exists(saved[0]["storage_path"])


# ===========================================================================
# channels/telegram_bot.py
# ===========================================================================


class TestTelegramBot:
    """Tests for Telegram bot channel."""

    def test_verify_webhook_secret_valid(self) -> None:
        """Should return True when token matches."""
        from aeros.channels.telegram_bot import verify_webhook_secret

        with patch("aeros.channels.telegram_bot.settings") as mock_settings:
            mock_settings.telegram_webhook_secret = "my-secret"
            assert verify_webhook_secret("my-secret") is True

    def test_verify_webhook_secret_invalid(self) -> None:
        """Should return False when token does not match."""
        from aeros.channels.telegram_bot import verify_webhook_secret

        with patch("aeros.channels.telegram_bot.settings") as mock_settings:
            mock_settings.telegram_webhook_secret = "my-secret"
            assert verify_webhook_secret("wrong-secret") is False

    def test_verify_webhook_secret_empty(self) -> None:
        """Should return True when no secret is configured."""
        from aeros.channels.telegram_bot import verify_webhook_secret

        with patch("aeros.channels.telegram_bot.settings") as mock_settings:
            mock_settings.telegram_webhook_secret = ""
            assert verify_webhook_secret("anything") is True

    @pytest.mark.asyncio
    async def test_send_message_no_token(self) -> None:
        """Should return None when no bot token is configured."""
        from aeros.channels.telegram_bot import send_message

        with patch("aeros.channels.telegram_bot.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            result = await send_message("12345", "Hello")
            assert result is None

    @pytest.mark.asyncio
    async def test_send_rfx_invitation(self) -> None:
        """Should format and send an RFQ invitation message."""
        from aeros.channels.telegram_bot import send_rfx_invitation

        with patch("aeros.channels.telegram_bot.send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"ok": True}
            result = await send_rfx_invitation(
                chat_id="12345",
                vendor_name="Test Vendor",
                rfx_title="Steel RFQ",
                rfx_summary="100 tons needed",
                portal_url="https://portal.example.com",
            )

            assert result is True
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][1]
            assert "Steel RFQ" in call_text
            assert "Test Vendor" in call_text

    @pytest.mark.asyncio
    async def test_send_po_notification(self) -> None:
        """Should format and send a PO notification."""
        from aeros.channels.telegram_bot import send_po_notification

        with patch("aeros.channels.telegram_bot.send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"ok": True}
            result = await send_po_notification(
                chat_id="12345",
                vendor_name="Vendor X",
                po_number="PO-1-2-20260101",
                portal_url="https://portal.example.com/po",
            )

            assert result is True
            call_text = mock_send.call_args[0][1]
            assert "PO-1-2-20260101" in call_text


# ===========================================================================
# channels/notifications.py
# ===========================================================================


class TestNotifications:
    """Tests for unified notification fan-out."""

    @pytest.mark.asyncio
    async def test_notify_vendor_in_app_only(
        self, session: Session, vendor_record: Vendor, thread: Thread, vendor_user: User
    ) -> None:
        """Should deliver in-app notification when enabled."""
        from aeros.channels.notifications import notify_vendor

        # Set prefs to in_app only
        vendor_user.notification_prefs_json = json.dumps({"email": False, "telegram": False, "in_app": True})
        session.add(vendor_user)
        session.commit()

        results = await notify_vendor(
            session,
            vendor_record,
            event_type="rfq",
            subject="New RFQ",
            body="Please respond",
            thread_id=thread.id,
        )

        assert results.get("in_app") is True
        assert "email" not in results
        assert "telegram" not in results

    @pytest.mark.asyncio
    async def test_notify_vendor_no_thread_skips_in_app(
        self, session: Session, vendor_record: Vendor, vendor_user: User
    ) -> None:
        """Should skip in-app when no thread_id is provided."""
        from aeros.channels.notifications import notify_vendor

        vendor_user.notification_prefs_json = json.dumps({"email": False, "telegram": False, "in_app": True})
        session.add(vendor_user)
        session.commit()

        results = await notify_vendor(
            session,
            vendor_record,
            event_type="rfq",
            subject="New RFQ",
            body="Please respond",
        )

        assert "in_app" not in results


# ===========================================================================
# agents/vendor_copilot.py
# ===========================================================================


class TestVendorCopilotAgent:
    """Tests for the vendor co-pilot agent."""

    @pytest.mark.asyncio
    async def test_vendor_copilot_returns_result(self, session: Session) -> None:
        """Should return an AgentResult with parsed JSON data."""
        from aeros.agents.vendor_copilot import VendorCopilotAgent
        from aeros.agents.base import AgentContext, AgentResult
        from aeros.ai.base import ChatResponse

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = ChatResponse(
            content=json.dumps({
                "message": "I can help you compose a quote.",
                "suggestions": ["Check unit prices", "Review quantities"],
                "status": "chatting",
            }),
            input_tokens=10,
            output_tokens=20,
        )

        ctx = AgentContext(
            session=session,
            caller=MagicMock(user_id=1, org_id=1, role="vendor"),
            chat_provider=mock_provider,
            metadata={"history": [], "rfx_context": "Steel RFQ for 100 tons"},
        )

        agent = VendorCopilotAgent()
        result = await agent.run(ctx, "How should I price this?")

        assert result.success is True
        assert "help" in result.message.lower() or "quote" in result.message.lower()
        assert result.data.get("status") == "chatting"

    @pytest.mark.asyncio
    async def test_vendor_copilot_handles_invalid_json(self, session: Session) -> None:
        """Should gracefully handle non-JSON LLM response."""
        from aeros.agents.vendor_copilot import VendorCopilotAgent
        from aeros.agents.base import AgentContext
        from aeros.ai.base import ChatResponse

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = ChatResponse(
            content="This is not JSON",
            input_tokens=5,
            output_tokens=10,
        )

        ctx = AgentContext(
            session=session,
            caller=MagicMock(user_id=1, org_id=1, role="vendor"),
            chat_provider=mock_provider,
            metadata={},
        )

        agent = VendorCopilotAgent()
        result = await agent.run(ctx, "Hello")

        assert result.success is True
        assert result.message == "This is not JSON"
        assert result.data.get("status") == "chatting"

    def test_vendor_copilot_name(self) -> None:
        """Agent name should be 'vendor_copilot'."""
        from aeros.agents.vendor_copilot import VendorCopilotAgent

        agent = VendorCopilotAgent()
        assert agent.name == "vendor_copilot"


# ===========================================================================
# agents/_stubs/__init__.py
# ===========================================================================


class TestStubAgents:
    """Tests for stub agents that return 'coming soon' responses."""

    @pytest.mark.asyncio
    async def test_negotiation_agent_stub(self, session: Session) -> None:
        from aeros.agents._stubs import NegotiationAgent
        from aeros.agents.base import AgentContext

        ctx = AgentContext(
            session=session,
            caller=MagicMock(user_id=1, org_id=1, role="buyer"),
            chat_provider=AsyncMock(),
        )
        agent = NegotiationAgent()
        result = await agent.run(ctx, "negotiate")

        assert result.success is False
        assert "coming soon" in result.message.lower()
        assert agent.name == "negotiation"

    @pytest.mark.asyncio
    async def test_contract_agent_stub(self, session: Session) -> None:
        from aeros.agents._stubs import ContractAgent
        from aeros.agents.base import AgentContext

        ctx = AgentContext(
            session=session,
            caller=MagicMock(user_id=1, org_id=1, role="buyer"),
            chat_provider=AsyncMock(),
        )
        agent = ContractAgent()
        result = await agent.run(ctx, "draft")

        assert result.success is False
        assert "coming soon" in result.message.lower()
        assert agent.name == "contract"

    @pytest.mark.asyncio
    async def test_invoice_agent_stub(self, session: Session) -> None:
        from aeros.agents._stubs import InvoiceAgent
        from aeros.agents.base import AgentContext

        ctx = AgentContext(
            session=session,
            caller=MagicMock(user_id=1, org_id=1, role="buyer"),
            chat_provider=AsyncMock(),
        )
        agent = InvoiceAgent()
        result = await agent.run(ctx, "process")

        assert result.success is False
        assert "coming soon" in result.message.lower()
        assert agent.name == "invoice"

    @pytest.mark.asyncio
    async def test_analytics_agent_stub(self, session: Session) -> None:
        from aeros.agents._stubs import AnalyticsAgent
        from aeros.agents.base import AgentContext

        ctx = AgentContext(
            session=session,
            caller=MagicMock(user_id=1, org_id=1, role="buyer"),
            chat_provider=AsyncMock(),
        )
        agent = AnalyticsAgent()
        result = await agent.run(ctx, "report")

        assert result.success is False
        assert "coming soon" in result.message.lower()
        assert agent.name == "analytics"


# ===========================================================================
# services/reminder_service.py
# ===========================================================================


class TestReminderService:
    """Tests for reminder service functions."""

    def test_get_reminders_sent_empty(self, session: Session, rfx_vendor: RFxVendor) -> None:
        """Should return empty list when no reminders sent."""
        from aeros.services.reminder_service import get_reminders_sent

        sent = get_reminders_sent(rfx_vendor)
        assert sent == []

    def test_mark_reminder_sent(self, session: Session, rfx_vendor: RFxVendor) -> None:
        """Should persist slot name in reminders_sent_json."""
        from aeros.services.reminder_service import mark_reminder_sent, get_reminders_sent

        mark_reminder_sent(session, rfx_vendor.id, "T-24h")
        session.refresh(rfx_vendor)

        sent = get_reminders_sent(rfx_vendor)
        assert "T-24h" in sent

    def test_mark_reminder_sent_idempotent(self, session: Session, rfx_vendor: RFxVendor) -> None:
        """Should not duplicate slot names."""
        from aeros.services.reminder_service import mark_reminder_sent, get_reminders_sent

        mark_reminder_sent(session, rfx_vendor.id, "T-24h")
        mark_reminder_sent(session, rfx_vendor.id, "T-24h")
        session.refresh(rfx_vendor)

        sent = get_reminders_sent(rfx_vendor)
        assert sent.count("T-24h") == 1

    def test_get_pending_reminders(
        self, session: Session, rfx: RFxRun, rfx_vendor: RFxVendor
    ) -> None:
        """Should return reminder status per vendor."""
        from aeros.services.reminder_service import get_pending_reminders

        result = get_pending_reminders(session, rfx.id)
        assert len(result) == 1
        assert result[0]["vendor_id"] == rfx_vendor.vendor_id
        assert result[0]["reminders_sent"] == []

    def test_mark_reminder_sent_nonexistent(self, session: Session) -> None:
        """Should gracefully handle non-existent RFxVendor."""
        from aeros.services.reminder_service import mark_reminder_sent

        # Should not raise
        mark_reminder_sent(session, 99999, "T-24h")


# ===========================================================================
# workers/reminders.py
# ===========================================================================


class TestRemindersWorker:
    """Tests for the reminders background worker."""

    @pytest.mark.asyncio
    async def test_check_and_send_reminders_sends_due(
        self, session: Session, rfx: RFxRun, rfx_vendor: RFxVendor, vendor_record: Vendor
    ) -> None:
        """Should send reminders for due slots."""
        from aeros.workers.reminders import check_and_send_reminders

        # Set deadline to 1 hour from now so T-24h and T-2h are due
        rfx.response_deadline = datetime.utcnow() + timedelta(hours=1)
        session.add(rfx)
        session.commit()

        with patch("aeros.workers.reminders.engine", session.get_bind()):
            with patch("aeros.workers.reminders.Session") as MockSession:
                MockSession.return_value.__enter__ = MagicMock(return_value=session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                with patch("aeros.channels.notifications.notify_vendor", new_callable=AsyncMock) as mock_notify:
                    mock_notify.return_value = {"in_app": True}
                    sent = await check_and_send_reminders()

        # T-24h and T-2h should be due (deadline is 1h away)
        assert sent >= 1


# ===========================================================================
# workers/extract_offer.py
# ===========================================================================


class TestExtractOfferWorker:
    """Tests for the offer extraction background worker."""

    @pytest.mark.asyncio
    async def test_extract_offer_attachment_not_found(self) -> None:
        """Should return False when attachment does not exist."""
        from aeros.workers.extract_offer import extract_offer_from_attachment

        with patch("aeros.workers.extract_offer.engine") as mock_engine:
            mock_session = MagicMock()
            mock_session.get.return_value = None
            with patch("aeros.workers.extract_offer.Session") as MockSession:
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                result = await extract_offer_from_attachment(
                    attachment_id=9999,
                    rfx_id=1,
                    vendor_id=1,
                    message_id=1,
                )
        assert result is False


# ===========================================================================
# workers/po_render.py
# ===========================================================================


class TestPORenderWorker:
    """Tests for the PO rendering background worker."""

    @pytest.mark.asyncio
    async def test_render_and_send_po_success(self) -> None:
        """Should return True when PO agent succeeds."""
        from aeros.workers.po_render import render_and_send_po
        from aeros.agents.base import AgentResult

        mock_agent_result = AgentResult(
            message="Generated 1 PO",
            data={"po_numbers": ["PO-1-1-20260101"]},
            success=True,
        )

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run.return_value = mock_agent_result

        mock_session = MagicMock()

        with patch("aeros.workers.po_render.engine"):
            with patch("aeros.workers.po_render.Session") as MockSession:
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                with patch("aeros.agents.po.POAgent", return_value=mock_agent_instance):
                    with patch("aeros.ai.factory.get_chat_provider"):
                        with patch("aeros.security.auth_context.AuthContext"):
                            result = await render_and_send_po(
                                rfx_id=1,
                                award_decisions=[{"vendor_id": 1, "line_item_id": 1}],
                            )

        assert result is True

    @pytest.mark.asyncio
    async def test_render_and_send_po_failure(self) -> None:
        """Should return False when PO agent fails."""
        from aeros.workers.po_render import render_and_send_po
        from aeros.agents.base import AgentResult

        mock_agent_result = AgentResult(
            message="Failed to generate PO",
            success=False,
        )

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run.return_value = mock_agent_result

        mock_session = MagicMock()

        with patch("aeros.workers.po_render.engine"):
            with patch("aeros.workers.po_render.Session") as MockSession:
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                with patch("aeros.agents.po.POAgent", return_value=mock_agent_instance):
                    with patch("aeros.ai.factory.get_chat_provider"):
                        with patch("aeros.security.auth_context.AuthContext"):
                            result = await render_and_send_po(
                                rfx_id=1,
                                award_decisions=[],
                            )

        assert result is False
