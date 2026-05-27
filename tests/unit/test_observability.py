"""Tests for telemetry and observability services."""

import json

import pytest
from sqlalchemy import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aeros.services import observability_service, telemetry_service


@pytest.fixture
def obs_session():
    """In-memory SQLite session with observability tables created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# ---- telemetry_service tests ----


def test_log_llm_call(obs_session):
    """Should persist an LLMCallLog with computed total_tokens and cost."""
    entry = telemetry_service.log_llm_call(
        obs_session,
        trace_id="trace-001",
        provider="openai",
        model="gpt-4o",
        prompt_tokens=500,
        completion_tokens=200,
        latency_ms=350,
        status="success",
        input_preview="Hello, can you help me with procurement?",
        output_preview="Sure, I can help you with procurement tasks.",
        rfx_id=10,
        user_id=1,
    )
    assert entry.id is not None
    assert entry.total_tokens == 700
    assert entry.estimated_cost_usd > 0
    assert entry.trace_id == "trace-001"
    assert entry.status == "success"


def test_log_llm_call_generates_trace_id(obs_session):
    """Should auto-generate a trace_id when none is provided."""
    entry = telemetry_service.log_llm_call(
        obs_session,
        provider="nvidia",
        model="nvidia/llama-3.1-nemotron-70b-instruct",
        prompt_tokens=100,
        completion_tokens=50,
    )
    assert entry.trace_id != ""
    assert len(entry.trace_id) > 10  # UUID format


def test_log_llm_call_redacts_pii(obs_session):
    """Should redact email addresses and PII from previews."""
    entry = telemetry_service.log_llm_call(
        obs_session,
        model="gpt-4o",
        input_preview="Contact me at user@example.com for details",
        output_preview="PAN number is ABCDE1234F",
    )
    assert "user@example.com" not in entry.input_preview
    assert "[EMAIL]" in entry.input_preview
    assert "ABCDE1234F" not in entry.output_preview
    assert "[PAN]" in entry.output_preview


def test_start_and_complete_agent_run(obs_session):
    """Should create a running agent run and then complete it."""
    run = telemetry_service.start_agent_run(
        obs_session,
        trace_id="trace-002",
        agent_name="intake",
        rfx_id=5,
        user_id=1,
        input_preview="Process this RFQ document",
    )
    assert run.id is not None
    assert run.status == "running"
    assert run.completed_at is None

    completed = telemetry_service.complete_agent_run(
        obs_session,
        run,
        status="success",
        output_preview="Extracted 5 line items",
        total_llm_calls=3,
        total_tokens=1500,
        duration_ms=2500,
    )
    assert completed.status == "success"
    assert completed.completed_at is not None
    assert completed.total_llm_calls == 3
    assert completed.duration_ms == 2500


def test_log_channel_event(obs_session):
    """Should persist a ChannelEventLog with JSON metadata."""
    entry = telemetry_service.log_channel_event(
        obs_session,
        trace_id="trace-003",
        channel="email",
        event_type="send",
        rfx_id=7,
        vendor_id=12,
        direction="outbound",
        status="success",
        metadata={"subject": "RFQ #7 Invitation", "recipient_count": 3},
    )
    assert entry.id is not None
    assert entry.channel == "email"
    assert entry.event_type == "send"
    parsed_meta = json.loads(entry.metadata_json)
    assert parsed_meta["recipient_count"] == 3


def test_create_pipeline_report(obs_session):
    """Should persist a PipelineReport with summary JSON."""
    report = telemetry_service.create_pipeline_report(
        obs_session,
        trace_id="trace-004",
        rfx_id=7,
        pipeline_type="extraction",
        summary={"pages_processed": 10, "items_extracted": 25},
        total_steps=4,
        total_duration_ms=8000,
        total_tokens=5000,
        total_cost_usd=0.05,
        status="success",
    )
    assert report.id is not None
    assert report.pipeline_type == "extraction"
    parsed_summary = json.loads(report.summary_json)
    assert parsed_summary["pages_processed"] == 10


# ---- observability_service tests ----


def test_get_summary_cards_empty(obs_session):
    """Should return zero-value summary when no data exists."""
    summary = observability_service.get_summary_cards(obs_session, days=7)
    assert summary["total_llm_calls"] == 0
    assert summary["total_tokens"] == 0
    assert summary["total_cost_usd"] == 0.0
    assert summary["total_agent_runs"] == 0
    assert summary["error_rate"] == 0.0
    assert summary["period_days"] == 7


def test_get_summary_cards_with_data(obs_session):
    """Should aggregate LLM call data correctly."""
    telemetry_service.log_llm_call(
        obs_session,
        model="gpt-4o",
        prompt_tokens=1000,
        completion_tokens=500,
        latency_ms=200,
        status="success",
    )
    telemetry_service.log_llm_call(
        obs_session,
        model="gpt-4o",
        prompt_tokens=800,
        completion_tokens=300,
        latency_ms=150,
        status="error",
        error_message="Rate limit exceeded",
    )
    telemetry_service.start_agent_run(
        obs_session,
        agent_name="intake",
    )

    summary = observability_service.get_summary_cards(obs_session, days=7)
    assert summary["total_llm_calls"] == 2
    assert summary["total_tokens"] == 2600  # (1000+500) + (800+300)
    assert summary["total_agent_runs"] == 1
    assert summary["error_count"] == 1
    assert summary["error_rate"] == 50.0  # 1/2 * 100


def test_get_recent_calls(obs_session):
    """Should return recent LLM calls in descending order."""
    for i in range(3):
        telemetry_service.log_llm_call(
            obs_session,
            model=f"model-{i}",
            prompt_tokens=100 * (i + 1),
            completion_tokens=50,
        )

    calls = observability_service.get_recent_calls(obs_session, limit=2)
    assert len(calls) == 2
    # Most recent first
    assert calls[0]["model"] == "model-2"
    assert calls[1]["model"] == "model-1"


def test_get_trace(obs_session):
    """Should return all events grouped by trace_id."""
    trace = "trace-lookup-001"
    telemetry_service.log_llm_call(
        obs_session,
        trace_id=trace,
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
    )
    telemetry_service.start_agent_run(
        obs_session,
        trace_id=trace,
        agent_name="intake",
    )
    telemetry_service.log_channel_event(
        obs_session,
        trace_id=trace,
        channel="email",
        event_type="send",
    )

    result = observability_service.get_trace(obs_session, trace)
    assert result["trace_id"] == trace
    assert len(result["llm_calls"]) == 1
    assert len(result["agent_runs"]) == 1
    assert len(result["channel_events"]) == 1


def test_get_timeline(obs_session):
    """Should return agent runs and channel events for an RFx sorted by time."""
    rfx_id = 42
    telemetry_service.start_agent_run(
        obs_session,
        agent_name="intake",
        rfx_id=rfx_id,
    )
    telemetry_service.log_channel_event(
        obs_session,
        channel="email",
        event_type="send",
        rfx_id=rfx_id,
    )

    timeline = observability_service.get_timeline(obs_session, rfx_id)
    assert len(timeline) == 2
    types = {e["type"] for e in timeline}
    assert "agent_run" in types
    assert "channel_event" in types


def test_redact_truncates_long_text(obs_session):
    """Should truncate preview text to 200 chars after redaction."""
    long_text = "A" * 500
    entry = telemetry_service.log_llm_call(
        obs_session,
        model="gpt-4o",
        input_preview=long_text,
    )
    assert len(entry.input_preview) == 200
