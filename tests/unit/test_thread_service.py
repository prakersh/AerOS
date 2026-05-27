"""Tests for aeros.services.thread_service — thread/message CRUD."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

# Import ALL models so their tables are created in metadata
from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import (
    Attachment,
    RFxRun,
)
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services import thread_service
from aeros.services.auth_service import hash_password


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def buyer_org(session: Session) -> Organization:
    org = Organization(name="ThreadTestOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def buyer(session: Session, buyer_org: Organization) -> User:
    user = User(
        email="thread-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Thread Buyer",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_record(session: Session, buyer_org: Organization) -> Vendor:
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        name="Thread Vendor",
        primary_email="thread-vendor@test.com",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def rfx(session: Session, buyer: User) -> RFxRun:
    r = RFxRun(buyer_id=buyer.id, title="Thread RFx")
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


# ---- get_or_create_thread ----


class TestGetOrCreateThread:
    def test_creates_new_thread(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor
    ) -> None:
        """Should create a new thread when none exists."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)

        assert thread.id is not None
        assert thread.rfx_id == rfx.id
        assert thread.vendor_id == vendor_record.id

    def test_returns_existing_thread(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor
    ) -> None:
        """Should return the same thread if called twice with same args."""
        t1 = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        t2 = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)

        assert t1.id == t2.id


# ---- add_message ----


class TestAddMessage:
    def test_add_message_basic(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor, buyer: User
    ) -> None:
        """Should create a message attached to the thread."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        msg = thread_service.add_message(
            session,
            thread.id,
            sender_user_id=buyer.id,
            sender_kind="buyer",
            body_text="Hello vendor!",
        )

        assert msg.id is not None
        assert msg.thread_id == thread.id
        assert msg.sender_user_id == buyer.id
        assert msg.sender_kind == "buyer"
        assert msg.body_text == "Hello vendor!"

    def test_add_system_message(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor
    ) -> None:
        """System messages should have sender_user_id=None."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        msg = thread_service.add_message(
            session,
            thread.id,
            body_text="Auto-generated notification",
        )

        assert msg.sender_user_id is None
        assert msg.sender_kind == "system"

    def test_add_message_with_html(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor
    ) -> None:
        """Should store body_html when provided."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        msg = thread_service.add_message(
            session,
            thread.id,
            body_text="Hello",
            body_html="<p>Hello</p>",
        )

        assert msg.body_html == "<p>Hello</p>"


# ---- get_thread_messages ----


class TestGetThreadMessages:
    def test_returns_messages_in_order(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor, buyer: User
    ) -> None:
        """Messages should be returned in chronological order."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        thread_service.add_message(session, thread.id, body_text="First")
        thread_service.add_message(session, thread.id, body_text="Second")
        thread_service.add_message(session, thread.id, body_text="Third")

        messages = thread_service.get_thread_messages(session, thread.id)

        assert len(messages) == 3
        assert messages[0].body_text == "First"
        assert messages[2].body_text == "Third"

    def test_empty_thread_returns_empty_list(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor
    ) -> None:
        """A thread with no messages should return an empty list."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        messages = thread_service.get_thread_messages(session, thread.id)

        assert messages == []


# ---- get_thread_attachments ----


class TestGetThreadAttachments:
    def test_no_attachments(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor
    ) -> None:
        """Thread with no messages should return empty attachments."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        attachments = thread_service.get_thread_attachments(session, thread.id)

        assert attachments == []

    def test_returns_attachments_for_thread(
        self, session: Session, rfx: RFxRun, vendor_record: Vendor
    ) -> None:
        """Should return attachments belonging to thread messages."""
        thread = thread_service.get_or_create_thread(session, rfx.id, vendor_record.id)
        msg = thread_service.add_message(session, thread.id, body_text="See attached")

        att = Attachment(
            message_id=msg.id,
            filename="quote.pdf",
            mime_type="application/pdf",
            storage_path="/uploads/quote.pdf",
            size_bytes=1024,
        )
        session.add(att)
        session.commit()

        attachments = thread_service.get_thread_attachments(session, thread.id)

        assert len(attachments) == 1
        assert attachments[0].filename == "quote.pdf"
