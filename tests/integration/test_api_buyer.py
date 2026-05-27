import pytest

from aeros.models.sku import SKU, Category
from aeros.models.vendor import Vendor

# ---- buyer-specific fixtures ----


@pytest.fixture
def category(session):
    cat = Category(name="Dairy", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def skus(session, buyer_org, category):
    sku = SKU(
        org_id=buyer_org.id,
        code="DAI-001",
        name="Milk",
        category_id=category.id,
        unit="ltr",
    )
    session.add(sku)
    session.commit()
    session.refresh(sku)
    return [sku]


@pytest.fixture
def vendor_record(session, buyer_org, vendor_user):
    """A Vendor record owned by the buyer org, linked to vendor_user."""
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_user_id=vendor_user.id,
        name="Acme Supplies",
        primary_email="vendor@test.com",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


# ---- tests ----


def test_list_rfx_empty(auth_client):
    """GET /api/buyer/rfx should return an empty list when no RFx exist."""
    resp = auth_client.get("/api/buyer/rfx")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_vendors(auth_client, vendor_record):
    """GET /api/buyer/vendors should return the vendor list for the buyer's org."""
    resp = auth_client.get("/api/buyer/vendors")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    names = [v["name"] for v in data]
    assert "Acme Supplies" in names


def test_list_inventory(auth_client, skus):
    """GET /api/buyer/inventory should return the SKU list for the buyer's org."""
    resp = auth_client.get("/api/buyer/inventory")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    codes = [s["code"] for s in data]
    assert "DAI-001" in codes


def test_list_categories(auth_client, category):
    """GET /api/buyer/categories should return the categories."""
    resp = auth_client.get("/api/buyer/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    names = [c["name"] for c in data]
    assert "Dairy" in names


def test_get_rfx_not_found(auth_client):
    """GET /api/buyer/rfx/999 should return 404 when RFx doesn't exist."""
    resp = auth_client.get("/api/buyer/rfx/999")
    assert resp.status_code == 404


def test_create_rfx_via_chat(auth_client, skus):
    """POST /api/chat/create-rfx should create an RFx from a draft."""
    draft = {
        "title": "Weekly Dairy Order",
        "line_items": [
            {"sku_name": "Milk", "qty": 50, "unit": "ltr"},
        ],
        "payment_terms": "NET15",
        "currency": "INR",
    }
    resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["rfx_id"] is not None
    assert data["data"]["status"] == "created"


def test_get_rfx_with_details(auth_client, skus):
    """GET /api/buyer/rfx/{id} should return the proper shape after creation."""
    # First create an RFx
    draft = {
        "title": "Detail Check Order",
        "line_items": [
            {"sku_name": "Milk", "qty": 20, "unit": "ltr", "target_price": 55.0},
        ],
    }
    create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    assert create_resp.status_code == 200
    rfx_id = create_resp.json()["data"]["rfx_id"]

    # Now fetch details
    resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == rfx_id
    assert data["title"] == "Detail Check Order"
    assert data["status"] == "drafting"
    assert len(data["line_items"]) == 1
    assert data["line_items"][0]["sku_name"] == "Milk"
    assert data["line_items"][0]["qty"] == 20
    assert "vendor_offers" in data


def test_cancel_rfx(auth_client, skus):
    """POST /api/buyer/rfx/{id}/cancel should cancel the RFx."""
    # Create first
    draft = {"title": "To Be Cancelled"}
    create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    assert create_resp.status_code == 200
    rfx_id = create_resp.json()["data"]["rfx_id"]

    # Cancel it
    resp = auth_client.post(
        f"/api/buyer/rfx/{rfx_id}/cancel",
        json={"reason": "No longer needed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_reason"] == "No longer needed"
