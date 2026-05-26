from datetime import datetime

from sqlmodel import Field, SQLModel


class Award(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfxrun.id", index=True)
    decisions_json: str = "[]"
    awarded_at: datetime = Field(default_factory=datetime.utcnow)
    awarded_by_user_id: int = Field(foreign_key="user.id")
    po_pdf_path: str | None = None
    po_sent_status: str = "pending"
    po_sent_message_ids_csv: str = ""


class PurchaseOrder(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    award_id: int = Field(foreign_key="award.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id")
    po_number: str = Field(index=True)
    total_amount: float
    currency: str = "INR"
    terms_json: str = "{}"
    line_items_json: str = "[]"
    pdf_path: str | None = None
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    signed_at: datetime | None = None
