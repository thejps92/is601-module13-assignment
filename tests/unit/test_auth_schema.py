import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_register_request_allows_missing_confirm_password():
    req = RegisterRequest(
        username="alice",
        email="alice@example.com",
        password="Password123",
    )
    assert req.confirm_password is None


def test_register_request_accepts_matching_confirm_password():
    req = RegisterRequest(
        username="alice",
        email="alice@example.com",
        password="Password123",
        confirm_password="Password123",
    )
    assert req.password == req.confirm_password


def test_register_request_rejects_mismatched_confirm_password():
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            username="alice",
            email="alice@example.com",
            password="Password123",
            confirm_password="Different123",
        )

    assert "Passwords do not match" in str(excinfo.value)
