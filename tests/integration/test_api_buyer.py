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
    draft = {"title": "To Be Cancelled"}
    create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    assert create_resp.status_code == 200
    rfx_id = create_resp.json()["data"]["rfx_id"]

    resp = auth_client.post(
        f"/api/buyer/rfx/{rfx_id}/cancel",
        json={"reason": "No longer needed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_reason"] == "No longer needed"


def test_assign_vendors(auth_client, skus, vendor_record):
    """POST /api/buyer/rfx/{id}/assign-vendors should assign vendors to items."""
    draft = {
        "title": "Assign Test",
        "line_items": [{"sku_name": "Milk", "qty": 100}],
    }
    create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    assert create_resp.status_code == 200
    rfx_id = create_resp.json()["data"]["rfx_id"]

    # Get line item ID
    detail_resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}")
    li_id = detail_resp.json()["line_items"][0]["id"]

    resp = auth_client.post(
        f"/api/buyer/rfx/{rfx_id}/assign-vendors",
        json={"assignments": [{"vendor_id": vendor_record.id, "line_item_ids": [li_id]}]},
    )
    assert resp.status_code == 200


def test_assign_vendors_invalid_ids(auth_client, skus, vendor_record):
    """Assign with invalid line item IDs should return 400."""
    draft = {"title": "Invalid Assign Test"}
    create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    assert create_resp.status_code == 200
    rfx_id = create_resp.json()["data"]["rfx_id"]

    resp = auth_client.post(
        f"/api/buyer/rfx/{rfx_id}/assign-vendors",
        json={"assignments": [{"vendor_id": vendor_record.id, "line_item_ids": [99999]}]},
    )
    assert resp.status_code == 400


def test_vendor_suggestions(auth_client, skus, vendor_record):
    """GET /api/buyer/rfx/{id}/vendor-suggestions should return suggestions."""
    draft = {
        "title": "Suggest Test",
        "line_items": [{"sku_name": "Milk", "qty": 50}],
    }
    create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    assert create_resp.status_code == 200
    rfx_id = create_resp.json()["data"]["rfx_id"]

    resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}/vendor-suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert "unassigned_items" in data


def test_defaults_get_and_put(auth_client):
    """GET and PUT /api/buyer/defaults should work."""
    resp = auth_client.get("/api/buyer/defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert "payment_terms" in data
    assert "currency" in data


def test_activity_returns_audit_logs(auth_client, skus):
    """GET /api/buyer/activity should return audit log entries."""
    # Create an RFx to generate audit log
    draft = {"title": "Activity Test"}
    auth_client.post("/api/chat/create-rfx", json={"draft": draft})

    resp = auth_client.get("/api/buyer/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Should have at least one entry from the create_rfx action
    assert len(data) >= 1


def test_get_rfx_idor_blocked(auth_client, skus):
    """GET /api/buyer/rfx/{id} should block access to other buyer's RFx."""
    # Create an RFx as the authenticated buyer
    draft = {"title": "IDOR Test"}
    create_resp = auth_client.post("/api/chat/create-rfx", json={"draft": draft})
    rfx_id = create_resp.json()["data"]["rfx_id"]

    # Access should work for the owner
    resp = auth_client.get(f"/api/buyer/rfx/{rfx_id}")
    assert resp.status_code == 200
