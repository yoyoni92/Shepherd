"""T9 - reports, events, and config endpoints."""
import uuid

from tests.conftest import admin_headers, driver_headers, customer_headers


def _make_vehicle(client) -> str:
    plate = f"REP-{uuid.uuid4().hex[:6]}"
    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    return r.json()["vehicle_id"]


# --- Reports ---

def test_create_report_admin(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/reports",
        json={"vehicle_id": vehicle_id, "ticket_type": "traffic", "amount": "150.00"},
        headers=admin_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["ticket_type"] == "traffic"
    assert data["status"] == "unpaid"


def test_list_reports_admin(client):
    vehicle_id = _make_vehicle(client)
    client.post("/reports", json={"vehicle_id": vehicle_id, "ticket_type": "parking"}, headers=admin_headers())
    r = client.get("/reports", headers=admin_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_report_driver_forbidden(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/reports",
        json={"vehicle_id": vehicle_id, "ticket_type": "traffic"},
        headers=driver_headers(str(uuid.uuid4())),
    )
    assert r.status_code == 403


# --- Events ---

def test_create_event_admin(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/events",
        json={
            "vehicle_id": vehicle_id,
            "event_type": "maintenance_due",
            "severity": "warning",
            "message": "Test event",
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["event_type"] == "maintenance_due"
    assert data["status"] == "open"


def test_list_events_admin(client):
    r = client.get("/events", headers=admin_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_events_driver_forbidden(client):
    r = client.get("/events", headers=driver_headers(str(uuid.uuid4())))
    assert r.status_code == 403


# --- Config ---

def test_get_config_any_role(client):
    r = client.get("/config", headers=admin_headers())
    assert r.status_code == 200

    r2 = client.get("/config", headers=driver_headers(str(uuid.uuid4())))
    assert r2.status_code == 200

    r3 = client.get("/config", headers=customer_headers(str(uuid.uuid4())))
    assert r3.status_code == 200


def test_update_config_admin(client):
    r = client.put(
        "/config/test_key",
        json={"config_value": 42},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    assert r.json()["config_key"] == "test_key"

    r2 = client.get("/config/test_key", headers=admin_headers())
    assert r2.status_code == 200
    assert r2.json()["config_value"] == 42


def test_update_config_driver_forbidden(client):
    r = client.put(
        "/config/some_key",
        json={"config_value": "bad"},
        headers=driver_headers(str(uuid.uuid4())),
    )
    assert r.status_code == 403


def test_get_config_key_not_found(client):
    r = client.get("/config/nonexistent_key_xyz", headers=admin_headers())
    assert r.status_code == 404
