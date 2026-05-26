"""Correlation token management for omnichannel reply routing."""

from aeros.security.hmac import generate_correlation_token, verify_correlation_token

__all__ = ["generate_correlation_token", "verify_correlation_token"]
