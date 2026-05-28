"""Telemetry service for logging LLM calls, agent runs, and channel events."""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlmodel import Session

from aeros.ai.pricing import estimate_cost
from aeros.models.observability import (
    AgentRunLog,
    ChannelEventLog,
    LLMCallLog,
    PipelineReport,
)

logger = structlog.get_logger()


def generate_trace_id() -> str:
    """Generate a unique trace identifier.

    Returns:
        A UUID4 string for correlating related telemetry events.
    """
    return str(uuid.uuid4())


def _redact(text: str, max_len: int = 200) -> str:
    """Redact PII from text and truncate to max_len.

    Redacts email addresses, Aadhaar numbers, and PAN numbers.

    Args:
        text: The raw text to redact.
        max_len: Maximum length of the returned string.

    Returns:
        Redacted and truncated text.
    """
    if not text:
        return ""
    redacted = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[EMAIL]",
        text,
    )
    redacted = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[AADHAAR]", redacted)
    redacted = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN]", redacted)
    return redacted[:max_len]


def log_llm_call(
    session: Session,
    *,
    trace_id: str = "",
    agent_run_id: int | None = None,
    provider: str = "",
    model: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    status: str = "success",
    error_message: str | None = None,
    input_preview: str = "",
    output_preview: str = "",
    rfx_id: int | None = None,
    user_id: int | None = None,
) -> LLMCallLog:
    """Log an individual LLM API call with token counts and cost.

    Args:
        session: Database session.
        trace_id: Correlation ID (auto-generated if empty).
        agent_run_id: FK to the parent AgentRunLog, if applicable.
        provider: LLM provider name (e.g. "mimo", "openai", "nvidia").
        model: Model identifier string.
        prompt_tokens: Number of input tokens.
        completion_tokens: Number of output tokens.
        latency_ms: Round-trip latency in milliseconds.
        status: One of "success", "error", "timeout".
        error_message: Error details if status != "success".
        input_preview: Raw input text (will be redacted).
        output_preview: Raw output text (will be redacted).
        rfx_id: Associated RFx run ID, if applicable.
        user_id: Associated user ID, if applicable.

    Returns:
        The persisted LLMCallLog record.
    """
    total = prompt_tokens + completion_tokens
    cost = estimate_cost(model, prompt_tokens, completion_tokens)

    entry = LLMCallLog(
        trace_id=trace_id or generate_trace_id(),
        agent_run_id=agent_run_id,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        latency_ms=latency_ms,
        estimated_cost_usd=cost,
        status=status,
        error_message=error_message,
        input_preview=_redact(input_preview),
        output_preview=_redact(output_preview),
        rfx_id=rfx_id,
        user_id=user_id,
    )
    session.add(entry)
    session.flush()
    session.commit()
    session.refresh(entry)
    return entry


def start_agent_run(
    session: Session,
    *,
    trace_id: str = "",
    agent_name: str = "",
    rfx_id: int | None = None,
    user_id: int | None = None,
    input_preview: str = "",
) -> AgentRunLog:
    """Start tracking an agent run.

    Args:
        session: Database session.
        trace_id: Correlation ID (auto-generated if empty).
        agent_name: Name of the agent (e.g. "intake", "sourcing").
        rfx_id: Associated RFx run ID.
        user_id: User who triggered the run.
        input_preview: Raw input text (will be redacted).

    Returns:
        The persisted AgentRunLog record with status "running".
    """
    entry = AgentRunLog(
        trace_id=trace_id or generate_trace_id(),
        agent_name=agent_name,
        rfx_id=rfx_id,
        user_id=user_id,
        input_preview=_redact(input_preview),
        status="running",
    )
    session.add(entry)
    session.flush()
    session.commit()
    session.refresh(entry)
    return entry


def complete_agent_run(
    session: Session,
    run: AgentRunLog,
    *,
    status: str = "success",
    output_preview: str = "",
    error_message: str | None = None,
    total_llm_calls: int = 0,
    total_tokens: int = 0,
    duration_ms: int = 0,
) -> AgentRunLog:
    """Mark an agent run as completed (success or error).

    Args:
        session: Database session.
        run: The AgentRunLog to update.
        status: Final status ("success" or "error").
        output_preview: Raw output text (will be redacted).
        error_message: Error details if status == "error".
        total_llm_calls: Number of LLM calls made during the run.
        total_tokens: Total tokens consumed across all LLM calls.
        duration_ms: Total wall-clock duration in milliseconds.

    Returns:
        The updated AgentRunLog record.
    """
    run.status = status
    run.output_preview = _redact(output_preview)
    run.error_message = error_message
    run.total_llm_calls = total_llm_calls
    run.total_tokens = total_tokens
    run.total_estimated_cost_usd = estimate_cost("", total_tokens, 0)
    run.duration_ms = duration_ms
    run.completed_at = datetime.now(UTC).replace(tzinfo=None)
    session.add(run)
    session.flush()
    session.commit()
    session.refresh(run)
    return run


def log_channel_event(
    session: Session,
    *,
    trace_id: str = "",
    channel: str = "",
    event_type: str = "",
    rfx_id: int | None = None,
    vendor_id: int | None = None,
    direction: str = "outbound",
    status: str = "success",
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ChannelEventLog:
    """Log a communication channel event (email, telegram, in-app).

    Args:
        session: Database session.
        trace_id: Correlation ID (auto-generated if empty).
        channel: Channel name ("email", "telegram", "in_app").
        event_type: Event type ("send", "receive", "bounce", etc.).
        rfx_id: Associated RFx run ID.
        vendor_id: Associated vendor ID.
        direction: "outbound" or "inbound".
        status: "success" or "error".
        error_message: Error details if status == "error".
        metadata: Additional event metadata as a dict.

    Returns:
        The persisted ChannelEventLog record.
    """
    entry = ChannelEventLog(
        trace_id=trace_id or generate_trace_id(),
        channel=channel,
        event_type=event_type,
        rfx_id=rfx_id,
        vendor_id=vendor_id,
        direction=direction,
        status=status,
        error_message=error_message,
        metadata_json=json.dumps(metadata or {}),
    )
    session.add(entry)
    session.flush()
    session.commit()
    session.refresh(entry)
    return entry


def create_pipeline_report(
    session: Session,
    *,
    trace_id: str = "",
    rfx_id: int | None = None,
    pipeline_type: str = "",
    summary: dict[str, Any] | None = None,
    total_steps: int = 0,
    total_duration_ms: int = 0,
    total_tokens: int = 0,
    total_cost_usd: float = 0.0,
    status: str = "success",
) -> PipelineReport:
    """Create a pipeline execution report.

    Args:
        session: Database session.
        trace_id: Correlation ID (auto-generated if empty).
        rfx_id: Associated RFx run ID.
        pipeline_type: Type of pipeline ("intake", "extraction", etc.).
        summary: Summary data as a dict.
        total_steps: Number of pipeline steps executed.
        total_duration_ms: Total duration in milliseconds.
        total_tokens: Total tokens consumed.
        total_cost_usd: Total estimated cost in USD.
        status: "success" or "error".

    Returns:
        The persisted PipelineReport record.
    """
    entry = PipelineReport(
        trace_id=trace_id or generate_trace_id(),
        rfx_id=rfx_id,
        pipeline_type=pipeline_type,
        summary_json=json.dumps(summary or {}),
        total_steps=total_steps,
        total_duration_ms=total_duration_ms,
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
        status=status,
    )
    session.add(entry)
    session.flush()
    session.commit()
    session.refresh(entry)
    return entry
