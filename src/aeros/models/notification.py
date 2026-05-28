import enum
from datetime import datetime

from sqlmodel import Field, SQLModel


class NotificationStatus(enum.StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class Notification(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    channel: str  # email, telegram, in_app
    subject: str
    body: str
    status: NotificationStatus = NotificationStatus.QUEUED
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    sent_at: datetime | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
