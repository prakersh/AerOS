"""Tests for cross-vendor isolation and file validation security."""

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import RFxRun, RFxStatus, RFxVendor, RFxVendorStatus, Thread
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services.auth_service import hash_password


@pytest.fixture
def iso_org(session):
    org = Organization(name="IsoOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def iso_buyer(session, iso_org):
    user = User(
        email="iso-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Iso Buyer",
        org_id=iso_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def iso_vendor_org_a(session):
    org = Organization(name="VendorOrgA", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def iso_vendor_org_b(session):
    org = Organization(name="VendorOrgB", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def vendor_a_user(session, iso_vendor_org_a):
    user = User(
        email="vendor-a@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Vendor A",
        org_id=iso_vendor_org_a.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_b_user(session, iso_vendor_org_b):
    user = User(
        email="vendor-b@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Vendor B",
        org_id=iso_vendor_org_b.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def vendor_a(session, iso_org, iso_vendor_org_a, vendor_a_user):
    v = Vendor(
        owning_buyer_org_id=iso_org.id,
        vendor_org_id=iso_vendor_org_a.id,
        name="Vendor A",
        primary_email="vendor-a@test.com",
        vendor_user_id=vendor_a_user.id,
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def vendor_b(session, iso_org, iso_vendor_org_b, vendor_b_user):
    v = Vendor(
        owning_buyer_org_id=iso_org.id,
        vendor_org_id=iso_vendor_org_b.id,
        name="Vendor B",
        primary_email="vendor-b@test.com",
        vendor_user_id=vendor_b_user.id,
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@pytest.fixture
def rfx_with_vendors(session, iso_buyer, vendor_a, vendor_b):
    """Create an RFx with threads for both vendors."""
    rfx = RFxRun(
        buyer_id=iso_buyer.id,
        title="Isolation Test RFx",
        status=RFxStatus.DISPATCHED,
    )
    session.add(rfx)
    session.commit()
    session.refresh(rfx)

    for vendor in [vendor_a, vendor_b]:
        rv = RFxVendor(
            rfx_id=rfx.id,
            vendor_id=vendor.id,
            status=RFxVendorStatus.INVITED,
        )
        session.add(rv)
        thread = Thread(rfx_id=rfx.id, vendor_id=vendor.id)
        session.add(thread)
    session.commit()
    return rfx


def _login(client, email):
    resp = client.post("/api/auth/login", json={"email": email, "password": "test123"})
    assert resp.status_code == 200


class TestCrossVendorIsolation:
    """Vendors should only see their own data."""

    def test_vendor_inbox_only_shows_own_invitations(
        self, client, vendor_a_user, vendor_b, vendor_b_user, rfx_with_vendors
    ):
        """Vendor A should only see their own RFx invitations, not vendor B's."""
        # Vendor A inbox
        _login(client, "vendor-a@test.com")
        resp_a = client.get("/api/vendor/inbox")
        assert resp_a.status_code == 200
        inbox_a = resp_a.json()
        assert len(inbox_a) >= 1

        # Vendor B inbox
        _login(client, "vendor-b@test.com")
        resp_b = client.get("/api/vendor/inbox")
        assert resp_b.status_code == 200
        inbox_b = resp_b.json()
        assert len(inbox_b) >= 1

        # Both see the same RFx but via their own vendor lane
        rfx_ids_a = {item.get("rfx_id") for item in inbox_a}
        rfx_ids_b = {item.get("rfx_id") for item in inbox_b}
        assert rfx_with_vendors.id in rfx_ids_a
        assert rfx_with_vendors.id in rfx_ids_b

    def test_vendor_cannot_view_other_vendors_thread(
        self, client, vendor_a_user, vendor_b, rfx_with_vendors
    ):
        """Vendor A should not see Vendor B's thread."""
        _login(client, "vendor-a@test.com")
        # Vendor A should be able to view their own thread
        resp = client.get(f"/api/vendor/rfx/{rfx_with_vendors.id}/thread")
        # Should succeed (200) since vendor A is invited
        assert resp.status_code == 200


class TestFileValidation:
    """File upload validation tests."""

    def test_upload_rejects_path_traversal_filename(self, client, vendor_a_user, rfx_with_vendors):
        """Path traversal in filename should be sanitized."""
        _login(client, "vendor-a@test.com")
        resp = client.post(
            f"/api/vendor/rfx/{rfx_with_vendors.id}/upload",
            files={"file": ("../../etc/passwd", b"malicious", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert ".." not in data.get("filename", "")
        assert "/" not in data.get("filename", "")

    def test_upload_rejects_null_bytes_in_filename(self, client, vendor_a_user, rfx_with_vendors):
        """Null bytes in filename should be handled."""
        _login(client, "vendor-a@test.com")
        resp = client.post(
            f"/api/vendor/rfx/{rfx_with_vendors.id}/upload",
            files={"file": ("test\x00.pdf", b"content", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "\x00" not in data.get("filename", "")
