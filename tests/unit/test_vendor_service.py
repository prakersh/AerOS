"""Tests for vendor_service — vendor listing and retrieval."""

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.vendor import KYCStatus, Vendor
from aeros.services import vendor_service

# ---- fixtures ----


@pytest.fixture
def buyer_org(session):
    org = Organization(name="VendorTestBuyer", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def vendors(session, buyer_org):
    """Create multiple vendors for the buyer org."""
    v1 = Vendor(
        owning_buyer_org_id=buyer_org.id,
        name="Alpha Supplies",
        primary_email="alpha@test.com",
        category_ids_csv="1,2,3",
        preferred_rank=2,
        kyc_status=KYCStatus.APPROVED,
    )
    v2 = Vendor(
        owning_buyer_org_id=buyer_org.id,
        name="Beta Traders",
        primary_email="beta@test.com",
        category_ids_csv="2,4",
        preferred_rank=1,
        kyc_status=KYCStatus.APPROVED,
    )
    v3 = Vendor(
        owning_buyer_org_id=buyer_org.id,
        name="Gamma Goods",
        primary_email="gamma@test.com",
        category_ids_csv="1,3,5",
        preferred_rank=1,
        kyc_status=KYCStatus.PENDING,
    )
    session.add(v1)
    session.add(v2)
    session.add(v3)
    session.commit()
    session.refresh(v1)
    session.refresh(v2)
    session.refresh(v3)
    return [v1, v2, v3]


# ---- tests ----


class TestListVendors:
    def test_list_returns_all_vendors(self, session, buyer_org, vendors):
        """Should return all vendors for the buyer org."""
        result = vendor_service.list_vendors(session, buyer_org.id)
        assert len(result) == 3

    def test_list_empty_for_no_vendors(self, session, buyer_org):
        """Should return empty list when no vendors exist."""
        result = vendor_service.list_vendors(session, buyer_org.id)
        assert result == []

    def test_list_ordered_by_preferred_rank_then_name(self, session, buyer_org, vendors):
        """Should be ordered by preferred_rank then name."""
        result = vendor_service.list_vendors(session, buyer_org.id)
        # preferred_rank=1 first (Beta Traders, Gamma Goods), then preferred_rank=2 (Alpha Supplies)
        assert result[0].name == "Beta Traders"
        assert result[1].name == "Gamma Goods"
        assert result[2].name == "Alpha Supplies"

    def test_list_excludes_other_org_vendors(self, session, buyer_org, vendors):
        """Should not include vendors from other buyer orgs."""
        other_org = Organization(name="OtherBuyer", type=OrgType.BUYER)
        session.add(other_org)
        session.commit()
        session.refresh(other_org)
        other_vendor = Vendor(
            owning_buyer_org_id=other_org.id,
            name="Other Vendor",
            primary_email="other@test.com",
        )
        session.add(other_vendor)
        session.commit()

        result = vendor_service.list_vendors(session, buyer_org.id)
        assert len(result) == 3
        assert all(v.owning_buyer_org_id == buyer_org.id for v in result)


class TestGetVendor:
    def test_get_existing_vendor(self, session, vendors):
        """Should return the vendor by ID."""
        found = vendor_service.get_vendor(session, vendors[0].id)
        assert found is not None
        assert found.name == vendors[0].name

    def test_get_nonexistent_vendor(self, session):
        """Should return None for nonexistent vendor."""
        found = vendor_service.get_vendor(session, 99999)
        assert found is None


class TestVendorsForCategory:
    def test_filter_by_category(self, session, buyer_org, vendors):
        """Should return only vendors that include the given category."""
        # Category 1: Alpha Supplies (1,2,3) and Gamma Goods (1,3,5)
        result = vendor_service.vendors_for_category(session, buyer_org.id, category_id=1)
        names = {v.name for v in result}
        assert "Alpha Supplies" in names
        assert "Gamma Goods" in names
        assert "Beta Traders" not in names

    def test_filter_category_no_match(self, session, buyer_org, vendors):
        """Should return empty list when no vendor has the category."""
        result = vendor_service.vendors_for_category(session, buyer_org.id, category_id=99)
        assert result == []

    def test_filter_category_single_match(self, session, buyer_org, vendors):
        """Category 4 should match only Beta Traders."""
        result = vendor_service.vendors_for_category(session, buyer_org.id, category_id=4)
        assert len(result) == 1
        assert result[0].name == "Beta Traders"
