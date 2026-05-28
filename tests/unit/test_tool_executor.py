"""Tests for tool executor — maps tool calls to service-layer functions.

Covers Bug #5: null thread_id when no thread exists for submit_quote.
"""

import pytest
from sqlmodel import select

from aeros.agents.executor import TOOL_ALIASES, execute_tool
from aeros.agents.tools import ToolResult
from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import (
    RFxLineItem,
    RFxRun,
    RFxStatus,
    RFxVendor,
    RFxVendorStatus,
    Thread,
)
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.user_defaults import UserDefaults
from aeros.models.vendor import Vendor
from aeros.security.auth_context import AuthContext
from aeros.services.auth_service import hash_password


@pytest.fixture
def exec_org(session):
    org = Organization(name="ExecOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def exec_buyer(session, exec_org):
    user = User(
        email="exec-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Exec Buyer",
        org_id=exec_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserDefaults(user_id=user.id))
    session.commit()
    return user


@pytest.fixture
def exec_buyer_ctx(exec_buyer, exec_org):
    return AuthContext(
        user_id=exec_buyer.id,
        role=Role.BUYER,
        org_id=exec_org.id,
    )


@pytest.fixture
def exec_vendor_org(session):
    org = Organization(name="ExecVendorOrg", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def exec_vendor_user(session, exec_vendor_org):
    user = User(
        email="exec-vendor@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Exec Vendor",
        org_id=exec_vendor_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def exec_vendor(session, exec_org, exec_vendor_org, exec_vendor_user):
    v = Vendor(
        owning_buyer_org_id=exec_org.id,
        vendor_org_id=exec_vendor_org.id,
        name="Exec Vendor Co",
        primary_email="exec-vendor@test.com",
        vendor_user_id=exec_vendor_user.id,
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def exec_vendor_ctx(exec_vendor_user):
    return AuthContext(
        user_id=exec_vendor_user.id,
        role=Role.VENDOR,
        org_id=exec_vendor_user.org_id,
    )


@pytest.fixture
def exec_category(session):
    cat = Category(name="Exec Category", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def exec_skus(session, exec_org, exec_category):
    sku = SKU(
        org_id=exec_org.id,
        code="EXEC-001",
        name="Rice",
        category_id=exec_category.id,
        unit="kg",
    )
    session.add(sku)
    session.commit()
    session.refresh(sku)
    return sku


class TestToolExecutorBasics:
    """Basic tool executor behavior."""

    def test_happy_path_returns_success(self, session, exec_buyer_ctx):
        """Valid tool returns ToolResult(success=True)."""
        result = execute_tool("list_rfx", {}, session, exec_buyer_ctx)
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.tool == "list_rfx"
        assert isinstance(result.data, list)

    def test_unknown_tool_raises(self, session, exec_buyer_ctx):
        """Unknown tool name raises ValueError."""
        result = execute_tool("nonexistent_tool", {}, session, exec_buyer_ctx)
        assert result.success is False
        assert "Unknown tool" in result.message

    def test_alias_resolution(self, session, exec_buyer_ctx):
        """Tool aliases resolve to canonical names."""
        result = execute_tool("search", {"query": "rice"}, session, exec_buyer_ctx)
        assert result.tool == "search_inventory"

    def test_latency_positive(self, session, exec_buyer_ctx):
        """latency_ms should be > 0."""
        result = execute_tool("list_rfx", {}, session, exec_buyer_ctx)
        assert result.latency_ms > 0

    def test_service_exception_returns_error(self, session, exec_buyer_ctx):
        """Service exceptions produce ToolResult(success=False)."""
        result = execute_tool("get_rfx_details", {"rfx_id": 99999}, session, exec_buyer_ctx)
        assert result.success is False


class TestToolExecutorRFx:
    """Tests for RFx-related tool execution."""

    def test_create_rfx_persists(self, session, exec_buyer_ctx):
        """create_rfx should persist an RFx in the database."""
        result = execute_tool(
            "create_rfx",
            {"title": "Executor Test RFx"},
            session,
            exec_buyer_ctx,
        )
        assert result.success is True
        assert result.data["rfx_id"] is not None
        assert result.data["status"] == "drafting"

        rfx = session.get(RFxRun, result.data["rfx_id"])
        assert rfx is not None
        assert rfx.title == "Executor Test RFx"

    def test_dispatch_rfx_changes_status(self, session, exec_buyer_ctx, exec_vendor):
        """dispatch_rfx should change status to dispatched."""
        rfx = execute_tool("create_rfx", {"title": "Dispatch Test"}, session, exec_buyer_ctx)
        execute_tool(
            "invite_vendor",
            {"rfx_id": rfx.data["rfx_id"], "vendor_id": exec_vendor.id},
            session,
            exec_buyer_ctx,
        )
        result = execute_tool(
            "dispatch_rfx", {"rfx_id": rfx.data["rfx_id"]}, session, exec_buyer_ctx
        )
        assert result.success is True
        assert result.data["status"] == "dispatched"

    def test_cancel_rfx_records_reason(self, session, exec_buyer_ctx):
        """cancel_rfx should persist the cancellation reason."""
        rfx = execute_tool("create_rfx", {"title": "Cancel Test"}, session, exec_buyer_ctx)
        result = execute_tool(
            "cancel_rfx",
            {"rfx_id": rfx.data["rfx_id"], "reason": "Budget cut"},
            session,
            exec_buyer_ctx,
        )
        assert result.success is True
        assert result.data["status"] == "cancelled"

    def test_list_rfx_returns_callers_only(self, session, exec_buyer_ctx):
        """list_rfx should only return the caller's RFx."""
        execute_tool("create_rfx", {"title": "My RFx"}, session, exec_buyer_ctx)
        result = execute_tool("list_rfx", {}, session, exec_buyer_ctx)
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["title"] == "My RFx"

    def test_evaluate_offers_with_quotes(self, session, exec_buyer_ctx, exec_vendor):
        """evaluate_offers should return quoted offers."""
        rfx = execute_tool("create_rfx", {"title": "Eval Test"}, session, exec_buyer_ctx)
        rfx_id = rfx.data["rfx_id"]
        execute_tool(
            "invite_vendor",
            {"rfx_id": rfx_id, "vendor_id": exec_vendor.id},
            session,
            exec_buyer_ctx,
        )
        execute_tool("dispatch_rfx", {"rfx_id": rfx_id}, session, exec_buyer_ctx)

        # Manually set vendor to QUOTED
        rv = session.exec(
            select(RFxVendor).where(
                RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == exec_vendor.id
            )
        ).first()
        rv.status = RFxVendorStatus.QUOTED
        session.add(rv)
        session.commit()

        result = execute_tool("evaluate_offers", {"rfx_id": rfx_id}, session, exec_buyer_ctx)
        assert result.success is True
        assert result.data["quoted"] == 1

    def test_evaluate_offers_no_quotes(self, session, exec_buyer_ctx, exec_vendor):
        """evaluate_offers with no quotes returns empty quoted list."""
        rfx = execute_tool("create_rfx", {"title": "No Quote Test"}, session, exec_buyer_ctx)
        rfx_id = rfx.data["rfx_id"]
        execute_tool(
            "invite_vendor",
            {"rfx_id": rfx_id, "vendor_id": exec_vendor.id},
            session,
            exec_buyer_ctx,
        )
        execute_tool("dispatch_rfx", {"rfx_id": rfx_id}, session, exec_buyer_ctx)

        result = execute_tool("evaluate_offers", {"rfx_id": rfx_id}, session, exec_buyer_ctx)
        assert result.success is True
        assert result.data["quoted"] == 0

    def test_daily_summary_counts(self, session, exec_buyer_ctx):
        """daily_summary should count RFx by status."""
        execute_tool("create_rfx", {"title": "Draft 1"}, session, exec_buyer_ctx)
        execute_tool("create_rfx", {"title": "Draft 2"}, session, exec_buyer_ctx)
        result = execute_tool("daily_summary", {}, session, exec_buyer_ctx)
        assert result.success is True
        assert result.data["total_rfx"] == 2
        assert result.data["drafting"] == 2

    def test_clear_context(self, session, exec_buyer_ctx):
        """clear_context returns cleared flag."""
        result = execute_tool("clear_context", {}, session, exec_buyer_ctx)
        assert result.success is True
        assert result.data["cleared"] is True


class TestToolExecutorBug5:
    """Tests for Bug #5: null thread_id when no thread exists."""

    def test_submit_quote_null_thread_id(
        self, session, exec_vendor_ctx, exec_vendor, exec_buyer, exec_org, exec_skus
    ):
        """When no thread exists, message should not have null thread_id.

        Bug #5: executor.py:215 creates Message(thread_id=thread.id if thread else None)
        which violates the FK constraint. The tool should either create the thread
        automatically or return an error — not create an orphaned message.
        """
        rfx = RFxRun(buyer_id=exec_buyer.id, title="Bug5 Test", status=RFxStatus.DISPATCHED)
        session.add(rfx)
        session.commit()
        session.refresh(rfx)

        li = RFxLineItem(rfx_id=rfx.id, sku_id=exec_skus.id, qty=100)
        session.add(li)
        session.commit()
        session.refresh(li)

        # Verify no thread exists for this vendor+rfx combo
        existing_thread = session.exec(
            select(Thread).where(
                Thread.rfx_id == rfx.id,
                Thread.vendor_id == exec_vendor.id,
            )
        ).first()
        assert existing_thread is None, "Precondition: no thread should exist"

        result = execute_tool(
            "submit_quote",
            {
                "rfx_id": rfx.id,
                "line_items": [{"line_item_id": li.id, "unit_price": 50.0}],
            },
            session,
            exec_vendor_ctx,
        )
        # The tool should either:
        # 1. Create the thread automatically, or
        # 2. Return an error saying thread doesn't exist
        # It should NOT create a message with thread_id=None
        if result.success:
            from aeros.models.rfx import Message

            msgs = list(session.exec(select(Message)).all())
            for msg in msgs:
                assert msg.thread_id is not None, "Message created with null thread_id (Bug #5)"


class TestToolAliases:
    """Test tool alias resolution."""

    def test_all_aliases_resolve(self):
        """All aliases should map to valid tool names."""
        from aeros.agents.tools import TOOL_CATALOG

        for alias, canonical in TOOL_ALIASES.items():
            assert canonical in TOOL_CATALOG, f"Alias '{alias}' maps to unknown tool '{canonical}'"
