from aeros.services.auth_service import authenticate, hash_password, register_user, verify_password


def test_hash_and_verify():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_authenticate_valid(session, buyer_user):
    user = authenticate(session, "buyer@test.com", "test123")
    assert user is not None
    assert user.email == "buyer@test.com"


def test_authenticate_wrong_password(session, buyer_user):
    user = authenticate(session, "buyer@test.com", "wrong")
    assert user is None


def test_authenticate_nonexistent(session):
    user = authenticate(session, "nobody@test.com", "test123")
    assert user is None


def test_register_duplicate(session, buyer_user):
    import pytest
    with pytest.raises(ValueError, match="already registered"):
        register_user(session, "buyer@test.com", "pass", "Dup", "buyer")
