"""System-wide settings (key-value pairs, admin-configurable)."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class SystemSetting(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str = ""
    value_type: str = "string"  # string, int, float, bool, json
    description: str = ""
    updated_by_user_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
