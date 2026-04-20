import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    return TestClient(main.app)


def test_root_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Welcome to the Calculations App" in resp.text


def test_healthcheck(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path,payload,expected",
    [
        ("/add", {"a": 10, "b": 5}, 15),
        ("/subtract", {"a": 10, "b": 5}, 5),
        ("/multiply", {"a": 10, "b": 5}, 50),
        ("/divide", {"a": 10, "b": 2}, 5),
    ],
)
def test_operation_routes_success(client, path, payload, expected):
    resp = client.post(path, json=payload)
    assert resp.status_code == 200
    assert resp.json()["result"] == expected


def test_divide_by_zero_returns_400(client):
    resp = client.post("/divide", json={"a": 10, "b": 0})
    assert resp.status_code == 400
    assert "Cannot divide by zero" in resp.json()["error"]


def test_validation_error_returns_400_and_error_field(client):
    resp = client.post("/add", json={"a": "not-a-number", "b": 1})
    assert resp.status_code == 400
    assert "error" in resp.json()
    assert "Both a and b must be numbers" in resp.json()["error"]


def test_http_exception_handler_format(client):
    # Trigger HTTPException via internal error path: monkeypatch add to raise
    original = main.add
    try:
        def boom(a, b):
            raise Exception("boom")

        main.add = boom
        resp = client.post("/add", json={"a": 1, "b": 2})
        assert resp.status_code == 400
        assert resp.json() == {"error": "boom"}
    finally:
        main.add = original


def test_divide_internal_error_returns_500(client):
    original = main.divide
    try:
        def boom(a, b):
            raise Exception("unexpected")

        main.divide = boom
        resp = client.post("/divide", json={"a": 1, "b": 2})
        assert resp.status_code == 500
        assert resp.json() == {"error": "Internal Server Error"}
    finally:
        main.divide = original


def test_subtract_exception_returns_400(client):
    original = main.subtract
    try:
        def boom(a, b):
            raise Exception("subtract boom")

        main.subtract = boom
        resp = client.post("/subtract", json={"a": 1, "b": 2})
        assert resp.status_code == 400
        assert resp.json() == {"error": "subtract boom"}
    finally:
        main.subtract = original


def test_multiply_exception_returns_400(client):
    original = main.multiply
    try:
        def boom(a, b):
            raise Exception("multiply boom")

        main.multiply = boom
        resp = client.post("/multiply", json={"a": 1, "b": 2})
        assert resp.status_code == 400
        assert resp.json() == {"error": "multiply boom"}
    finally:
        main.multiply = original
