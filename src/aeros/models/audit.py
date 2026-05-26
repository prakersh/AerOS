from datetime import datetime

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int | None = None
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_id: str
    before_json: str | None = None
    after_json: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
