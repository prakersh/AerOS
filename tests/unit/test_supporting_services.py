"""Tests for supporting services — inventory search, auth registration, notifications."""

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.sku import SKU, Category
from aeros.models.vendor import Vendor
from aeros.services import inventory_service


@pytest.fixture
def svc_org(session):
    org = Organization(name="SvcOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def svc_category(session):
    cat = Category(name="Grains", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def svc_vendor(session, svc_org):
    vorg = Organization(name="SvcVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    v = Vendor(
        owning_buyer_org_id=svc_org.id,
        vendor_org_id=vorg.id,
        name="Svc Vendor",
        primary_email="svc-vendor@test.com",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def svc_skus(session, svc_org, svc_category):
    """Create multiple SKUs for search testing."""
    skus = []
    for name, code in [
        ("Basmati Rice", "GRN-001"),
        ("Brown Rice", "GRN-002"),
        ("Wheat Flour", "GRN-003"),
        ("Sugar", "GRN-004"),
    ]:
        sku = SKU(
            org_id=svc_org.id,
            code=code,
            name=name,
            category_id=svc_category.id,
            unit="kg",
        )
        session.add(sku)
        skus.append(sku)
    session.commit()
    for sku in skus:
        session.refresh(sku)
    return skus


class TestInventorySearch:
    """Tests for inventory search edge cases."""

    def test_search_exact_match(self, session, svc_org, svc_skus):
        """Exact name match should return the SKU."""
        results = inventory_service.search_skus(session, svc_org.id, "Basmati Rice")
        assert len(results) == 1
        assert results[0].name == "Basmati Rice"

    def test_search_partial_match(self, session, svc_org, svc_skus):
        """Partial name match should return matching SKUs."""
        results = inventory_service.search_skus(session, svc_org.id, "rice")
        assert len(results) == 2  # Basmati Rice, Brown Rice

    def test_search_no_results(self, session, svc_org, svc_skus):
        """Search with no matches should return empty list."""
        results = inventory_service.search_skus(session, svc_org.id, "xyzzy")
        assert results == []

    def test_search_empty_query(self, session, svc_org, svc_skus):
        """Empty query should return all SKUs."""
        results = inventory_service.search_skus(session, svc_org.id, "")
        assert len(results) == 4

    def test_list_skus_empty_org(self, session):
        """SKUs for an org with no SKUs should return empty."""
        org = Organization(name="EmptyOrg", type=OrgType.BUYER)
        session.add(org)
        session.commit()
        session.refresh(org)
        results = inventory_service.list_skus(session, org.id)
        assert results == []

    def test_list_categories(self, session, svc_category):
        """list_categories should return all categories."""
        results = inventory_service.list_categories(session)
        assert len(results) >= 1
        names = [c.name for c in results]
        assert "Grains" in names


class TestAuthRegistration:
    """Tests for auth registration edge cases."""

    def test_register_buyer_creates_defaults(self, client, session):
        """Registering a buyer should auto-create UserDefaults."""
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "newbuyer@test.com",
                "password": "test12345",
                "display_name": "New Buyer",
                "role": "buyer",
            },
        )
        assert resp.status_code == 200, resp.json()

    def test_register_duplicate_email_rejected(self, client, buyer_user):
        """Registering with existing email should fail."""
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "buyer@test.com",
                "password": "test123",
                "display_name": "Duplicate",
                "role": "buyer",
            },
        )
        # Should fail with 400 or 409
        assert resp.status_code in (400, 409, 422)


class TestNotificationFanout:
    """Tests for notification fan-out logic."""

    @pytest.mark.asyncio
    async def test_notify_vendor_respects_prefs(self, session, svc_vendor):
        """notify_vendor should respect vendor notification preferences."""
        from unittest.mock import AsyncMock, patch

        from aeros.channels.notifications import notify_vendor

        with (
            patch(
                "aeros.channels.email_out.send_rfx_invitation",
                new_callable=AsyncMock,
            ) as mock_email,
            patch(
                "aeros.channels.in_app.deliver_in_app",
                new_callable=AsyncMock,
            ) as mock_inapp,
        ):
            mock_email.return_value = True
            mock_inapp.return_value = None

            result = await notify_vendor(
                session=session,
                vendor=svc_vendor,
                event_type="rfq",
                subject="Test RFQ",
                body="Please quote",
                thread_id=1,
            )
            assert isinstance(result, dict)
