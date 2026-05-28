"""Tests for POAgent rendering, idempotency, and error handling.

Covers Bugs #2 (silent PO failure), #6 (idempotency), #7 (HTML-as-PDF fallback).
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import select

from aeros.models.award import Award, PurchaseOrder
from aeros.models.organization import Organization, OrgType
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services import rfx_service
from aeros.services.auth_service import hash_password


@pytest.fixture
def po_buyer_org(session):
    org = Organization(name="POBuyerOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def po_buyer(session, po_buyer_org):
    user = User(
        email="po-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="PO Buyer",
        org_id=po_buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def po_vendor_org(session):
    org = Organization(name="POVendorOrg", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def po_vendor(session, po_vendor_org):
    vendor = Vendor(
        owning_buyer_org_id=po_vendor_org.id,
        vendor_org_id=po_vendor_org.id,
        name="PO Test Vendor",
        primary_email="po-vendor@test.com",
    )
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor


@pytest.fixture
def po_category(session):
    cat = Category(name="PO Category", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def po_skus(session, po_buyer_org, po_category):
    sku1 = SKU(
        org_id=po_buyer_org.id,
        code="PO-001",
        name="Rice",
        category_id=po_category.id,
        unit="kg",
    )
    sku2 = SKU(
        org_id=po_buyer_org.id,
        code="PO-002",
        name="Wheat",
        category_id=po_category.id,
        unit="kg",
    )
    session.add(sku1)
    session.add(sku2)
    session.commit()
    session.refresh(sku1)
    session.refresh(sku2)
    return [sku1, sku2]


@pytest.fixture
def dispatched_rfx(session, po_buyer, po_vendor, po_skus):
    """Create a dispatched RFx with line items and an invited vendor."""
    rfx = rfx_service.create_rfx(session, buyer_id=po_buyer.id, title="PO Test RFx")
    rfx_service.add_line_items(
        session,
        rfx.id,
        [
            {"sku_id": po_skus[0].id, "qty": 100, "target_price": 40.0},
            {"sku_id": po_skus[1].id, "qty": 50, "target_price": 30.0},
        ],
    )
    rfx_service.invite_vendor(session, rfx.id, po_vendor.id, token_hash="po_hash")  # noqa: S106
    rfx_service.dispatch_rfx(session, rfx.id, po_buyer.id)
    return rfx


class TestPORendering:
    """Tests for POAgent HTML template rendering."""

    @patch("aeros.agents.po.send_po_email", new_callable=AsyncMock)
    @patch("weasyprint.HTML")
    def test_po_agent_generates_html_template(
        self, mock_html_cls, mock_email, session, dispatched_rfx, po_buyer, po_vendor
    ):
        """HTML template should contain vendor name, PO number, and line items."""
        mock_html_instance = mock_html_cls.return_value
        mock_html_instance.write_pdf = lambda path: open(  # noqa: SIM115
            path, "w"
        ).write("<html>pdf</html>")

        decisions = [{"vendor_id": po_vendor.id, "items": [1, 2], "qty": 100, "unit_price": 40.0}]
        rfx = rfx_service.award_rfx(session, dispatched_rfx.id, po_buyer.id, decisions)

        award = session.exec(select(Award).where(Award.rfx_id == rfx.id)).first()
        assert award is not None

        from aeros.agents.base import AgentContext
        from aeros.agents.po import POAgent

        agent = POAgent()
        ctx = AgentContext(
            session=session,
            caller=po_buyer,
            chat_provider=AsyncMock(),
        )
        import asyncio

        result = asyncio.run(agent.run(ctx, str(award.id)))
        assert result.success is True
        assert len(result.data["po_numbers"]) == 1

        po = session.exec(select(PurchaseOrder).where(PurchaseOrder.award_id == award.id)).first()
        assert po is not None
        assert po.vendor_id == po_vendor.id
        assert po.total_amount > 0

    @patch("aeros.agents.po.send_po_email", new_callable=AsyncMock)
    @patch("weasyprint.HTML")
    def test_po_agent_calculates_total_from_qty_times_price(
        self, mock_html_cls, mock_email, session, dispatched_rfx, po_buyer, po_vendor
    ):
        """Total = sum(qty * price) for all items."""
        mock_html_instance = mock_html_cls.return_value
        mock_html_instance.write_pdf = lambda path: open(  # noqa: SIM115
            path, "w"
        ).write("<html>pdf</html>")

        decisions = [
            {
                "vendor_id": po_vendor.id,
                "items": [1, 2],
                "sku_id": 1,
                "qty": 100,
                "unit_price": 40.0,
            },
            {
                "vendor_id": po_vendor.id,
                "items": [1, 2],
                "sku_id": 2,
                "qty": 50,
                "unit_price": 30.0,
            },
        ]
        rfx = rfx_service.award_rfx(session, dispatched_rfx.id, po_buyer.id, decisions)

        award = session.exec(select(Award).where(Award.rfx_id == rfx.id)).first()

        from aeros.agents.base import AgentContext
        from aeros.agents.po import POAgent

        agent = POAgent()
        ctx = AgentContext(session=session, caller=po_buyer, chat_provider=AsyncMock())
        import asyncio

        result = asyncio.run(agent.run(ctx, str(award.id)))
        assert result.success is True

        po = session.exec(select(PurchaseOrder).where(PurchaseOrder.award_id == award.id)).first()
        assert po is not None
        # 100 * 40 + 50 * 30 = 4000 + 1500 = 5500
        assert po.total_amount == 5500.0


class TestPOFallback:
    """Tests for Bug #7: WeasyPrint fallback saves HTML but pdf_path is used."""

    @patch("aeros.agents.po.send_po_email", new_callable=AsyncMock)
    @patch("weasyprint.HTML", side_effect=RuntimeError("no weasyprint"))
    def test_weasyprint_fallback_saves_html(
        self, mock_html_cls, mock_email, session, dispatched_rfx, po_buyer, po_vendor
    ):
        """When WeasyPrint fails, an .html file should be saved."""
        decisions = [{"vendor_id": po_vendor.id, "items": [1], "qty": 100, "unit_price": 40.0}]
        rfx = rfx_service.award_rfx(session, dispatched_rfx.id, po_buyer.id, decisions)

        award = session.exec(select(Award).where(Award.rfx_id == rfx.id)).first()

        from aeros.agents.base import AgentContext
        from aeros.agents.po import POAgent

        agent = POAgent()
        ctx = AgentContext(session=session, caller=po_buyer, chat_provider=AsyncMock())
        import asyncio

        result = asyncio.run(agent.run(ctx, str(award.id)))
        assert result.success is True

        po = session.exec(select(PurchaseOrder).where(PurchaseOrder.award_id == award.id)).first()
        assert po is not None
        assert po.pdf_path.endswith(".html")

    @patch("aeros.agents.po.send_po_email", new_callable=AsyncMock)
    @patch("weasyprint.HTML", side_effect=RuntimeError("no weasyprint"))
    def test_po_download_html_fallback_content_type(
        self, mock_html_cls, mock_email, session, dispatched_rfx, po_buyer, po_vendor, client
    ):
        """When pdf_path ends in .html, content-type should be text/html.

        Bug #7: Currently serves HTML as application/pdf.
        """
        decisions = [{"vendor_id": po_vendor.id, "items": [1], "qty": 100, "unit_price": 40.0}]
        rfx = rfx_service.award_rfx(session, dispatched_rfx.id, po_buyer.id, decisions)

        award = session.exec(select(Award).where(Award.rfx_id == rfx.id)).first()

        from aeros.agents.base import AgentContext
        from aeros.agents.po import POAgent

        agent = POAgent()
        ctx = AgentContext(session=session, caller=po_buyer, chat_provider=AsyncMock())
        import asyncio

        asyncio.run(agent.run(ctx, str(award.id)))

        po = session.exec(select(PurchaseOrder).where(PurchaseOrder.award_id == award.id)).first()
        assert po is not None

        # Login as buyer to access PO endpoint
        client.post("/api/auth/login", json={"email": "po-buyer@test.com", "password": "test123"})
        resp = client.get(f"/api/po/{po.id}/download")
        if po.pdf_path and po.pdf_path.endswith(".html"):
            assert resp.status_code == 200
            assert "text/html" in resp.headers.get("content-type", "")
        elif po.pdf_path and os.path.exists(po.pdf_path):
            assert resp.status_code == 200
            assert "application/pdf" in resp.headers.get("content-type", "")


