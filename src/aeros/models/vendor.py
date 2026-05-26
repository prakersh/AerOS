import enum
from datetime import datetime

from sqlmodel import Field, SQLModel


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Vendor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owning_buyer_org_id: int = Field(foreign_key="organization.id", index=True)
    vendor_user_id: int | None = Field(default=None, foreign_key="user.id")
    vendor_org_id: int | None = Field(default=None, foreign_key="organization.id")
    name: str
    primary_email: str
    telegram_chat_id: str | None = None
    phone: str | None = None
    category_ids_csv: str = ""
    performance_score: float = 0.0
    preferred_rank: int = 0
    kyc_status: KYCStatus = KYCStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
