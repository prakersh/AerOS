from aeros.security.hmac import generate_correlation_token, verify_correlation_token


def test_roundtrip():
    token, token_hash = generate_correlation_token(42, 7)
    result = verify_correlation_token(token)
    assert result is not None
    rfx_id, vendor_id, nonce = result
    assert rfx_id == 42
    assert vendor_id == 7
    assert len(nonce) > 0


def test_tampered_signature():
    token, _ = generate_correlation_token(1, 2)
    tampered = token[:-4] + "xxxx"
    assert verify_correlation_token(tampered) is None


def test_missing_signature():
    assert verify_correlation_token("no_dot_here") is None


def test_bad_format():
    token, _ = generate_correlation_token(1, 2)
    parts = token.rsplit(".", 1)
    bad = "bad_prefix." + parts[1]
    assert verify_correlation_token(bad) is None