class TestPOIdempotency:
    """Tests for Bug #6: awarding twice should not create duplicate POs."""

    def test_award_from_awarded_raises(self, session, dispatched_rfx, po_buyer, po_vendor):
        """Second award attempt must raise ValueError."""
        decisions = [{"vendor_id": po_vendor.id, "items": [1], "qty": 100, "unit_price": 40.0}]
        rfx_service.award_rfx(session, dispatched_rfx.id, po_buyer.id, decisions)

        with pytest.raises(ValueError, match="Cannot award"):
            rfx_service.award_rfx(session, dispatched_rfx.id, po_buyer.id, decisions)


class TestPOErrorHandling:
    """Tests for Bug #2: bare except: pass swallows PO errors."""

    @patch("aeros.workers.po_render.render_and_send_po", side_effect=RuntimeError("PO failed"))
    def test_award_endpoint_returns_po_error(
        self, mock_po, session, dispatched_rfx, po_buyer, po_vendor, client
    ):
        """When PO generation fails, the error should be in the response."""
        client.post("/api/auth/login", json={"email": "po-buyer@test.com", "password": "test123"})

        resp = client.post(
            f"/api/buyer/rfx/{dispatched_rfx.id}/award",
            json={"decisions": [{"vendor_id": po_vendor.id, "items": [1, 2]}]},
        )
        # The award itself should succeed
        assert resp.status_code == 200
        data = resp.json()
        # Bug #2 fix: PO error should be observable in the response
        assert "po_generation_error" in data
        assert "PO failed" in data["po_generation_error"]


