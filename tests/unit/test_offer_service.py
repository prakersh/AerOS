"""Tests for offer_service — CRUD + fusion for extracted offers."""

import json

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import RFxLineItem, RFxRun, RFxStatus
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.vendor import KYCStatus, Vendor
from aeros.services import offer_service
from aeros.services.auth_service import hash_password

# ---- fixtures ----


@pytest.fixture
def buyer_org(session):
    org = Organization(name="OfferTestBuyer", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def buyer_user(session, buyer_org):
    user = User(
        email="offer-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Offer Buyer",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_record(session, buyer_org):
    vorg = Organization(name="OfferVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_org_id=vorg.id,
        name="Test Vendor Co",
        primary_email="vendor-offer@test.com",
        kyc_status=KYCStatus.APPROVED,
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def category(session):
    cat = Category(name="Groceries", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def skus(session, buyer_org, category):
    sku1 = SKU(
        org_id=buyer_org.id,
        code="GROC-001",
        name="Rice",
        category_id=category.id,
        unit="kg",
    )
    sku2 = SKU(
        org_id=buyer_org.id,
        code="GROC-002",
        name="Wheat",
        category_id=category.id,
        unit="kg",
    )
    session.add(sku1)
    session.add(sku2)
    session.commit()
    session.refresh(sku1)
    session.refresh(sku2)
    return [sku1, sku2]


@pytest.fixture
def rfx_run(session, buyer_user):
    rfx = RFxRun(title="Offer Test RFx", buyer_id=buyer_user.id, status=RFxStatus.DISPATCHED)
    session.add(rfx)
    session.commit()
    session.refresh(rfx)
    return rfx


@pytest.fixture
def rfx_line_items(session, rfx_run, skus):
    li1 = RFxLineItem(rfx_id=rfx_run.id, sku_id=skus[0].id, qty=100)
    li2 = RFxLineItem(rfx_id=rfx_run.id, sku_id=skus[1].id, qty=50)
    session.add(li1)
    session.add(li2)
    session.commit()
    session.refresh(li1)
    session.refresh(li2)
    return [li1, li2]


# ---- tests ----


class TestCreateOfferFromExtraction:
    def test_create_basic_offer(self, session, rfx_run, vendor_record, rfx_line_items):
        """Should create an offer from extraction data."""
        extraction = {
            "total_quote": 5000.0,
            "currency": "INR",
            "lead_time_hours": 48,
            "payment_terms": "NET30",
            "delivery_terms": "doorstep",
            "line_items": [
                {"sku_name": "Rice", "unit_price": 40.0, "qty": 100},
                {"sku_name": "Wheat", "unit_price": 20.0, "qty": 50},
            ],
            "confidence_overall": 0.85,
        }
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data=extraction,
            source_message_ids=[1, 2],
        )
        assert offer.id is not None
        assert offer.rfx_id == rfx_run.id
        assert offer.vendor_id == vendor_record.id
        assert offer.total_quote == 5000.0
        assert offer.currency == "INR"
        assert offer.revision_no == 1
        assert offer.is_late is False
        assert offer.extraction_confidence_overall == 0.85

    def test_offer_maps_line_items_by_sku_name(
        self,
        session,
        rfx_run,
        vendor_record,
        rfx_line_items,
    ):
        """Should fuzzy-match extracted line item names to RFx line items."""
        extraction = {
            "line_items": [
                {"sku_name": "Rice Basmati", "unit_price": 45.0, "qty": 100},
            ],
        }
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        items = json.loads(offer.line_items_json)
        assert len(items) == 1
        # "rice" should match to the Rice SKU's line item
        assert items[0]["line_item_id"] == rfx_line_items[0].id

    def test_revision_increments_on_duplicate(
        self,
        session,
        rfx_run,
        vendor_record,
        rfx_line_items,
    ):
        """Second offer from same vendor should be revision 2 and supersede the first."""
        extraction = {"line_items": [], "total_quote": 1000.0}
        offer1 = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        offer2 = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data=extraction,
            source_message_ids=[2],
        )
        assert offer1.revision_no == 1
        assert offer2.revision_no == 2

        # Refresh offer1 to see supersede link
        session.refresh(offer1)
        assert offer1.superseded_by_offer_id == offer2.id

    def test_late_flag(self, session, rfx_run, vendor_record):
        """Should store is_late flag correctly."""
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": []},
            source_message_ids=[1],
            is_late=True,
        )
        assert offer.is_late is True

    def test_source_message_ids_stored(self, session, rfx_run, vendor_record):
        """Should store source message IDs as CSV."""
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": []},
            source_message_ids=[10, 20, 30],
        )
        assert offer.source_message_ids_csv == "10,20,30"

    def test_raw_extraction_json_stored(self, session, rfx_run, vendor_record):
        """Should store the raw extraction data as JSON."""
        extraction = {
            "line_items": [{"sku_name": "Rice", "unit_price": 40}],
            "custom_field": "value",
        }
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data=extraction,
            source_message_ids=[1],
        )
        raw = json.loads(offer.raw_extraction_json)
        assert raw["custom_field"] == "value"


