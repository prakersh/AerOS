"""Seed demo data for AEROS dark-store persona."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from aeros.db import create_db_and_tables, engine
from aeros.models.offer import Offer
from aeros.models.organization import Organization, OrgType
from aeros.models.rfx import (
    Message,
    RFxLineItem,
    RFxRun,
    RFxStatus,
    RFxVendor,
    RFxVendorStatus,
    Thread,
)
from aeros.models.sku import SKU, Category
from aeros.models.user import Role, User
from aeros.models.user_defaults import UserDefaults
from aeros.models.vendor import KYCStatus, Vendor
from aeros.services.auth_service import hash_password

CATEGORIES = [
    "Fruits & Vegetables",
    "Dairy & Eggs",
    "Packaged FMCG",
    "Bakery",
    "Beverages",
]

SKUS = [
    # Fruits & Vegetables
    ("FV001", "Tomato", "Fruits & Vegetables", "kg", 18.0),
    ("FV002", "Onion", "Fruits & Vegetables", "kg", 22.0),
    ("FV003", "Potato", "Fruits & Vegetables", "kg", 15.0),
    ("FV004", "Green Chilli", "Fruits & Vegetables", "kg", 40.0),
    ("FV005", "Coriander", "Fruits & Vegetables", "kg", 60.0),
    ("FV006", "Capsicum", "Fruits & Vegetables", "kg", 35.0),
    ("FV007", "Carrot", "Fruits & Vegetables", "kg", 25.0),
    ("FV008", "Cabbage", "Fruits & Vegetables", "kg", 20.0),
    ("FV009", "Spinach", "Fruits & Vegetables", "kg", 30.0),
    ("FV010", "Banana", "Fruits & Vegetables", "dozen", 40.0),
    # Dairy & Eggs
    ("DE001", "Full Cream Milk", "Dairy & Eggs", "ltr", 56.0),
    ("DE002", "Toned Milk", "Dairy & Eggs", "ltr", 48.0),
    ("DE003", "Curd (Dahi)", "Dairy & Eggs", "kg", 50.0),
    ("DE004", "Paneer", "Dairy & Eggs", "kg", 320.0),
    ("DE005", "Butter (Amul)", "Dairy & Eggs", "kg", 520.0),
    ("DE006", "Eggs", "Dairy & Eggs", "dozen", 72.0),
    ("DE007", "Cheese Slice", "Dairy & Eggs", "pcs", 25.0),
    ("DE008", "Ghee", "Dairy & Eggs", "ltr", 580.0),
    # Packaged FMCG
    ("PF001", "Aashirvaad Atta 5kg", "Packaged FMCG", "pcs", 275.0),
    ("PF002", "Fortune Sunflower Oil 1L", "Packaged FMCG", "pcs", 140.0),
    ("PF003", "Tata Salt 1kg", "Packaged FMCG", "pcs", 28.0),
    ("PF004", "MDH Garam Masala 100g", "Packaged FMCG", "pcs", 85.0),
    ("PF005", "Maggi Noodles 70g", "Packaged FMCG", "pcs", 14.0),
    ("PF006", "Parle-G 800g", "Packaged FMCG", "pcs", 80.0),
    ("PF007", "Surf Excel 1kg", "Packaged FMCG", "pcs", 195.0),
    ("PF008", "Sugar 1kg", "Packaged FMCG", "pcs", 42.0),
    # Bakery
    ("BK001", "White Bread Loaf", "Bakery", "pcs", 35.0),
    ("BK002", "Whole Wheat Bread", "Bakery", "pcs", 45.0),
    ("BK003", "Pav (6-pack)", "Bakery", "pcs", 30.0),
    ("BK004", "Cake Rusk 400g", "Bakery", "pcs", 60.0),
    ("BK005", "Bun (4-pack)", "Bakery", "pcs", 40.0),
    # Beverages
    ("BV001", "Bisleri Water 1L", "Beverages", "pcs", 20.0),
    ("BV002", "Coca-Cola 2L", "Beverages", "pcs", 95.0),
    ("BV003", "Frooti 200ml", "Beverages", "pcs", 10.0),
    ("BV004", "Red Bull 250ml", "Beverages", "pcs", 115.0),
    ("BV005", "Aam Panna 500ml", "Beverages", "pcs", 35.0),
    ("BV006", "Tata Tea Gold 250g", "Beverages", "pcs", 130.0),
    ("BV007", "Nescafe Classic 50g", "Beverages", "pcs", 165.0),
    ("BV008", "Lassi 200ml", "Beverages", "pcs", 25.0),
    ("BV009", "Coconut Water 200ml", "Beverages", "pcs", 30.0),
    ("BV010", "Lemon Soda 300ml", "Beverages", "pcs", 15.0),
]

VENDORS = [
    ("FreshFarm Dairy", "freshfarm@vendor.demo", "Dairy & Eggs,Fruits & Vegetables", 4.2, 1),
    ("Sabzi Mandi Co", "sabzi@vendor.demo", "Fruits & Vegetables", 3.8, 2),
    ("Bakery Bros", "bakery@vendor.demo", "Bakery", 4.5, 1),
    ("Metro FMCG Supply", "metro@vendor.demo", "Packaged FMCG,Beverages", 4.0, 3),
    ("Kirana King", "kirana@vendor.demo", "Packaged FMCG,Dairy & Eggs", 3.5, 4),
    ("Green Valley Produce", "greenvalley@vendor.demo", "Fruits & Vegetables", 4.3, 2),
    ("Daily Beverages", "daily@vendor.demo", "Beverages", 3.9, 3),
    ("Annapurna Foods", "annapurna@vendor.demo", "Dairy & Eggs,Bakery,Packaged FMCG", 4.1, 2),
]


def seed() -> None:
    create_db_and_tables()

    with Session(engine) as session:
        if session.exec(select(Organization)).first():
            return

        # Buyer org
        buyer_org = Organization(
            name="QuickMart Dark Store",
            type=OrgType.BUYER,
            address="Indiranagar, Bangalore",
        )
        session.add(buyer_org)
        session.flush()

        # Buyer user
        buyer = User(
            email="buyer@aeros.demo",
            password_hash=hash_password("buyer123"),
            role=Role.BUYER,
            display_name="Rahul (Procurement)",
            org_id=buyer_org.id,
        )
        session.add(buyer)
        session.flush()
        session.add(UserDefaults(user_id=buyer.id))

        # Admin user
        admin = User(
            email="admin@aeros.demo",
            password_hash=hash_password("admin123"),
            role=Role.ADMIN,
            display_name="Admin",
        )
        session.add(admin)
        session.flush()
        session.add(UserDefaults(user_id=admin.id))

        # Categories
        cat_map: dict[str, Category] = {}
        for i, name in enumerate(CATEGORIES):
            cat = Category(name=name, sort_order=i)
            session.add(cat)
            session.flush()
            cat_map[name] = cat

        # SKUs
        for code, name, cat_name, unit, price in SKUS:
            sku = SKU(
                org_id=buyer_org.id,
                code=code,
                name=name,
                category_id=cat_map[cat_name].id,
                unit=unit,
                last_price=price,
            )
            session.add(sku)

        # Vendor orgs + users + vendor records
        for vname, vemail, vcats, score, rank in VENDORS:
            vorg = Organization(name=vname, type=OrgType.VENDOR)
            session.add(vorg)
            session.flush()

            vuser = User(
                email=vemail,
                password_hash=hash_password("vendor123"),
                role=Role.VENDOR,
                display_name=vname,
                org_id=vorg.id,
            )
            session.add(vuser)
            session.flush()
            session.add(UserDefaults(user_id=vuser.id))

            cat_ids = ",".join(
                str(cat_map[c.strip()].id) for c in vcats.split(",") if c.strip() in cat_map
            )
            vendor = Vendor(
                owning_buyer_org_id=buyer_org.id,
                vendor_user_id=vuser.id,
                vendor_org_id=vorg.id,
                name=vname,
                primary_email=vemail,
                category_ids_csv=cat_ids,
                performance_score=score,
                preferred_rank=rank,
                kyc_status=KYCStatus.APPROVED,
            )
            session.add(vendor)

        session.flush()

        # --- Demo RFx: dispatched with vendor invitations + one quoted offer ---
        now = datetime.now(UTC)
        rfx = RFxRun(
            buyer_id=buyer.id,
            title="Weekly Dairy & Produce Replenishment - W23",
            status=RFxStatus.DISPATCHED,
            response_deadline=now + timedelta(days=2),
            delivery_window_start=now + timedelta(days=3),
            delivery_window_end=now + timedelta(days=4),
        )
        session.add(rfx)
        session.flush()

        sku_items = [
            ("FV001", 200, "kg", 18.0),
            ("FV002", 150, "kg", 22.0),
            ("DE001", 300, "ltr", 56.0),
            ("DE004", 50, "kg", 320.0),
        ]
        sku_map = {}
        for code, qty, unit, target in sku_items:
            sku_found = session.exec(select(SKU).where(SKU.code == code)).first()
            if sku_found:
                li = RFxLineItem(
                    rfx_id=rfx.id,
                    sku_id=sku_found.id,
                    qty=qty,
                    unit_override=unit,
                    target_price=target,
                )
                session.add(li)
                session.flush()
                sku_map[code] = li

        vendors_to_invite = session.exec(
            select(Vendor).where(
                Vendor.primary_email.in_(  # type: ignore[attr-defined]
                    ["freshfarm@vendor.demo", "sabzi@vendor.demo", "kirana@vendor.demo"]
                )
            )
        ).all()

        import hashlib

        for v in vendors_to_invite:
            token_hash = hashlib.sha256(f"demo-token-{v.id}".encode()).hexdigest()
            rv = RFxVendor(
                rfx_id=rfx.id,
                vendor_id=v.id,
                correlation_token_hash=token_hash,
                dispatched_at=now,
                status=RFxVendorStatus.INVITED,
            )
            session.add(rv)
            session.flush()

            thread = Thread(rfx_id=rfx.id, vendor_id=v.id)
            session.add(thread)
            session.flush()

            msg = Message(
                thread_id=thread.id,
                sender_kind="system",
                channel="in_app",
                body_text=f"You have been invited to quote for: {rfx.title}",
            )
            session.add(msg)

        # Simulate one quoted vendor (FreshFarm Dairy)
        freshfarm = next(
            (v for v in vendors_to_invite if v.primary_email == "freshfarm@vendor.demo"),
            None,
        )
        if freshfarm:
            fv = session.exec(
                select(RFxVendor).where(
                    RFxVendor.rfx_id == rfx.id,
                    RFxVendor.vendor_id == freshfarm.id,
                )
            ).first()
            if fv:
                fv.status = RFxVendorStatus.QUOTED
                session.add(fv)

            import json

            line_items_json = json.dumps(
                [
                    {
                        "sku_name": "Tomato",
                        "unit_price": 16.5,
                        "qty": 200,
                        "unit": "kg",
                        "total": 3300,
                        "confidence": 0.92,
                    },
                    {
                        "sku_name": "Onion",
                        "unit_price": 20.0,
                        "qty": 150,
                        "unit": "kg",
                        "total": 3000,
                        "confidence": 0.88,
                    },
                    {
                        "sku_name": "Full Cream Milk",
                        "unit_price": 52.0,
                        "qty": 300,
                        "unit": "ltr",
                        "total": 15600,
                        "confidence": 0.95,
                    },
                    {
                        "sku_name": "Paneer",
                        "unit_price": 290.0,
                        "qty": 50,
                        "unit": "kg",
                        "total": 14500,
                        "confidence": 0.85,
                    },
                ]
            )
            offer = Offer(
                rfx_id=rfx.id,
                vendor_id=freshfarm.id,
                total_quote=36400.0,
                currency="INR",
                payment_terms="NET15",
                delivery_terms="doorstep",
                lead_time_hours=18,
                extraction_confidence_overall=0.90,
                line_items_json=line_items_json,
            )
            session.add(offer)

        session.commit()


if __name__ == "__main__":
    seed()
