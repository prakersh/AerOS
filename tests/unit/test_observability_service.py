"""Tests for observability_service — dashboard aggregations and trace lookups."""

from datetime import UTC, datetime, timedelta

import pytest

from aeros.models.observability import (
    AgentRunLog,
    ChannelEventLog,
    LLMCallLog,
)
from aeros.services import observability_service


@pytest.fixture
def sample_llm_calls(session):
    """Create sample LLM call log entries."""
    now = datetime.now(UTC)
    calls = [
        LLMCallLog(
            trace_id="trace-1",
            provider="nvidia_nim",
            model="nemotron-70b",
            total_tokens=500,
            latency_ms=1200,
            estimated_cost_usd=0.01,
            status="success",
            created_at=now - timedelta(days=1),
        ),
        LLMCallLog(
            trace_id="trace-2",
            provider="groq",
            model="whisper-v3",
            total_tokens=200,
            latency_ms=800,
            estimated_cost_usd=0.005,
            status="error",
            error_message="timeout",
            created_at=now - timedelta(days=2),
        ),
    ]
    for c in calls:
        session.add(c)
    session.commit()
    for c in calls:
        session.refresh(c)
    return calls


@pytest.fixture
def sample_agent_runs(session):
    """Create sample agent run log entries."""
    now = datetime.now(UTC)
    runs = [
        AgentRunLog(
            trace_id="trace-1",
            agent_name="intake",
            rfx_id=1,
            status="success",
            total_tokens=1000,
            duration_ms=5000,
            started_at=now - timedelta(days=1),
        ),
        AgentRunLog(
            trace_id="trace-2",
            agent_name="evaluation",
            rfx_id=1,
            status="error",
            total_tokens=300,
            duration_ms=2000,
            started_at=now - timedelta(days=2),
        ),
    ]
    for r in runs:
        session.add(r)
    session.commit()
    for r in runs:
        session.refresh(r)
    return runs


@pytest.fixture
def sample_channel_events(session):
    """Create sample channel event log entries."""
    now = datetime.now(UTC)
    events = [
        ChannelEventLog(
            trace_id="trace-1",
            channel="email",
            event_type="send",
            rfx_id=1,
            direction="outbound",
            status="success",
            created_at=now - timedelta(days=1),
        ),
    ]
    for e in events:
        session.add(e)
    session.commit()
    for e in events:
        session.refresh(e)
    return events


class TestGetSummaryCards:
    def test_empty_db_returns_zeros(self, session):
        """Should return zeros when no data exists."""
        result = observability_service.get_summary_cards(session, days=7)
        assert result["total_llm_calls"] == 0
        assert result["total_tokens"] == 0
        assert result["total_cost_usd"] == 0.0
        assert result["total_agent_runs"] == 0
        assert result["channel_events"] == 0
        assert result["period_days"] == 7

    def test_with_data(self, session, sample_llm_calls, sample_agent_runs, sample_channel_events):
        """Should aggregate data correctly."""
        result = observability_service.get_summary_cards(session, days=30)
        assert result["total_llm_calls"] == 2
        assert result["total_tokens"] == 700
        assert result["total_agent_runs"] == 2
        assert result["channel_events"] == 1
        assert result["error_count"] == 1
        assert result["error_rate"] == 50.0

    def test_custom_days(self, session, sample_llm_calls):
        """Should respect custom days parameter."""
        result = observability_service.get_summary_cards(session, days=3)
        # Both calls are within 3 days
        assert result["total_llm_calls"] == 2
        # With 1 day filter, only the 1-day-old call should show
        result_1d = observability_service.get_summary_cards(session, days=1)
        assert result_1d["total_llm_calls"] <= 2


class TestGetRecentCalls:
    def test_empty_returns_empty_list(self, session):
        """Should return empty list when no calls exist."""
        result = observability_service.get_recent_calls(session)
        assert result == []

    def test_returns_call_details(self, session, sample_llm_calls):
        """Should return formatted call details."""
        result = observability_service.get_recent_calls(session, limit=10)
        assert len(result) == 2
        for call in result:
            assert "id" in call
            assert "trace_id" in call
            assert "provider" in call
            assert "model" in call
            assert "total_tokens" in call
            assert "status" in call

    def test_limit_respected(self, session, sample_llm_calls):
        """Should limit results."""
        result = observability_service.get_recent_calls(session, limit=1)
        assert len(result) == 1


class TestGetTimeline:
    def test_empty_timeline(self, session):
        """Should return empty list for RFx with no events."""
        result = observability_service.get_timeline(session, rfx_id=999)
        assert result == []

    def test_returns_sorted_events(self, session, sample_agent_runs, sample_channel_events):
        """Should return events sorted by timestamp."""
        result = observability_service.get_timeline(session, rfx_id=1)
        assert len(result) == 3  # 2 agent runs + 1 channel event
        # Should be sorted by timestamp
        for i in range(len(result) - 1):
            assert result[i]["timestamp"] <= result[i + 1]["timestamp"]

    def test_event_types_present(self, session, sample_agent_runs, sample_channel_events):
        """Should include both agent_run and channel_event types."""
        result = observability_service.get_timeline(session, rfx_id=1)
        types = {e["type"] for e in result}
        assert "agent_run" in types
        assert "channel_event" in types


class TestGetTrace:
    def test_empty_trace(self, session):
        """Should return empty lists for unknown trace."""
        result = observability_service.get_trace(session, "unknown-trace")
        assert result["trace_id"] == "unknown-trace"
        assert result["agent_runs"] == []
        assert result["llm_calls"] == []
        assert result["channel_events"] == []

    def test_returns_correlated_data(self, session, sample_llm_calls, sample_agent_runs):
        """Should return all data correlated by trace ID."""
        result = observability_service.get_trace(session, "trace-1")
        assert len(result["agent_runs"]) == 1
        assert len(result["llm_calls"]) == 1
        assert result["agent_runs"][0]["name"] == "intake"
        assert result["llm_calls"][0]["model"] == "nemotron-70b"
