from datetime import datetime

from sqlmodel import Field, SQLModel


class LLMCache(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content_hash: str = Field(index=True)
    provider: str
    model: str
    prompt_hash: str
    response_json: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
