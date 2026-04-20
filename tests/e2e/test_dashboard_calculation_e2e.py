import uuid

import pytest


@pytest.mark.e2e
def test_dashboard_create_calculation_shows_in_history(page, fastapi_server):
    username = f"user_{uuid.uuid4().hex[:10]}"
    email = f"e2e_{uuid.uuid4().hex[:10]}@example.com"
    password = "Password123"

    # Ensure no prior session state in this browser context.
    page.goto("http://localhost:8000")
    page.evaluate("() => localStorage.clear()")

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

    # Login via UI (redirects to /dashboard)
    page.goto("http://localhost:8000/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#loginForm button[type='submit']")

    page.wait_for_url("**/dashboard")
    page.wait_for_selector("#calculationForm")

    # Wait for the initial history load to populate the table.
    page.wait_for_selector("#calculationsTable tr")
    existing_rows = len(page.query_selector_all(".delete-calc"))

    # Create a calculation using values unlikely to collide with existing data.
    a = int(uuid.uuid4().hex[:2], 16)
    b = int(uuid.uuid4().hex[2:4], 16)
    expected_result = a + b

    page.select_option("#calcType", "addition")
    page.fill("#calcInputs", f"{a},{b}")

    with page.expect_response(
        lambda resp: resp.url.endswith("/calculations")
        and resp.request.method == "POST"
    ) as create_resp_info:
        page.click("#calculationForm button[type='submit']")

    create_resp = create_resp_info.value
    assert create_resp.status == 201

    created = create_resp.json()
    assert created["a"] == a
    assert created["b"] == b
    assert created["type"] == "add"
    assert created["result"] == expected_result

    page.wait_for_selector("#successAlert", state="visible")
    assert "Calculation created successfully" in page.inner_text("#successAlert")

    # Table should refresh and include the new calculation.
    expected_rows = existing_rows + 1
    page.wait_for_function(
        f"() => document.querySelectorAll('.delete-calc').length === {expected_rows}",
    )
    assert page.is_visible(f"tr:has-text('{a}, {b}')")
