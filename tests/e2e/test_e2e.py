import pytest


@pytest.mark.e2e
def test_homepage_shows_app_title(page, fastapi_server):
    page.goto("http://localhost:8000")
    assert page.inner_text("h1") == "Calculations App"
    assert "Welcome to the Calculations App" in page.inner_text("body")


@pytest.mark.e2e
def test_homepage_shows_auth_links(page, fastapi_server):
    page.goto("http://localhost:8000")
    assert page.is_visible("a:has-text('Login')")
    assert page.is_visible("a:has-text('Register')")