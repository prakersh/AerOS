"""Expanded tests for offer service — revision, supersede, fuzzy matching."""

import json

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import RFxLineItem, RFxRun, RFxStatus
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services import offer_service
from aeros.services.auth_service import hash_password


@pytest.fixture
def offer_org(session):
    org = Organization(name="OfferOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def offer_buyer(session, offer_org):
    user = User(
        email="offer-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Offer Buyer",
        org_id=offer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def offer_vendor(session, offer_org):
    vorg = Organization(name="OfferVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    v = Vendor(
        owning_buyer_org_id=offer_org.id,
        vendor_org_id=vorg.id,
        name="Offer Vendor",
        primary_email="offer-vendor@test.com",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def offer_category(session):
    cat = Category(name="OfferCat", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def offer_rfx(session, offer_buyer, offer_category):
    """Create an RFx with line items for offer testing."""
    sku = SKU(
        org_id=offer_buyer.org_id,
        code="OFFER-001",
        name="Rice Basmati",
        category_id=offer_category.id,
        unit="kg",
    )
    session.add(sku)
    session.commit()
    session.refresh(sku)

    rfx = RFxRun(
        buyer_id=offer_buyer.id,
        title="Offer Test RFx",
        status=RFxStatus.DISPATCHED,
    )
    session.add(rfx)
    session.commit()
    session.refresh(rfx)

    li = RFxLineItem(rfx_id=rfx.id, sku_id=sku.id, qty=100)
    session.add(li)
    session.commit()
    session.refresh(li)

    return rfx, li, sku


class TestCreateOfferFromExtraction:
    """Tests for offer creation from extraction data."""

    def test_create_offer_basic(self, session, offer_rfx, offer_vendor):
        """Basic offer creation should persist correctly."""
        rfx, _li, _sku = offer_rfx
        extraction = {
            "line_items": [
                {
                    "sku_name": "Rice Basmati",
                    "unit_price": 45.0,
                    "confidence": 0.95,
                }
            ],
            "total_quote": 4500.0,
            "confidence_overall": 0.95,
        }
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        assert offer.id is not None
        assert offer.rfx_id == rfx.id
        assert offer.vendor_id == offer_vendor.id
        assert offer.total_quote == 4500.0
        assert offer.revision_no == 1

    def test_create_offer_revision_increments(self, session, offer_rfx, offer_vendor):
        """Second offer should increment revision number."""
        rfx, _li, _sku = offer_rfx
        extraction = {
            "line_items": [{"sku_name": "Rice", "unit_price": 40.0}],
            "total_quote": 4000.0,
        }
        offer1 = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        assert offer1.revision_no == 1

        offer2 = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data={**extraction, "total_quote": 4200.0},
            source_message_ids=[2],
        )
        assert offer2.revision_no == 2

    def test_create_offer_supersedes_previous(self, session, offer_rfx, offer_vendor):
        """Previous offer should get superseded_by_offer_id set."""
        rfx, _li, _sku = offer_rfx
        extraction = {
            "line_items": [{"sku_name": "Rice", "unit_price": 40.0}],
            "total_quote": 4000.0,
        }
        offer1 = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        offer2 = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data={**extraction, "total_quote": 4200.0},
            source_message_ids=[2],
        )
        session.refresh(offer1)
        assert offer1.superseded_by_offer_id == offer2.id

    def test_create_offer_fuzzy_sku_matching(self, session, offer_rfx, offer_vendor):
        """Fuzzy SKU name matching should resolve line_item_id."""
        rfx, li, _sku = offer_rfx
        extraction = {
            "line_items": [{"sku_name": "rice", "unit_price": 45.0, "confidence": 0.9}],
            "total_quote": 4500.0,
        }
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        items = json.loads(offer.line_items_json)
        assert len(items) == 1
        # "rice" should fuzzy-match "Rice Basmati"
        assert items[0]["line_item_id"] == li.id

    def test_create_offer_no_matching_sku(self, session, offer_rfx, offer_vendor):
        """Items without SKU match should get null line_item_id."""
        rfx, _li, _sku = offer_rfx
        extraction = {
            "line_items": [{"sku_name": "Unknown Item", "unit_price": 100.0, "confidence": 0.5}],
            "total_quote": 100.0,
        }
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        items = json.loads(offer.line_items_json)
        assert items[0]["line_item_id"] is None


class TestOfferQueries:
    """Tests for offer query functions."""

    def test_get_offers_for_rfx(self, session, offer_rfx, offer_vendor):
        """Should return only non-superseded offers."""
        rfx, _li, _sku = offer_rfx
        extraction = {
            "line_items": [{"sku_name": "Rice", "unit_price": 40.0}],
            "total_quote": 4000.0,
        }
        offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data={**extraction, "total_quote": 4200.0},
            source_message_ids=[2],
        )
        offers = offer_service.get_offers_for_rfx(session, rfx.id)
        assert len(offers) == 1
        assert offers[0].revision_no == 2

    def test_get_offer_history(self, session, offer_rfx, offer_vendor):
        """Should return all revisions for a vendor."""
        rfx, _li, _sku = offer_rfx
        for i in range(3):
            offer_service.create_offer_from_extraction(
                session=session,
                rfx_id=rfx.id,
                vendor_id=offer_vendor.id,
                extraction_data={
                    "line_items": [],
                    "total_quote": 1000.0 * (i + 1),
                },
                source_message_ids=[i + 1],
            )
        history = offer_service.get_offer_history(session, rfx.id, offer_vendor.id)
        assert len(history) == 3
        assert [h.revision_no for h in history] == [1, 2, 3]


class TestOfferOverride:
    """Tests for manual offer field overrides."""

    def test_override_offer_field(self, session, offer_rfx, offer_vendor):
        """Manual override should be persisted."""
        rfx, _li, _sku = offer_rfx
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx.id,
            vendor_id=offer_vendor.id,
            extraction_data={
                "line_items": [],
                "total_quote": 4000.0,
            },
            source_message_ids=[1],
        )
        updated = offer_service.override_offer_field(
            session=session,
            offer_id=offer.id,
            field_name="total_quote",
            new_value="3800",
            user_id=rfx.buyer_id,
        )
        overrides = json.loads(updated.manual_overrides_json)
        assert "total_quote" in overrides
        assert overrides["total_quote"]["value"] == "3800"

    def test_override_nonexistent_offer_raises(self, session):
        """Override on nonexistent offer should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            offer_service.override_offer_field(
                session=session,
                offer_id=99999,
                field_name="total_quote",
                new_value="100",
                user_id=1,
            )
