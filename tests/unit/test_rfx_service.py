import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import RFxStatus, RFxVendorStatus, Thread
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.user_defaults import UserDefaults
from aeros.models.vendor import Vendor
from aeros.services import rfx_service
from aeros.services.auth_service import hash_password

# ---- fixtures local to rfx_service tests ----


@pytest.fixture
def buyer_org(session):
    org = Organization(name="ServiceTestOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def buyer(session, buyer_org):
    user = User(
        email="svc-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Svc Buyer",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserDefaults(user_id=user.id))
    session.commit()
    return user


@pytest.fixture
def category(session):
    cat = Category(name="Vegetables", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def skus(session, buyer_org, category):
    sku1 = SKU(
        org_id=buyer_org.id,
        code="VEG-001",
        name="Tomato",
        category_id=category.id,
        unit="kg",
    )
    sku2 = SKU(
        org_id=buyer_org.id,
        code="VEG-002",
        name="Onion",
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
def vendor_org(session):
    org = Organization(name="VendorOrg", type=OrgType.VENDOR)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def vendor_record(session, buyer_org, vendor_org):
    v = Vendor(
        owning_buyer_org_id=buyer_org.id,
        vendor_org_id=vendor_org.id,
        name="Test Vendor Co",
        primary_email="vendor-co@test.com",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


# ---- tests ----


def test_create_rfx(session, buyer):
    """create_rfx should persist an RFxRun and return it with an id."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Q3 Vegetables")

    assert rfx.id is not None
    assert rfx.title == "Q3 Vegetables"
    assert rfx.buyer_id == buyer.id
    assert rfx.status == RFxStatus.DRAFTING


def test_add_line_items(session, buyer, skus):
    """add_line_items should attach line items to an RFx."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="LI Test")
    items = [
        {"sku_id": skus[0].id, "qty": 100, "target_price": 25.0},
        {"sku_id": skus[1].id, "qty": 50, "target_price": 18.0},
    ]
    result = rfx_service.add_line_items(session, rfx.id, items)

    assert len(result) == 2
    assert result[0].rfx_id == rfx.id
    assert result[0].qty == 100
    assert result[1].qty == 50


def test_list_rfx_for_buyer(session, buyer, skus, vendor_record):
    """list_rfx_for_buyer should return dicts with vendor_count and line_items."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="List Test")
    rfx_service.add_line_items(
        session,
        rfx.id,
        [{"sku_id": skus[0].id, "qty": 10}],
    )
    rfx_service.invite_vendor(session, rfx.id, vendor_record.id, token_hash="abc123")  # noqa: S106

    results = rfx_service.list_rfx_for_buyer(session, buyer.id)

    assert len(results) == 1
    row = results[0]
    assert row["id"] == rfx.id
    assert row["title"] == "List Test"
    assert row["status"] == "drafting"
    assert row["vendor_count"] == 1
    assert len(row["line_items"]) == 1
    assert row["line_items"][0]["sku_code"] == "VEG-001"
    assert row["line_items"][0]["sku_name"] == "Tomato"


def test_invite_vendor(session, buyer, vendor_record):
    """invite_vendor should create an RFxVendor record and a Thread."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Invite Test")
    rv = rfx_service.invite_vendor(session, rfx.id, vendor_record.id, token_hash="hash123")  # noqa: S106

    assert rv.id is not None
    assert rv.rfx_id == rfx.id
    assert rv.vendor_id == vendor_record.id
    assert rv.status == RFxVendorStatus.INVITED

    # Thread should also have been created
    from sqlmodel import select

    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx.id, Thread.vendor_id == vendor_record.id)
    ).first()
    assert thread is not None


def test_dispatch_rfx(session, buyer, vendor_record):
    """dispatch_rfx should update RFx status to DISPATCHED."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Dispatch Test")
    rfx_service.invite_vendor(session, rfx.id, vendor_record.id, token_hash="d_hash")  # noqa: S106

    updated = rfx_service.dispatch_rfx(session, rfx.id, buyer.id)

    assert updated.status == RFxStatus.DISPATCHED


def test_cancel_rfx(session, buyer):
    """cancel_rfx should update RFx status to CANCELLED with reason."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Cancel Test")

    cancelled = rfx_service.cancel_rfx(session, rfx.id, buyer.id, reason="Budget cut")

    assert cancelled.status == RFxStatus.CANCELLED
    assert cancelled.cancelled_reason == "Budget cut"
    assert cancelled.cancelled_by_user_id == buyer.id
    assert cancelled.cancelled_at is not None


