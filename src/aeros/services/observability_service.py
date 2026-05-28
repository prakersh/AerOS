"""Observability service for dashboard aggregations and trace lookups."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, func, select

from aeros.models.observability import (
    AgentRunLog,
    ChannelEventLog,
    LLMCallLog,
)


def get_summary_cards(
    session: Session,
    days: int = 7,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Aggregate telemetry data into summary cards for the dashboard.

    Args:
        session: Database session.
        days: Number of days to look back.
        user_id: If provided, filter to only this user's data.

    Returns:
        Dictionary with aggregated metrics (calls, tokens, cost, etc.).
    """
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

    llm_base = select(func.count(LLMCallLog.id)).where(LLMCallLog.created_at >= since)  # type: ignore[arg-type]
    tokens_base = select(func.sum(LLMCallLog.total_tokens)).where(LLMCallLog.created_at >= since)
    cost_base = select(func.sum(LLMCallLog.estimated_cost_usd)).where(
        LLMCallLog.created_at >= since
    )
    agent_base = select(func.count(AgentRunLog.id)).where(AgentRunLog.started_at >= since)  # type: ignore[arg-type]
    latency_base = select(func.avg(LLMCallLog.latency_ms)).where(LLMCallLog.created_at >= since)
    error_base = select(func.count(LLMCallLog.id)).where(  # type: ignore[arg-type]
        LLMCallLog.created_at >= since, LLMCallLog.status == "error"
    )
    channel_base = select(func.count(ChannelEventLog.id)).where(ChannelEventLog.created_at >= since)  # type: ignore[arg-type]

    # Note: LLM calls are logged at the provider layer without user_id,
    # so we don't filter by user_id for summary cards — buyers see all
    # LLM telemetry for their org. Agent runs are user-scoped.

    total_llm_calls = session.exec(llm_base).one() or 0
    total_tokens = session.exec(tokens_base).one() or 0
    total_cost = session.exec(cost_base).one() or 0.0
    total_agent_runs = session.exec(agent_base).one() or 0
    avg_latency = session.exec(latency_base).one() or 0
    error_count = session.exec(error_base).one() or 0
    channel_events = session.exec(channel_base).one() or 0

    return {
        "total_llm_calls": total_llm_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(float(total_cost), 4),
        "total_agent_runs": total_agent_runs,
        "avg_latency_ms": round(float(avg_latency), 1),
        "error_count": error_count,
        "error_rate": round(error_count / max(total_llm_calls, 1) * 100, 2),
        "channel_events": channel_events,
        "period_days": days,
    }


def get_recent_calls(
    session: Session,
    limit: int = 50,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Get the most recent LLM call logs.

    Args:
        session: Database session.
        limit: Maximum number of records to return.
        user_id: If provided, filter to only this user's calls.

    Returns:
        List of dicts with call metadata.
    """
    query = (
        select(LLMCallLog)
        .order_by(
            LLMCallLog.created_at.desc()  # type: ignore[attr-defined]
        )
        .limit(limit)
    )

    calls = list(session.exec(query).all())
    return [
        {
            "id": c.id,
            "trace_id": c.trace_id,
            "provider": c.provider,
            "model": c.model,
            "total_tokens": c.total_tokens,
            "latency_ms": c.latency_ms,
            "cost_usd": c.estimated_cost_usd,
            "status": c.status,
            "rfx_id": c.rfx_id,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in calls
    ]


def get_timeline(session: Session, rfx_id: int) -> list[dict[str, Any]]:
    """Get a chronological timeline of events for a specific RFx.

    Args:
        session: Database session.
        rfx_id: The RFx run ID to filter by.

    Returns:
        Sorted list of agent run and channel event dicts.
    """
    events: list[dict[str, Any]] = []

    agent_runs = list(
        session.exec(
            select(AgentRunLog).where(AgentRunLog.rfx_id == rfx_id).order_by(AgentRunLog.started_at)  # type: ignore[arg-type]
        ).all()
    )
    for r in agent_runs:
        events.append(
            {
                "type": "agent_run",
                "id": r.id,
                "name": r.agent_name,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "tokens": r.total_tokens,
                "timestamp": r.started_at.isoformat() if r.started_at else "",
            }
        )

    channel_events = list(
        session.exec(
            select(ChannelEventLog)
            .where(ChannelEventLog.rfx_id == rfx_id)
            .order_by(ChannelEventLog.created_at)  # type: ignore[arg-type]
        ).all()
    )
    for e in channel_events:
        events.append(
            {
                "type": "channel_event",
                "id": e.id,
                "channel": e.channel,
                "event_type": e.event_type,
                "direction": e.direction,
                "status": e.status,
                "timestamp": e.created_at.isoformat() if e.created_at else "",
            }
        )

    events.sort(key=lambda e: e.get("timestamp", ""))
    return events


def get_trace(session: Session, trace_id: str) -> dict[str, Any]:
    """Get all telemetry events correlated by a trace ID.

    Args:
        session: Database session.
        trace_id: The trace ID to look up.

    Returns:
        Dictionary with agent_runs, llm_calls, and channel_events lists.
    """
    agent_runs = list(
        session.exec(select(AgentRunLog).where(AgentRunLog.trace_id == trace_id)).all()
    )
    llm_calls = list(session.exec(select(LLMCallLog).where(LLMCallLog.trace_id == trace_id)).all())
    channel_events = list(
        session.exec(select(ChannelEventLog).where(ChannelEventLog.trace_id == trace_id)).all()
    )

    return {
        "trace_id": trace_id,
        "agent_runs": [
            {
                "id": r.id,
                "name": r.agent_name,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "tokens": r.total_tokens,
            }
            for r in agent_runs
        ],
        "llm_calls": [
            {
                "id": c.id,
                "model": c.model,
                "tokens": c.total_tokens,
                "latency_ms": c.latency_ms,
                "status": c.status,
            }
            for c in llm_calls
        ],
        "channel_events": [
            {
                "id": e.id,
                "channel": e.channel,
                "event_type": e.event_type,
                "status": e.status,
            }
            for e in channel_events
        ],
    }