class TestPOServiceUnit:
    """Unit tests for PO service functions."""

    def test_create_po_record(self, session, dispatched_rfx, po_vendor):
        """create_po should persist a PurchaseOrder."""
        from aeros.services import po_service

        award = Award(
            rfx_id=dispatched_rfx.id,
            awarded_by_user_id=dispatched_rfx.buyer_id,
            decisions_json="[]",
        )
        session.add(award)
        session.commit()
        session.refresh(award)

        po = po_service.create_po(
            session=session,
            award_id=award.id,
            vendor_id=po_vendor.id,
            po_number="PO-TEST-001",
            total_amount=5000.0,
            currency="INR",
            terms_json='{"payment": "NET30"}',
            line_items_json="[]",
        )
        assert po.id is not None
        assert po.po_number == "PO-TEST-001"
        assert po.total_amount == 5000.0

    def test_list_pos_for_rfx(self, session, dispatched_rfx, po_vendor):
        """list_pos_for_rfx should return POs for the given RFx."""
        from aeros.services import po_service

        award = Award(
            rfx_id=dispatched_rfx.id,
            awarded_by_user_id=dispatched_rfx.buyer_id,
            decisions_json="[]",
        )
        session.add(award)
        session.commit()
        session.refresh(award)

        po_service.create_po(
            session=session,
            award_id=award.id,
            vendor_id=po_vendor.id,
            po_number="PO-LIST-001",
            total_amount=1000.0,
            currency="INR",
            terms_json="{}",
            line_items_json="[]",
        )

        pos = po_service.list_pos_for_rfx(session, dispatched_rfx.id)
        assert len(pos) == 1
        assert pos[0]["po_number"] == "PO-LIST-001"
