"""Telemetry data retention and cleanup worker."""

from datetime import UTC, datetime, timedelta

import structlog
from sqlmodel import Session, select

from aeros.db import engine
from aeros.models.observability import (
    AgentRunLog,
    ChannelEventLog,
    LLMCallLog,
    PipelineReport,
)

logger = structlog.get_logger()


def cleanup_old_telemetry(retention_days: int = 30) -> dict[str, int]:
    """Delete telemetry records older than retention_days.

    Args:
        retention_days: Number of days to retain data (default 30).

    Returns:
        Dictionary with counts of deleted records per model type.
    """
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    deleted: dict[str, int] = {
        "llm_calls": 0,
        "agent_runs": 0,
        "channel_events": 0,
        "pipeline_reports": 0,
    }

    with Session(engine) as session:
        for model_class, key in [
            (LLMCallLog, "llm_calls"),
            (AgentRunLog, "agent_runs"),
            (ChannelEventLog, "channel_events"),
            (PipelineReport, "pipeline_reports"),
        ]:
            old = list(
                session.exec(select(model_class).where(model_class.created_at < cutoff)).all()
            )
            for record in old:
                session.delete(record)
            deleted[key] = len(old)

        session.commit()

    logger.info(
        "telemetry.retention.cleanup",
        deleted=deleted,
        retention_days=retention_days,
    )
    return deleted
