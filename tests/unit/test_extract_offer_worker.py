"""Tests for extract_offer worker — background extraction flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aeros.models.organization import OrgType, Organization
from aeros.models.rfx import (
    Attachment,
    ExtractionStatus,
    Message,
    RFxRun,
    RFxStatus,
    RFxVendor,
    RFxVendorStatus,
    Thread,
)
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services.auth_service import hash_password


@pytest.fixture
def buyer_org(session):
    org = Organization(name="WorkerTestBuyer", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def buyer_user(session, buyer_org):
    user = User(
        email="worker-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Worker Buyer",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_record(session, buyer_org):
    vorg = Organization(name="WorkerVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_org_id=vorg.id,
        name="Worker Vendor",
        primary_email="worker-vendor@test.com",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def rfx_run(session, buyer_user):
    rfx = RFxRun(title="Worker RFx", buyer_id=buyer_user.id, status=RFxStatus.DISPATCHED)
    session.add(rfx)
    session.commit()
    session.refresh(rfx)
    return rfx


@pytest.fixture
def thread(session, rfx_run, vendor_record):
    t = Thread(rfx_id=rfx_run.id, vendor_id=vendor_record.id)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def message(session, thread):
    m = Message(thread_id=thread.id, sender_kind="vendor", body_text="Here is our quote")
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


@pytest.fixture
def attachment(session, message):
    att = Attachment(
        message_id=message.id,
        filename="quote.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/quote.pdf",
        size_bytes=1024,
    )
    session.add(att)
    session.commit()
    session.refresh(att)
    return att


@pytest.fixture
def rfx_vendor(session, rfx_run, vendor_record):
    rv = RFxVendor(
        rfx_id=rfx_run.id,
        vendor_id=vendor_record.id,
        status=RFxVendorStatus.INVITED,
    )
    session.add(rv)
    session.commit()
    session.refresh(rv)
    return rv


def _make_mock_session(real_session):
    """Create a mock Session that acts as a context manager returning real_session."""
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=real_session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_session_cls


class TestExtractOfferFromAttachment:
    async def test_attachment_not_found_returns_false(self, session, rfx_run, vendor_record):
        """Should return False when attachment doesn't exist."""
        from aeros.workers.extract_offer import extract_offer_from_attachment

        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session_cls = _make_mock_session(mock_session)

        with (
            patch("aeros.workers.extract_offer.Session", mock_session_cls),
            patch("aeros.workers.extract_offer.engine", MagicMock()),
        ):
            result = await extract_offer_from_attachment(
                attachment_id=99999,
                rfx_id=rfx_run.id,
                vendor_id=vendor_record.id,
                message_id=1,
            )
            assert result is False

    async def test_successful_extraction(
        self, session, rfx_run, vendor_record, message, attachment, rfx_vendor
    ):
        """Should create offer and update statuses on successful extraction."""
        from aeros.workers.extract_offer import extract_offer_from_attachment

        mock_agent_result = MagicMock()
        mock_agent_result.success = True
        mock_agent_result.data = {
            "total_quote": 5000.0,
            "currency": "INR",
            "line_items": [{"sku_name": "Rice", "unit_price": 40}],
            "confidence_overall": 0.9,
        }

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_agent_result)

        mock_session = MagicMock()
        mock_session.get.return_value = attachment
        mock_session.exec.return_value.first.return_value = rfx_vendor
        mock_session_cls = _make_mock_session(mock_session)

        # Patch at source modules since imports are local inside the function
        with (
            patch("aeros.workers.extract_offer.Session", mock_session_cls),
            patch("aeros.workers.extract_offer.engine", MagicMock()),
            patch("aeros.agents.evaluation.EvaluationAgent", return_value=mock_agent),
            patch("aeros.agents.base.AgentContext", return_value=MagicMock()),
            patch("aeros.ai.factory.get_chat_provider", return_value=MagicMock()),
            patch("aeros.ai.factory.get_vision_provider", return_value=MagicMock()),
            patch("aeros.security.auth_context.AuthContext", return_value=MagicMock()),
            patch("aeros.workers.extract_offer.offer_service") as mock_offer_svc,
        ):
            mock_offer_svc.create_offer_from_extraction = MagicMock()
            result = await extract_offer_from_attachment(
                attachment_id=attachment.id,
                rfx_id=rfx_run.id,
                vendor_id=vendor_record.id,
                message_id=message.id,
            )

            assert result is True

    async def test_failed_extraction_marks_failed(
        self, session, rfx_run, vendor_record, message, attachment, rfx_vendor
    ):
        """Should mark attachment as FAILED when extraction fails."""
        from aeros.workers.extract_offer import extract_offer_from_attachment

        mock_agent_result = MagicMock()
        mock_agent_result.success = False
        mock_agent_result.data = None

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_agent_result)

        mock_session = MagicMock()
        mock_session.get.return_value = attachment
        mock_session_cls = _make_mock_session(mock_session)

        with (
            patch("aeros.workers.extract_offer.Session", mock_session_cls),
            patch("aeros.workers.extract_offer.engine", MagicMock()),
            patch("aeros.agents.evaluation.EvaluationAgent", return_value=mock_agent),
            patch("aeros.agents.base.AgentContext", return_value=MagicMock()),
            patch("aeros.ai.factory.get_chat_provider", return_value=MagicMock()),
            patch("aeros.ai.factory.get_vision_provider", return_value=MagicMock()),
            patch("aeros.security.auth_context.AuthContext", return_value=MagicMock()),
        ):
            result = await extract_offer_from_attachment(
                attachment_id=attachment.id,
                rfx_id=rfx_run.id,
                vendor_id=vendor_record.id,
                message_id=message.id,
            )

            assert result is False

    async def test_exception_marks_failed(
        self, session, rfx_run, vendor_record, message, attachment, rfx_vendor
    ):
        """Should mark attachment as FAILED when an exception occurs."""
        from aeros.workers.extract_offer import extract_offer_from_attachment

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("LLM exploded"))

        mock_session = MagicMock()
        mock_session.get.return_value = attachment
        mock_session_cls = _make_mock_session(mock_session)

        with (
            patch("aeros.workers.extract_offer.Session", mock_session_cls),
            patch("aeros.workers.extract_offer.engine", MagicMock()),
            patch("aeros.agents.evaluation.EvaluationAgent", return_value=mock_agent),
            patch("aeros.agents.base.AgentContext", return_value=MagicMock()),
            patch("aeros.ai.factory.get_chat_provider", return_value=MagicMock()),
            patch("aeros.ai.factory.get_vision_provider", return_value=MagicMock()),
            patch("aeros.security.auth_context.AuthContext", return_value=MagicMock()),
        ):
            result = await extract_offer_from_attachment(
                attachment_id=attachment.id,
                rfx_id=rfx_run.id,
                vendor_id=vendor_record.id,
                message_id=message.id,
            )

            assert result is False
