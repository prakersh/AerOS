"""Tests for aeros.services.ai_budget_service — circuit breaker and budget stubs."""

from datetime import UTC, datetime, timedelta

import pytest

from aeros.services.ai_budget_service import (
    CIRCUIT_BREAKER_MAX_ERRORS,
    CIRCUIT_BREAKER_WINDOW_SEC,
    BudgetExceededError,
    CircuitOpenError,
    _error_counts,
    check_circuit,
    record_error,
    reset_circuit,
)


@pytest.fixture(autouse=True)
def clear_error_state():
    """Reset global error counts before each test."""
    _error_counts.clear()
    yield
    _error_counts.clear()


class TestRecordError:
    def test_records_single_error(self) -> None:
        """Should record an error timestamp for a provider."""
        record_error("nvidia_nim")
        assert len(_error_counts["nvidia_nim"]) == 1

    def test_records_multiple_errors(self) -> None:
        """Should accumulate errors for the same provider."""
        for _ in range(3):
            record_error("groq")
        assert len(_error_counts["groq"]) == 3

    def test_separate_providers_independent(self) -> None:
        """Errors for different providers should be independent."""
        record_error("nvidia_nim")
        record_error("nvidia_nim")
        record_error("groq")

        assert len(_error_counts["nvidia_nim"]) == 2
        assert len(_error_counts["groq"]) == 1


class TestCheckCircuit:
    def test_no_errors_passes(self) -> None:
        """Check should pass when no errors recorded."""
        check_circuit("nvidia_nim")  # no exception

    def test_below_threshold_passes(self) -> None:
        """Check should pass when error count is below max."""
        for _ in range(CIRCUIT_BREAKER_MAX_ERRORS - 1):
            record_error("nvidia_nim")

        check_circuit("nvidia_nim")  # no exception

    def test_at_threshold_raises(self) -> None:
        """Check should raise CircuitOpenError at max errors."""
        for _ in range(CIRCUIT_BREAKER_MAX_ERRORS):
            record_error("nvidia_nim")

        with pytest.raises(CircuitOpenError, match="Circuit breaker open"):
            check_circuit("nvidia_nim")

    def test_above_threshold_raises(self) -> None:
        """Check should raise when errors exceed max."""
        for _ in range(CIRCUIT_BREAKER_MAX_ERRORS + 3):
            record_error("groq")

        with pytest.raises(CircuitOpenError):
            check_circuit("groq")

    def test_old_errors_expire(self) -> None:
        """Errors outside the window should not count."""
        past = datetime.now(UTC) - timedelta(seconds=CIRCUIT_BREAKER_WINDOW_SEC + 10)
        _error_counts["nvidia_nim"] = [past] * CIRCUIT_BREAKER_MAX_ERRORS

        # Old errors should have expired; circuit should be closed
        check_circuit("nvidia_nim")  # no exception


class TestResetCircuit:
    def test_reset_clears_errors(self) -> None:
        """Reset should clear all errors for a provider."""
        for _ in range(CIRCUIT_BREAKER_MAX_ERRORS):
            record_error("nvidia_nim")

        reset_circuit("nvidia_nim")

        # Should no longer raise
        check_circuit("nvidia_nim")
        assert "nvidia_nim" not in _error_counts

    def test_reset_nonexistent_provider_no_error(self) -> None:
        """Resetting a provider with no errors should not raise."""
        reset_circuit("unknown_provider")  # no exception


class TestExceptionTypes:
    def test_budget_exceeded_is_exception(self) -> None:
        """BudgetExceededError should be a proper Exception subclass."""
        with pytest.raises(BudgetExceededError):
            raise BudgetExceededError("over limit")

    def test_circuit_open_is_exception(self) -> None:
        """CircuitOpenError should be a proper Exception subclass."""
        with pytest.raises(CircuitOpenError):
            raise CircuitOpenError("breaker tripped")
