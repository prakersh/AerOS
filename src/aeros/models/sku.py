from datetime import datetime

from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    sort_order: int = 0


class SKU(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    org_id: int = Field(foreign_key="organization.id", index=True)
    code: str = Field(index=True)
    name: str
    category_id: int = Field(foreign_key="category.id")
    unit: str  # kg, g, ltr, ml, pcs, dozen, crate
    pack_size: float | None = None
    reorder_point: float = 0
    last_price: float | None = None
    last_vendor_id: int | None = None
    image_url: str | None = None
    aliases_json: str = "[]"
    gst_pct: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
