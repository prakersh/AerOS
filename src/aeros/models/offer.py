from datetime import datetime

from sqlmodel import Field, SQLModel


class Offer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfxrun.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    line_items_json: str = "[]"
    total_quote: float | None = None
    currency: str = "INR"
    lead_time_hours: float | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    validity_until: datetime | None = None
    tax_treatment: str | None = None
    gst_pct: float | None = None
    additional_charges_json: str = "[]"
    vendor_remarks: str | None = None
    extraction_confidence_overall: float = 0.0
    source_message_ids_csv: str = ""
    raw_extraction_json: str | None = None
    manual_overrides_json: str = "{}"
    revision_no: int = 1
    superseded_by_offer_id: int | None = None
    is_late: bool = False
    total_quote_inr: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
