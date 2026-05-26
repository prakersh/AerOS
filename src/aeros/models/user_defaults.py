from datetime import datetime

from sqlmodel import Field, SQLModel


class UserDefaults(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    payment_terms_default: str = "NET30"
    delivery_terms_default: str = "doorstep"
    quote_validity_days_default: int = 7
    currency_default: str = "INR"
    tax_treatment_default: str = "exclusive"
    delivery_window_default: str = "05:00-07:00"
    auto_reminder_hours_before_deadline: int = 12
    escalation_emails_csv: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)
