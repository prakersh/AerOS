"""Observability API endpoints for buyer and admin dashboards."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from aeros.db import get_session
from aeros.models.user import Role
from aeros.security.auth_context import AuthContext, require_role
from aeros.services import observability_service

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/summary")
def get_summary(
    days: int = 7,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> dict:
    """Get aggregated summary cards for the observability dashboard.

    Args:
        days: Number of days to look back (default 7).
        session: Database session (injected).
        caller: Authenticated user context (must be BUYER or ADMIN).

    Returns:
        Dictionary with aggregated telemetry metrics.
    """
    return observability_service.get_summary_cards(session, days=days)


@router.get("/calls")
def get_calls(
    limit: int = 50,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> list[dict]:
    """Get recent LLM call logs.

    Args:
        limit: Maximum number of records (default 50).
        session: Database session (injected).
        caller: Authenticated user context (must be BUYER or ADMIN).

    Returns:
        List of recent LLM call log dicts.
    """
    return observability_service.get_recent_calls(session, limit=limit)


@router.get("/timeline/{rfx_id}")
def get_timeline(
    rfx_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> list[dict]:
    """Get chronological timeline of events for an RFx.

    Args:
        rfx_id: The RFx run ID.
        session: Database session (injected).
        caller: Authenticated user context (must be BUYER or ADMIN).

    Returns:
        Sorted list of agent run and channel event dicts.
    """
    return observability_service.get_timeline(session, rfx_id)


@router.get("/trace/{trace_id}")
def get_trace(
    trace_id: str,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.BUYER, Role.ADMIN),
) -> dict:
    """Get all telemetry events correlated by trace ID.

    Args:
        trace_id: The trace identifier string.
        session: Database session (injected).
        caller: Authenticated user context (must be BUYER or ADMIN).

    Returns:
        Dictionary with agent_runs, llm_calls, and channel_events.
    """
    return observability_service.get_trace(session, trace_id)
