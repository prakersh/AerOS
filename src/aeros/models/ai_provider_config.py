"""DB-backed AI provider configuration."""

import enum
from datetime import datetime

from sqlmodel import Field, SQLModel


class ProviderStatus(enum.StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class AIProviderConfig(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    provider_name: str = Field(index=True)  # "mimo", "nvidia_nim", "groq", "anthropic"
    model_id: str  # "mimo-v2.5"
    display_name: str = ""
    capability: str = "chat"  # chat, vision, asr, embedding
    is_default: bool = False
    status: ProviderStatus = ProviderStatus.ACTIVE
    api_key_env_var: str = ""  # which env var holds the key
    base_url: str = ""
    max_tokens: int = 4096
    config_json: str = "{}"  # extra provider-specific config
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
