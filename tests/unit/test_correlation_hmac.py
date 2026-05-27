import hashlib
import hmac as stdlib_hmac
import secrets

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="function")

SECRET = "test-secret-key-for-unit-tests"


def _generate(rfx_id: int, vendor_id: int, secret: str) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(16)
    raw = f"rfx_{rfx_id}_{vendor_id}_{nonce}"
    sig = stdlib_hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    token = f"{raw}.{sig}"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def _verify(token: str, secret: str) -> tuple[int, int, str] | None:
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None
    raw, sig = parts
    expected = stdlib_hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not stdlib_hmac.compare_digest(sig, expected):
        return None
    segments = raw.split("_", 3)
    if len(segments) != 4 or segments[0] != "rfx":
        return None
    try:
        rfx_id = int(segments[1])
        vendor_id = int(segments[2])
    except ValueError:
        return None
    return rfx_id, vendor_id, segments[3]


async def test_roundtrip():
    token, token_hash = _generate(42, 7, SECRET)
    result = _verify(token, SECRET)
    assert result is not None
    rfx_id, vendor_id, nonce = result
    assert rfx_id == 42
    assert vendor_id == 7
    assert len(nonce) > 0


async def test_tampered_signature():
    token, _ = _generate(1, 2, SECRET)
    tampered = token[:-4] + "xxxx"
    assert _verify(tampered, SECRET) is None


async def test_missing_signature():
    assert _verify("no_dot_here", SECRET) is None


async def test_bad_format():
    token, _ = _generate(1, 2, SECRET)
    parts = token.rsplit(".", 1)
    bad = "bad_prefix." + parts[1]
    assert _verify(bad, SECRET) is None
