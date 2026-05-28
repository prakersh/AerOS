import enum
from datetime import datetime

from sqlmodel import Field, SQLModel


class RFxType(enum.StrEnum):
    RFQ = "RFQ"
    RFI = "RFI"
    RFP = "RFP"


class RFxStatus(enum.StrEnum):
    DRAFTING = "drafting"
    AWAITING_APPROVAL = "awaiting_approval"
    DISPATCHED = "dispatched"
    COLLECTING = "collecting"
    COMPARING = "comparing"
    AWARDED = "awarded"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class RFxVendorStatus(enum.StrEnum):
    INVITED = "invited"
    VIEWED = "viewed"
    QUOTED = "quoted"
    DECLINED = "declined"
    EXPIRED = "expired"


class ExtractionStatus(enum.StrEnum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    FAILED = "failed"


class RFxRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    buyer_id: int = Field(foreign_key="user.id", index=True)
    type: RFxType = RFxType.RFQ
    status: RFxStatus = RFxStatus.DRAFTING
    title: str = ""
    delivery_window_start: datetime | None = None
    delivery_window_end: datetime | None = None
    response_deadline: datetime | None = None
    payment_terms_for_this_rfx: str = "NET30"
    delivery_terms_for_this_rfx: str = "doorstep"
    quote_validity_days_for_this_rfx: int = 7
    currency_for_this_rfx: str = "INR"
    tax_treatment_for_this_rfx: str = "exclusive"
    notes_for_vendors: str | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: int | None = None
    cancelled_reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RFxLineItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfxrun.id", index=True)
    sku_id: int = Field(foreign_key="sku.id")
    qty: float
    unit_override: str | None = None
    target_price: float | None = None
    target_lead_time_hours: float | None = None
    notes: str | None = None


class RFxVendor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfxrun.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    correlation_token_hash: str = ""
    dispatched_at: datetime | None = None
    last_seen_at: datetime | None = None
    status: RFxVendorStatus = RFxVendorStatus.INVITED
    decline_reason: str | None = None
    declined_at: datetime | None = None
    reminders_sent_json: str = "[]"
    line_item_ids_json: str | None = None  # JSON array of line item IDs; null = all items


class Thread(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfxrun.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="thread.id", index=True)
    sender_user_id: int | None = None
    sender_kind: str = "system"  # buyer, vendor, system, agent
    channel: str = "in_app"  # email, telegram, in_app, system
    body_text: str = ""
    body_html: str | None = None
    raw_payload_json: str | None = None
    parent_message_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Attachment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="message.id", index=True)
    filename: str
    mime_type: str
    storage_path: str
    size_bytes: int = 0
    sha256: str = ""
    extraction_status: ExtractionStatus = ExtractionStatus.PENDING
    extraction_attempts: int = 0
    extracted_at: datetime | None = None
