"""Per-RFx and per-user AI token budget tracking with circuit breaker."""

from datetime import UTC, datetime

from sqlmodel import Session

MAX_TOKENS_PER_RFX: int = 100_000
MAX_TOKENS_PER_USER_PER_DAY: int = 500_000
CIRCUIT_BREAKER_WINDOW_SEC: int = 60
CIRCUIT_BREAKER_MAX_ERRORS: int = 5


class BudgetExceededError(Exception):
    """Raised when an AI token budget is exceeded."""


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open for a provider."""


# Module-level mutable state for circuit breaker tracking.
_error_counts: dict[str, list[datetime]] = {}


def check_budget(
    session: Session,
    *,
    user_id: int,
    rfx_id: int | None = None,
    estimated_tokens: int = 0,
) -> bool:
    """Check whether an AI call is within budget.

    Token tracking requires observability models (Phase 9.5); stub for now.

    Args:
        session: Active database session.
        user_id: The user requesting the AI call.
        rfx_id: Optional RFx scope.
        estimated_tokens: Estimated token count for the call.

    Returns:
        True if within budget.
    """
    return True


def record_usage(
    session: Session,
    *,
    user_id: int,
    rfx_id: int | None = None,
    tokens_used: int = 0,
    model: str = "",
) -> None:
    """Record token usage for a completed AI call.

    Will integrate with telemetry_service once observability models land.

    Args:
        session: Active database session.
        user_id: The user who made the call.
        rfx_id: Optional RFx scope.
        tokens_used: Number of tokens consumed.
        model: The model identifier used.
    """
    pass


def record_error(provider: str) -> None:
    """Record an error for a provider (circuit breaker input).

    Old errors outside the window are pruned on each call.

    Args:
        provider: The provider name (e.g. "mimo", "nvidia_nim", "groq").
    """
    now = datetime.now(UTC)
    if provider not in _error_counts:
        _error_counts[provider] = []
    _error_counts[provider] = [
        t for t in _error_counts[provider] if (now - t).total_seconds() < CIRCUIT_BREAKER_WINDOW_SEC
    ]
    _error_counts[provider].append(now)


def check_circuit(provider: str) -> None:
    """Check whether the circuit breaker is open for a provider.

    Args:
        provider: The provider name.

    Raises:
        CircuitOpenError: If too many recent errors have occurred.
    """
    now = datetime.now(UTC)
    errors = _error_counts.get(provider, [])
    recent = [t for t in errors if (now - t).total_seconds() < CIRCUIT_BREAKER_WINDOW_SEC]
    if len(recent) >= CIRCUIT_BREAKER_MAX_ERRORS:
        raise CircuitOpenError(
            f"Circuit breaker open for {provider}: "
            f"{len(recent)} errors in {CIRCUIT_BREAKER_WINDOW_SEC}s"
        )


def reset_circuit(provider: str) -> None:
    """Reset the circuit breaker for a provider (clear all errors).

    Args:
        provider: The provider name.
    """
    _error_counts.pop(provider, None)
