import uuid

import pytest


@pytest.mark.e2e
def test_register_success_shows_success_message(page, fastapi_server):
    username = f"user_{uuid.uuid4().hex[:10]}"
    email = f"e2e_{uuid.uuid4().hex[:10]}@example.com"
    password = "Password123"

    page.goto("http://localhost:8000/register")
    page.fill("#username", username)
    page.fill("#email", email)
    page.fill("#first_name", "E2E")
    page.fill("#last_name", "User")
    page.fill("#password", password)
    page.fill("#confirm_password", password)
    page.click("#registrationForm button[type='submit']")

    page.wait_for_selector("#successAlert", state="visible")
    assert "Registration successful" in page.inner_text("#successAlert")


@pytest.mark.e2e
def test_register_short_password_shows_error(page, fastapi_server):
    username = f"user_{uuid.uuid4().hex[:10]}"
    email = f"e2e_{uuid.uuid4().hex[:10]}@example.com"
    short_password = "short"

    page.goto("http://localhost:8000/register")
    page.fill("#username", username)
    page.fill("#email", email)
    page.fill("#first_name", "E2E")
    page.fill("#last_name", "User")
    page.fill("#password", short_password)
    page.fill("#confirm_password", short_password)
    page.click("#registrationForm button[type='submit']")

    page.wait_for_selector("#errorAlert", state="visible")
    assert "at least 8 characters" in page.inner_text("#errorAlert")


@pytest.mark.e2e
def test_login_success_stores_token(page, fastapi_server):
    username = f"user_{uuid.uuid4().hex[:10]}"
    email = f"e2e_{uuid.uuid4().hex[:10]}@example.com"
    password = "Password123"

    # Register via UI
    page.goto("http://localhost:8000/register")
    page.fill("#username", username)
    page.fill("#email", email)
    page.fill("#first_name", "E2E")
    page.fill("#last_name", "User")
    page.fill("#password", password)
    page.fill("#confirm_password", password)
    page.click("#registrationForm button[type='submit']")
    page.wait_for_selector("#successAlert", state="visible")

    # Clear any stored token so we can assert login stores it
    page.evaluate("() => localStorage.clear()")

    # Login via UI
    page.goto("http://localhost:8000/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#loginForm button[type='submit']")

    page.wait_for_function("() => !!localStorage.getItem('access_token')")

    token = page.evaluate("() => localStorage.getItem('access_token')")
    assert token is not None and len(token) > 0


@pytest.mark.e2e
def test_login_wrong_password_shows_error(page, fastapi_server):
    username = f"user_{uuid.uuid4().hex[:10]}"
    email = f"e2e_{uuid.uuid4().hex[:10]}@example.com"
    password = "Password123"

    # Register via UI
    page.goto("http://localhost:8000/register")
    page.fill("#username", username)
    page.fill("#email", email)
    page.fill("#first_name", "E2E")
    page.fill("#last_name", "User")
    page.fill("#password", password)
    page.fill("#confirm_password", password)
    page.click("#registrationForm button[type='submit']")
    page.wait_for_selector("#successAlert", state="visible")

    # Attempt login with wrong password
    page.goto("http://localhost:8000/login")
    page.fill("#username", username)
    page.fill("#password", "WrongPass123")
    page.click("#loginForm button[type='submit']")

    page.wait_for_selector("#errorAlert", state="visible")
    message = page.inner_text("#errorAlert").lower()
    assert ("login failed" in message) or ("invalid" in message)
