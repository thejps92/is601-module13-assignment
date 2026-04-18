from fastapi import status


def test_calculation_crud_flow(client):
    create_payload = {"a": 10, "b": 5, "type": "Add"}
    created_resp = client.post("/calculations", json=create_payload)
    assert created_resp.status_code == status.HTTP_201_CREATED

    created = created_resp.json()
    calc_id = created["id"]
    assert created["type"] == "add"
    assert created["result"] == 15

    list_resp = client.get("/calculations")
    assert list_resp.status_code == status.HTTP_200_OK
    assert any(item["id"] == calc_id for item in list_resp.json())

    get_resp = client.get(f"/calculations/{calc_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == calc_id

    update_payload = {"a": 20, "b": 2, "type": "Divide"}
    update_resp = client.put(f"/calculations/{calc_id}", json=update_payload)
    assert update_resp.status_code == status.HTTP_200_OK
    assert update_resp.json()["type"] == "divide"
    assert update_resp.json()["result"] == 10

    delete_resp = client.delete(f"/calculations/{calc_id}")
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

    missing_resp = client.get(f"/calculations/{calc_id}")
    assert missing_resp.status_code == status.HTTP_404_NOT_FOUND


def test_create_calculation_invalid_type_returns_400(client):
    resp = client.post("/calculations", json={"a": 1, "b": 2, "type": "modulus"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp.json()


def test_create_calculation_divide_by_zero_returns_400(client):
    resp = client.post("/calculations", json={"a": 10, "b": 0, "type": "Divide"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot divide by zero" in resp.json().get("error", "")


def test_get_calculation_invalid_uuid_returns_400(client):
    resp = client.get("/calculations/not-a-uuid")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp.json()
