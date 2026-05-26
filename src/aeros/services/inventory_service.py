from sqlmodel import Session, select

from aeros.models.sku import Category, SKU


def list_categories(session: Session) -> list[Category]:
    return list(session.exec(select(Category).order_by(Category.sort_order)).all())


def list_skus(session: Session, org_id: int, category_id: int | None = None) -> list[SKU]:
    stmt = select(SKU).where(SKU.org_id == org_id)
    if category_id:
        stmt = stmt.where(SKU.category_id == category_id)
    return list(session.exec(stmt.order_by(SKU.name)).all())


def get_sku(session: Session, sku_id: int) -> SKU | None:
    return session.get(SKU, sku_id)


def search_skus(session: Session, org_id: int, query: str) -> list[SKU]:
    return list(
        session.exec(
            select(SKU)
            .where(SKU.org_id == org_id, SKU.name.contains(query))  # type: ignore[union-attr]
            .order_by(SKU.name)
            .limit(20)
        ).all()
    )
