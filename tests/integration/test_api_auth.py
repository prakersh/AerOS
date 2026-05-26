def test_login_success(client, buyer_user):
    resp = client.post("/api/auth/login", json={"email": "buyer@test.com", "password": "test123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "buyer@test.com"
    assert data["role"] == "buyer"
    assert "access_token" in resp.cookies


def test_login_wrong_password(client, buyer_user):
    resp = client.post("/api/auth/login", json={"email": "buyer@test.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me_without_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_auth(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "buyer@test.com"


def test_logout(auth_client):
    resp = auth_client.post("/api/auth/logout")
    assert resp.status_code == 200


def test_register_new_user(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "new@test.com",
            "password": "newpass123",
            "display_name": "New User",
            "role": "buyer",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@test.com"


def test_register_duplicate(client, buyer_user):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "buyer@test.com",
            "password": "whatever",
            "display_name": "Dup",
            "role": "buyer",
        },
    )
    assert resp.status_code == 409
