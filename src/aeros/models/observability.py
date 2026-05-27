"""Telemetry and observability data models for AEROS."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class LLMCallLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    trace_id: str = Field(index=True, default="")
    agent_run_id: int | None = Field(default=None, index=True)
    provider: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0
    status: str = "success"  # success, error, timeout
    error_message: str | None = None
    input_preview: str = ""  # first 200 chars of input (redacted)
    output_preview: str = ""  # first 200 chars of output (redacted)
    rfx_id: int | None = None
    user_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRunLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    trace_id: str = Field(index=True, default="")
    agent_name: str = ""
    rfx_id: int | None = None
    user_id: int | None = None
    input_preview: str = ""
    output_preview: str = ""
    status: str = "running"  # running, success, error
    error_message: str | None = None
    total_llm_calls: int = 0
    total_tokens: int = 0
    total_estimated_cost_usd: float = 0.0
    duration_ms: int = 0
    tool_calls_json: str = "[]"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class ChannelEventLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    trace_id: str = Field(index=True, default="")
    channel: str = ""  # email, telegram, in_app
    event_type: str = ""  # send, receive, delivery_confirmed, bounce, error
    rfx_id: int | None = None
    vendor_id: int | None = None
    direction: str = "outbound"  # outbound, inbound
    status: str = "success"
    error_message: str | None = None
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    trace_id: str = Field(index=True, default="")
    rfx_id: int | None = None
    pipeline_type: str = ""  # intake, extraction, evaluation, dispatch, po_generation
    summary_json: str = "{}"
    total_steps: int = 0
    total_duration_ms: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    status: str = "success"
    created_at: datetime = Field(default_factory=datetime.utcnow)
