import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.services.auth_service import hash_password

# ---- vendor-specific fixtures ----


@pytest.fixture
def vendor_org(session):
    org = Organization(name="VendorTestOrg", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def vendor_user_with_profile(session, vendor_org, buyer_org):
    """Create a vendor user AND a Vendor record linked to that user."""
    user = User(
        email="vendor-api@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Vendor API User",
        org_id=vendor_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    vendor = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_user_id=user.id,
        vendor_org_id=vendor_org.id,
        name="Vendor API Co",
        primary_email="vendor-api@test.com",
    )
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return user, vendor


@pytest.fixture
def vendor_auth_client(client, vendor_user_with_profile):
    """TestClient with vendor auth cookie set."""
    _user, _ = vendor_user_with_profile
    resp = client.post(
        "/api/auth/login",
        json={"email": "vendor-api@test.com", "password": "test123"},
    )
    assert resp.status_code == 200
    return client


# ---- tests ----


def test_vendor_inbox_empty(vendor_auth_client):
    """GET /api/vendor/inbox should return [] when no invitations exist."""
    resp = vendor_auth_client.get("/api/vendor/inbox")
    assert resp.status_code == 200
    assert resp.json() == []


def test_vendor_thread_not_found(vendor_auth_client):
    """GET /api/vendor/rfx/999/thread should return 404 when no thread exists."""
    resp = vendor_auth_client.get("/api/vendor/rfx/999/thread")
    assert resp.status_code == 404


def test_vendor_uploads_empty(vendor_auth_client):
    """GET /api/vendor/rfx/999/uploads should return [] when no uploads exist."""
    resp = vendor_auth_client.get("/api/vendor/rfx/999/uploads")
    assert resp.status_code == 200
    assert resp.json() == []


def test_vendor_decline_not_found(vendor_auth_client):
    """POST /api/vendor/rfx/999/decline should return 404 when vendor is not invited."""
    resp = vendor_auth_client.post(
        "/api/vendor/rfx/999/decline",
        json={"reason": "Not interested"},
    )
    assert resp.status_code == 404
