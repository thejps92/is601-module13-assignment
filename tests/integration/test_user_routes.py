from fastapi import status

from app.models.user import User


def test_register_user_persists_hashed_password(client, db_session):
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "Password123",
    }

    resp = client.post("/users/register", json=payload)
    assert resp.status_code == status.HTTP_201_CREATED

    body = resp.json()
    assert body["username"] == payload["username"]
    assert body["email"] == payload["email"]
    assert "id" in body
    assert "created_at" in body

    user = db_session.query(User).filter(User.username == payload["username"]).first()
    assert user is not None
    assert user.password_hash != payload["password"]
    assert user.verify(payload["password"]) is True


def test_register_duplicate_user_rejected(client):
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "Password123",
    }

    first = client.post("/users/register", json=payload)
    assert first.status_code == status.HTTP_201_CREATED

    second = client.post("/users/register", json=payload)
    assert second.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in second.json()


def test_login_success_and_wrong_password(client):
    register_payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "Password123",
    }
    client.post("/users/register", json=register_payload)

    ok = client.post(
        "/users/login",
        json={"username": "alice", "password": "Password123"},
    )
    assert ok.status_code == status.HTTP_200_OK
    assert ok.json()["username"] == "alice"

    bad = client.post(
        "/users/login",
        json={"username": "alice", "password": "WrongPass123"},
    )
    assert bad.status_code == status.HTTP_401_UNAUTHORIZED
    assert "error" in bad.json()