def test_get_rfx_with_details(session, buyer, skus, vendor_record):
    """get_rfx_with_details should return a flat dict including vendor_offers."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Details Test")
    rfx_service.add_line_items(
        session,
        rfx.id,
        [{"sku_id": skus[0].id, "qty": 200, "target_price": 30.0}],
    )
    rfx_service.invite_vendor(session, rfx.id, vendor_record.id, token_hash="det_hash")  # noqa: S106

    details = rfx_service.get_rfx_with_details(session, rfx.id)

    assert details is not None
    assert details["id"] == rfx.id
    assert details["title"] == "Details Test"
    assert details["status"] == "drafting"
    assert len(details["line_items"]) == 1
    assert details["line_items"][0]["qty"] == 200
    assert len(details["vendor_offers"]) == 1
    assert details["vendor_offers"][0]["vendor_id"] == vendor_record.id
    assert details["vendor_offers"][0]["vendor_name"] == "Test Vendor Co"
    assert details["vendor_offers"][0]["status"] == "invited"


def test_decline_rfx_vendor(session, buyer, vendor_record):
    """decline_rfx_vendor should set status to DECLINED with reason."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Decline Test")
    rfx_service.invite_vendor(session, rfx.id, vendor_record.id, token_hash="dec_hash")  # noqa: S106

    rv = rfx_service.decline_rfx_vendor(session, rfx.id, vendor_record.id, reason="No stock")
    assert rv.status == RFxVendorStatus.DECLINED
    assert rv.decline_reason == "No stock"
    assert rv.declined_at is not None


def test_decline_rfx_vendor_not_invited(session, buyer, vendor_record):
    """decline_rfx_vendor should raise ValueError when vendor not invited."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="No Invite Test")
    import pytest

    with pytest.raises(ValueError, match="not invited"):
        rfx_service.decline_rfx_vendor(session, rfx.id, vendor_record.id, reason="test")


def test_list_rfx_for_vendor(session, buyer, skus, vendor_record):
    """list_rfx_for_vendor should return dicts with buyer_name and item_count."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Vendor List Test")
    rfx_service.add_line_items(
        session,
        rfx.id,
        [{"sku_id": skus[0].id, "qty": 25}, {"sku_id": skus[1].id, "qty": 50}],
    )
    rfx_service.invite_vendor(session, rfx.id, vendor_record.id, token_hash="vlist_h")  # noqa: S106

    results = rfx_service.list_rfx_for_vendor(session, vendor_record.id)

    assert len(results) == 1
    row = results[0]
    assert row["rfx_id"] == rfx.id
    assert row["title"] == "Vendor List Test"
    assert row["buyer_name"] == "Svc Buyer"
    assert row["item_count"] == 2


def test_award_rfx(session, buyer, vendor_record):
    """award_rfx should create an Award and set RFx status to AWARDED."""
    rfx = rfx_service.create_rfx(session, buyer_id=buyer.id, title="Award Test")
    rfx_service.invite_vendor(session, rfx.id, vendor_record.id, token_hash="award_hash")  # noqa: S106

    decisions = [{"vendor_id": vendor_record.id, "items": [1, 2]}]
    result = rfx_service.award_rfx(session, rfx.id, buyer.id, decisions)

    assert result.status == RFxStatus.AWARDED
    # Check award was created
    from sqlmodel import select

    from aeros.models.award import Award

    award = session.exec(select(Award).where(Award.rfx_id == rfx.id)).first()
    assert award is not None
    assert award.awarded_by_user_id == buyer.id
