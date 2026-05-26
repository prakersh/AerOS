from sqlmodel import Session, select

from aeros.models.vendor import Vendor


def list_vendors(session: Session, buyer_org_id: int) -> list[Vendor]:
    return list(
        session.exec(
            select(Vendor)
            .where(Vendor.owning_buyer_org_id == buyer_org_id)
            .order_by(Vendor.preferred_rank, Vendor.name)
        ).all()
    )


def get_vendor(session: Session, vendor_id: int) -> Vendor | None:
    return session.get(Vendor, vendor_id)


def vendors_for_category(session: Session, buyer_org_id: int, category_id: int) -> list[Vendor]:
    all_vendors = list_vendors(session, buyer_org_id)
    cat_str = str(category_id)
    return [v for v in all_vendors if cat_str in v.category_ids_csv.split(",")]
