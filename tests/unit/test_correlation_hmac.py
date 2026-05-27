from unittest.mock import PropertyMock, patch

import aeros.security.hmac as hmac_module
from aeros.security.hmac import generate_correlation_token, verify_correlation_token


def _with_secret(fn):
    """Run fn with a deterministic HMAC secret."""
    original = hmac_module.settings.hmac_secret
    try:
        object.__setattr__(hmac_module.settings, "hmac_secret", "test-secret-key")
        return fn()
    except (AttributeError, TypeError):
        hmac_module.settings.hmac_secret = "test-secret-key"
        return fn()
    finally:
        try:
            object.__setattr__(hmac_module.settings, "hmac_secret", original)
        except (AttributeError, TypeError):
            hmac_module.settings.hmac_secret = original


def test_roundtrip():
    def _run():
        token, token_hash = generate_correlation_token(42, 7)
        result = verify_correlation_token(token)
        assert result is not None
        rfx_id, vendor_id, nonce = result
        assert rfx_id == 42
        assert vendor_id == 7
        assert len(nonce) > 0
    _with_secret(_run)


def test_tampered_signature():
    def _run():
        token, _ = generate_correlation_token(1, 2)
        tampered = token[:-4] + "xxxx"
        assert verify_correlation_token(tampered) is None
    _with_secret(_run)


def test_missing_signature():
    assert verify_correlation_token("no_dot_here") is None


def test_bad_format():
    def _run():
        token, _ = generate_correlation_token(1, 2)
        parts = token.rsplit(".", 1)
        bad = "bad_prefix." + parts[1]
        assert verify_correlation_token(bad) is None
    _with_secret(_run)