class TestGetOffersForRfx:
    def test_returns_empty_when_no_offers(self, session, rfx_run):
        """Should return empty list when no offers exist."""
        result = offer_service.get_offers_for_rfx(session, rfx_run.id)
        assert result == []

    def test_returns_only_non_superseded(self, session, rfx_run, vendor_record):
        """Should return only the latest (non-superseded) offers."""
        offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": [], "total_quote": 100},
            source_message_ids=[1],
        )
        offer2 = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": [], "total_quote": 200},
            source_message_ids=[2],
        )
        result = offer_service.get_offers_for_rfx(session, rfx_run.id)
        # Only offer2 should be returned (offer1 is superseded)
        assert len(result) == 1
        assert result[0].id == offer2.id


class TestGetOfferHistory:
    def test_returns_all_revisions(self, session, rfx_run, vendor_record):
        """Should return all revisions for a vendor on an RFx."""
        offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": [], "total_quote": 100},
            source_message_ids=[1],
        )
        offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": [], "total_quote": 200},
            source_message_ids=[2],
        )
        history = offer_service.get_offer_history(session, rfx_run.id, vendor_record.id)
        assert len(history) == 2
        assert history[0].revision_no == 1
        assert history[1].revision_no == 2

    def test_empty_history(self, session, rfx_run, vendor_record):
        """Should return empty list when no history exists."""
        history = offer_service.get_offer_history(session, rfx_run.id, vendor_record.id)
        assert history == []


class TestOverrideOfferField:
    def test_override_stores_value(self, session, rfx_run, vendor_record, buyer_user):
        """Should store manual override with value, user, and timestamp."""
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": [], "total_quote": 1000.0},
            source_message_ids=[1],
        )
        updated = offer_service.override_offer_field(
            session=session,
            offer_id=offer.id,
            field_name="total_quote",
            new_value="1200.00",
            user_id=buyer_user.id,
        )
        overrides = json.loads(updated.manual_overrides_json)
        assert "total_quote" in overrides
        assert overrides["total_quote"]["value"] == "1200.00"
        assert overrides["total_quote"]["overridden_by"] == buyer_user.id
        assert "overridden_at" in overrides["total_quote"]

    def test_override_nonexistent_offer_raises(self, session, buyer_user):
        """Should raise ValueError for nonexistent offer."""
        with pytest.raises(ValueError, match="Offer not found"):
            offer_service.override_offer_field(
                session=session,
                offer_id=99999,
                field_name="total_quote",
                new_value="100",
                user_id=buyer_user.id,
            )

    def test_multiple_overrides(self, session, rfx_run, vendor_record, buyer_user):
        """Should accumulate multiple field overrides."""
        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=rfx_run.id,
            vendor_id=vendor_record.id,
            extraction_data={"line_items": [], "total_quote": 1000.0},
            source_message_ids=[1],
        )
        offer_service.override_offer_field(session, offer.id, "total_quote", "1100", buyer_user.id)
        updated = offer_service.override_offer_field(
            session, offer.id, "payment_terms", "NET60", buyer_user.id
        )
        overrides = json.loads(updated.manual_overrides_json)
        assert "total_quote" in overrides
        assert "payment_terms" in overrides
