"""Admin-managed maintenance types: CRUD, validation, and block-delete-if-in-use."""
import uuid

from tests.conftest import admin_headers, driver_headers

H = admin_headers


def _name() -> str:
    return f"mt-{uuid.uuid4().hex[:8]}"


def test_create_list_update_maintenance_type(client):
    created = client.post(
        "/maintenance-types",
        headers=H(),
        json={"name": _name(), "interval_km": 12000, "steps": ["קטן", "גדול"], "description": "x"},
    )
    assert created.status_code == 201
    tid = created.json()["id"]
    assert created.json()["steps"] == ["קטן", "גדול"]

    listed = client.get("/maintenance-types", headers=H())
    assert listed.status_code == 200
    assert any(t["id"] == tid for t in listed.json())

    patched = client.patch(f"/maintenance-types/{tid}", headers=H(), json={"interval_km": 8000, "steps": ["א", "ב", "ג"]})
    assert patched.status_code == 200
    assert patched.json()["interval_km"] == 8000
    assert patched.json()["steps"] == ["א", "ב", "ג"]


def test_validation_rejects_bad_input(client):
    base = {"name": _name(), "interval_km": 10000}
    assert client.post("/maintenance-types", headers=H(), json={**base, "steps": []}).status_code == 422
    assert client.post("/maintenance-types", headers=H(), json={**base, "name": _name(), "steps": ["קטן", "קטן"]}).status_code == 422
    assert client.post("/maintenance-types", headers=H(), json={"name": _name(), "interval_km": 0, "steps": ["קטן"]}).status_code == 422


def test_delete_blocked_when_in_use(client):
    mt = client.post("/maintenance-types", headers=H(), json={"name": _name(), "interval_km": 10000, "steps": ["קטן", "גדול"]}).json()
    plate = str(uuid.uuid4().int % 100_000_000).zfill(8)
    client.post("/vehicles", headers=H(), json={"licensing_plate": plate, "maintenance_type_id": mt["id"]})

    blocked = client.delete(f"/maintenance-types/{mt['id']}", headers=H())
    assert blocked.status_code == 409

    # an unused type deletes fine
    unused = client.post("/maintenance-types", headers=H(), json={"name": _name(), "interval_km": 5000, "steps": ["יחיד"]}).json()
    assert client.delete(f"/maintenance-types/{unused['id']}", headers=H()).status_code == 204


def test_forbidden_for_driver(client):
    resp = client.get("/maintenance-types", headers=driver_headers("00000000-0000-0000-0000-000000000000"))
    assert resp.status_code == 403
