import pytest
from fastapi import HTTPException

from app.auth.jwt import create_access_token, decode_access_token


def test_decode_access_token_returns_payload_for_valid_token():
    subject = "user-id-123"
    token = create_access_token(subject=subject)

    payload = decode_access_token(token)

    assert payload["sub"] == subject


def test_decode_access_token_raises_401_for_invalid_token():
    with pytest.raises(HTTPException) as excinfo:
        decode_access_token("not-a-jwt")

    exc = excinfo.value
    assert exc.status_code == 401
    assert exc.detail == "Could not validate credentials"
    assert exc.headers and exc.headers.get("WWW-Authenticate") == "Bearer"
