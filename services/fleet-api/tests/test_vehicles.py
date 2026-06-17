"""T4 - Vehicles CRUD with ownership enforcement (T3 integration)."""
import uuid

from tests.conftest import admin_headers, driver_headers, customer_headers


def _plate(suffix: str) -> str:
    return f"VT-{suffix}"


def _make_driver(client) -> str:
    r = client.post(
        "/drivers",
        json={"full_name": "Test Driver", "phone_number": f"+1{uuid.uuid4().int % 10**10:010d}"},
        headers=admin_headers(),
    )
    return r.json()["driver_id"]


def _make_customer(client) -> str:
    r = client.post(
        "/customers",
        json={"full_name": "Test Customer", "email": f"c{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers(),
    )
    return r.json()["customer_id"]


def test_create_vehicle_admin(client):
    plate = _plate(uuid.uuid4().hex[:6])
    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    assert r.status_code == 201
    data = r.json()
    assert data["licensing_plate"] == plate
    assert "vehicle_id" in data


def test_create_vehicle_duplicate_plate(client):
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    assert r.status_code == 409


def test_get_vehicle_admin(client):
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    r = client.get(f"/vehicles/{plate}", headers=admin_headers())
    assert r.status_code == 200
    assert r.json()["licensing_plate"] == plate


def test_get_vehicle_driver_own(client):
    driver_id = _make_driver(client)
    plate = _plate(uuid.uuid4().hex[:6])
    client.post(
        "/vehicles",
        json={"licensing_plate": plate, "driver_id": driver_id},
        headers=admin_headers(),
    )
    r = client.get(f"/vehicles/{plate}", headers=driver_headers(driver_id))
    assert r.status_code == 200


def test_get_vehicle_driver_not_own(client):
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    other_driver_id = str(uuid.uuid4())
    r = client.get(f"/vehicles/{plate}", headers=driver_headers(other_driver_id))
    assert r.status_code == 403


def test_get_vehicle_not_found(client):
    r = client.get("/vehicles/NONEXISTENT-9999", headers=admin_headers())
    assert r.status_code == 404


def test_delete_vehicle_admin(client):
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.delete(f"/vehicles/{vehicle_id}", headers=admin_headers())
    assert r.status_code == 204


def test_delete_vehicle_driver_forbidden(client):
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.delete(f"/vehicles/{vehicle_id}", headers=driver_headers(str(uuid.uuid4())))
    assert r.status_code == 403


def test_delete_vehicle_customer_forbidden(client):
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.delete(f"/vehicles/{vehicle_id}", headers=customer_headers(str(uuid.uuid4())))
    assert r.status_code == 403


def test_list_vehicles_admin_sees_all(client):
    # Create 2 vehicles
    p1 = _plate(uuid.uuid4().hex[:6])
    p2 = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": p1}, headers=admin_headers())
    client.post("/vehicles", json={"licensing_plate": p2}, headers=admin_headers())
    r = client.get("/vehicles", headers=admin_headers())
    assert r.status_code == 200
    plates = [v["licensing_plate"] for v in r.json()]
    assert p1 in plates
    assert p2 in plates


def test_list_vehicles_driver_sees_own_only(client):
    driver_id = _make_driver(client)
    p_own = _plate(uuid.uuid4().hex[:6])
    p_other = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": p_own, "driver_id": driver_id}, headers=admin_headers())
    client.post("/vehicles", json={"licensing_plate": p_other}, headers=admin_headers())
    r = client.get("/vehicles", headers=driver_headers(driver_id))
    assert r.status_code == 200
    plates = [v["licensing_plate"] for v in r.json()]
    assert p_own in plates
    assert p_other not in plates
