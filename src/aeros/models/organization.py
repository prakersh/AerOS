import enum
from datetime import datetime

from sqlmodel import Field, SQLModel


class OrgType(str, enum.Enum):
    BUYER = "buyer"
    VENDOR = "vendor"


class Organization(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    type: OrgType
    gst_number: str | None = None
    address: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
