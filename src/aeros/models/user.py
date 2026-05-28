import enum
from datetime import datetime

from sqlmodel import Field, SQLModel


class Role(enum.StrEnum):
    BUYER = "buyer"
    VENDOR = "vendor"
    ADMIN = "admin"


class UserStatus(enum.StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: Role
    display_name: str
    telegram_chat_id: str | None = None
    notification_prefs_json: str = '{"email": true, "telegram": false, "in_app": true}'
    language_pref: str = "en"
    status: UserStatus = UserStatus.ACTIVE
    org_id: int | None = Field(default=None, foreign_key="organization.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: datetime | None = None
    suspended_at: datetime | None = None
    suspended_by_admin_id: int | None = None
