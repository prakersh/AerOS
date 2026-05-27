import hashlib
import hmac
import secrets

from aeros.config import settings


def generate_correlation_token(rfx_id: int, vendor_id: int) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(16)
    raw = f"rfx_{rfx_id}_{vendor_id}_{nonce}"
    sig = hmac.new(settings.hmac_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    token = f"{raw}.{sig}"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def verify_correlation_token(token: str) -> tuple[int, int, str] | None:
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None
    raw, sig = parts
    expected = hmac.new(settings.hmac_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    segments = raw.split("_", 3)
    if len(segments) != 4 or segments[0] != "rfx":
        return None
    try:
        rfx_id = int(segments[1])
        vendor_id = int(segments[2])
    except ValueError:
        return None
    nonce = segments[3]
    return rfx_id, vendor_id, nonce
