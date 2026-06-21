"""Vehicle type + full CRUD (PATCH) + customer-delete cascade (UI CRUD pass)."""
import uuid

from tests.conftest import admin_headers, driver_headers

H = admin_headers


def _plate() -> str:
    return str(uuid.uuid4().int % 100_000_000).zfill(8)


def test_vehicle_type_round_trips_and_patches(client):
    plate = _plate()
    created = client.post("/vehicles", headers=H(), json={"licensing_plate": plate, "vehicle_type": "car", "current_km": 1000})
    assert created.status_code == 201
    vid = created.json()["vehicle_id"]
    assert created.json()["vehicle_type"] == "car"

    patched = client.patch(f"/vehicles/{vid}", headers=H(), json={"vehicle_type": "truck", "current_km": 4200})
    assert patched.status_code == 200
    assert patched.json()["vehicle_type"] == "truck"
    assert patched.json()["current_km"] == 4200


def test_patch_driver_and_customer(client):
    drv = client.post("/drivers", headers=H(), json={"full_name": "א", "phone_number": _plate()}).json()
    upd = client.patch(f"/drivers/{drv['driver_id']}", headers=H(), json={"status": "inactive", "license_valid_to": "2028-01-01"})
    assert upd.status_code == 200
    assert upd.json()["status"] == "inactive"
    assert upd.json()["license_valid_to"] == "2028-01-01"

    cust = client.post("/customers", headers=H(), json={"full_name": "לקוח"}).json()
    cupd = client.patch(f"/customers/{cust['customer_id']}", headers=H(), json={"email": "x@y.co.il", "status": "inactive"})
    assert cupd.status_code == 200
    assert cupd.json()["email"] == "x@y.co.il"


def test_delete_customer_nulls_vehicle_link(client):
    cust = client.post("/customers", headers=H(), json={"full_name": "לקוח למחיקה"}).json()
    cid = cust["customer_id"]
    veh = client.post("/vehicles", headers=H(), json={"licensing_plate": _plate(), "customer_id": cid}).json()
    vid = veh["vehicle_id"]
    assert veh["customer_id"] == cid

    deleted = client.delete(f"/customers/{cid}", headers=H())
    assert deleted.status_code == 204

    # vehicle survives with its customer link cleared
    got = client.get(f"/vehicles/{veh['licensing_plate']}", headers=H())
    assert got.status_code == 200
    assert got.json()["customer_id"] is None


def test_invalid_vehicle_type_rejected(client):
    # vehicle_type is an enum on the API now → bad value is a 422, not a DB 500
    resp = client.post("/vehicles", headers=H(), json={"licensing_plate": _plate(), "vehicle_type": "spaceship"})
    assert resp.status_code == 422


def test_patch_forbidden_for_driver(client):
    resp = client.patch(
        "/vehicles/00000000-0000-0000-0000-000000000000",
        headers=driver_headers("00000000-0000-0000-0000-000000000000"),
        json={"vehicle_type": "bus"},
    )
    assert resp.status_code == 403
