"""Seed demo data for AEROS dark-store persona."""

from datetime import UTC, datetime, timedelta
from typing import Any

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

        import hashlib
        import json

        now = datetime.now(UTC)

        def _invite_vendors(
            sess: Session,
            rfx_run: RFxRun,
            vendor_emails: list[str],
            ts: datetime,
        ) -> list[Vendor]:
            invited = list(
                sess.exec(
                    select(Vendor).where(
                        Vendor.primary_email.in_(vendor_emails)  # type: ignore[attr-defined]
                    )
                ).all()
            )
            for v in invited:
                tok = hashlib.sha256(f"demo-{rfx_run.id}-{v.id}".encode()).hexdigest()
                rv = RFxVendor(
                    rfx_id=rfx_run.id,
                    vendor_id=v.id,
                    correlation_token_hash=tok,
                    dispatched_at=ts,
                    status=RFxVendorStatus.INVITED,
                )
                sess.add(rv)
                sess.flush()
                thread = Thread(rfx_id=rfx_run.id, vendor_id=v.id)
                sess.add(thread)
                sess.flush()
                sess.add(
                    Message(
                        thread_id=thread.id,
                        sender_kind="system",
                        channel="in_app",
                        body_text=f"You have been invited to quote for: {rfx_run.title}",
                    )
                )
            return invited

        def _offer_li(
            li_map: dict[str, RFxLineItem],
            code: str,
            price: float,
            days: int,
            conf: float = 1.0,
        ) -> dict[str, Any]:
            return {
                "line_item_id": li_map[code].id,
                "unit_price": price,
                "lead_time_days": days,
                "confidence": conf,
            }

        # --- RFx #1: Dispatched, 2 quoted vendors + 1 invited ---
        rfx1 = RFxRun(
            buyer_id=buyer.id,
            title="Weekly Dairy & Produce Replenishment - W23",
            status=RFxStatus.DISPATCHED,
            response_deadline=now + timedelta(days=2),
            delivery_window_start=now + timedelta(days=3),
            delivery_window_end=now + timedelta(days=4),
            payment_terms_for_this_rfx="NET30",
            delivery_terms_for_this_rfx="doorstep",
            currency_for_this_rfx="INR",
            tax_treatment_for_this_rfx="exclusive",
        )
        session.add(rfx1)
        session.flush()

        rfx1_items = [
            ("FV001", 200, "kg", 18.0),
            ("FV002", 150, "kg", 22.0),
            ("DE001", 300, "ltr", 56.0),
            ("DE004", 50, "kg", 320.0),
        ]
        rfx1_li_map: dict[str, RFxLineItem] = {}
        for code, qty, unit, target in rfx1_items:
            sku_found = session.exec(select(SKU).where(SKU.code == code)).first()
            if sku_found:
                li = RFxLineItem(
                    rfx_id=rfx1.id,
                    sku_id=sku_found.id,
                    qty=qty,
                    unit_override=unit,
                    target_price=target,
                )
                session.add(li)
                session.flush()
                rfx1_li_map[code] = li

        rfx1_vendors = _invite_vendors(
            session,
            rfx1,
            ["freshfarm@vendor.demo", "sabzi@vendor.demo", "kirana@vendor.demo"],
            now - timedelta(hours=6),
        )

        # FreshFarm Dairy: quoted with competitive prices
        freshfarm = next((v for v in rfx1_vendors if "freshfarm" in (v.primary_email or "")), None)
        if freshfarm and rfx1_li_map:
            fv = session.exec(
                select(RFxVendor).where(
                    RFxVendor.rfx_id == rfx1.id, RFxVendor.vendor_id == freshfarm.id
                )
            ).first()
            if fv:
                fv.status = RFxVendorStatus.QUOTED
                session.add(fv)
            ff_thread = session.exec(
                select(Thread).where(Thread.rfx_id == rfx1.id, Thread.vendor_id == freshfarm.id)
            ).first()
            if ff_thread:
                session.add(
                    Message(
                        thread_id=ff_thread.id,
                        sender_kind="vendor",
                        channel="in_app",
                        body_text="Hi, we can supply all items. Prices competitive this week.",
                        sender_user_id=freshfarm.vendor_user_id,
                    )
                )
            session.add(
                Offer(
                    rfx_id=rfx1.id,
                    vendor_id=freshfarm.id,
                    total_quote=36400.0,
                    currency="INR",
                    payment_terms="NET15",
                    delivery_terms="doorstep",
                    lead_time_hours=18,
                    extraction_confidence_overall=0.95,
                    line_items_json=json.dumps(
                        [
                            _offer_li(rfx1_li_map, "FV001", 16.5, 1, 0.95),
                            _offer_li(rfx1_li_map, "FV002", 20.0, 1, 0.92),
                            _offer_li(rfx1_li_map, "DE001", 52.0, 1, 0.97),
                            _offer_li(rfx1_li_map, "DE004", 290.0, 2, 0.88),
                        ]
                    ),
                )
            )

        # Kirana King: quoted, slightly higher prices but faster delivery
        kirana = next((v for v in rfx1_vendors if "kirana" in (v.primary_email or "")), None)
        if kirana and rfx1_li_map:
            kv = session.exec(
                select(RFxVendor).where(
                    RFxVendor.rfx_id == rfx1.id, RFxVendor.vendor_id == kirana.id
                )
            ).first()
            if kv:
                kv.status = RFxVendorStatus.QUOTED
                session.add(kv)
            kr_thread = session.exec(
                select(Thread).where(Thread.rfx_id == rfx1.id, Thread.vendor_id == kirana.id)
            ).first()
            if kr_thread:
                session.add(
                    Message(
                        thread_id=kr_thread.id,
                        sender_kind="vendor",
                        channel="in_app",
                        body_text="We can deliver same day for dairy items. See our quote.",
                        sender_user_id=kirana.vendor_user_id,
                    )
                )
            session.add(
                Offer(
                    rfx_id=rfx1.id,
                    vendor_id=kirana.id,
                    total_quote=39750.0,
                    currency="INR",
                    payment_terms="NET30",
                    delivery_terms="doorstep",
                    lead_time_hours=6,
                    vendor_remarks="Same-day delivery for dairy. Paneer from our own unit.",
                    extraction_confidence_overall=1.0,
                    line_items_json=json.dumps(
                        [
                            _offer_li(rfx1_li_map, "FV001", 19.0, 1),
                            _offer_li(rfx1_li_map, "FV002", 23.0, 1),
                            _offer_li(rfx1_li_map, "DE001", 54.0, 0),
                            _offer_li(rfx1_li_map, "DE004", 310.0, 0),
                        ]
                    ),
                )
            )

        # Sabzi Mandi: still invited (viewed but not yet quoted)
        sabzi = next((v for v in rfx1_vendors if "sabzi" in (v.primary_email or "")), None)
        if sabzi:
            sv = session.exec(
                select(RFxVendor).where(
                    RFxVendor.rfx_id == rfx1.id, RFxVendor.vendor_id == sabzi.id
                )
            ).first()
            if sv:
                sv.status = RFxVendorStatus.VIEWED
                session.add(sv)

        # --- RFx #2: Awarded (completed lifecycle) ---
        rfx2 = RFxRun(
            buyer_id=buyer.id,
            title="Monthly FMCG Restock - May 2026",
            status=RFxStatus.AWARDED,
            response_deadline=now - timedelta(days=5),
            delivery_window_start=now - timedelta(days=2),
            delivery_window_end=now - timedelta(days=1),
            payment_terms_for_this_rfx="NET30",
            delivery_terms_for_this_rfx="warehouse pickup",
            currency_for_this_rfx="INR",
            tax_treatment_for_this_rfx="inclusive",
        )
        session.add(rfx2)
        session.flush()

        rfx2_items = [
            ("PF001", 100, "pcs", 275.0),
            ("PF002", 200, "pcs", 140.0),
            ("PF005", 500, "pcs", 14.0),
            ("BV002", 300, "pcs", 95.0),
        ]
        rfx2_li_map: dict[str, RFxLineItem] = {}
        for code, qty, unit, target in rfx2_items:
            sku_found = session.exec(select(SKU).where(SKU.code == code)).first()
            if sku_found:
                li = RFxLineItem(
                    rfx_id=rfx2.id,
                    sku_id=sku_found.id,
                    qty=qty,
                    unit_override=unit,
                    target_price=target,
                )
                session.add(li)
                session.flush()
                rfx2_li_map[code] = li

        rfx2_vendors = _invite_vendors(
            session,
            rfx2,
            ["metro@vendor.demo", "daily@vendor.demo"],
            now - timedelta(days=10),
        )

        metro = next((v for v in rfx2_vendors if "metro" in (v.primary_email or "")), None)
        if metro and rfx2_li_map:
            mv = session.exec(
                select(RFxVendor).where(
                    RFxVendor.rfx_id == rfx2.id, RFxVendor.vendor_id == metro.id
                )
            ).first()
            if mv:
                mv.status = RFxVendorStatus.QUOTED
                session.add(mv)
            session.add(
                Offer(
                    rfx_id=rfx2.id,
                    vendor_id=metro.id,
                    total_quote=62000.0,
                    currency="INR",
                    payment_terms="NET30",
                    delivery_terms="warehouse pickup",
                    lead_time_hours=48,
                    extraction_confidence_overall=1.0,
                    line_items_json=json.dumps(
                        [
                            _offer_li(rfx2_li_map, "PF001", 260.0, 2),
                            _offer_li(rfx2_li_map, "PF002", 132.0, 2),
                            _offer_li(rfx2_li_map, "PF005", 12.5, 1),
                            _offer_li(rfx2_li_map, "BV002", 88.0, 3),
                        ]
                    ),
                )
            )

        # --- RFx #3: Drafting (not yet dispatched) ---
        rfx3 = RFxRun(
            buyer_id=buyer.id,
            title="Bakery Supplies - Weekend Rush",
            status=RFxStatus.DRAFTING,
            response_deadline=now + timedelta(days=5),
            delivery_window_start=now + timedelta(days=6),
            delivery_window_end=now + timedelta(days=7),
            payment_terms_for_this_rfx="NET15",
            delivery_terms_for_this_rfx="doorstep",
            currency_for_this_rfx="INR",
            tax_treatment_for_this_rfx="exclusive",
        )
        session.add(rfx3)
        session.flush()

        rfx3_items = [
            ("BK001", 200, "pcs", 35.0),
            ("BK003", 300, "pcs", 30.0),
            ("BK005", 150, "pcs", 40.0),
        ]
        for code, qty, unit, target in rfx3_items:
            sku_found = session.exec(select(SKU).where(SKU.code == code)).first()
            if sku_found:
                session.add(
                    RFxLineItem(
                        rfx_id=rfx3.id,
                        sku_id=sku_found.id,
                        qty=qty,
                        unit_override=unit,
                        target_price=target,
                    )
                )

        session.commit()


if __name__ == "__main__":
    seed()
