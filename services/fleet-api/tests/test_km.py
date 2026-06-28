"""T5 - KM update + maintenance trigger + ownership enforcement."""
import uuid

from tests.conftest import admin_headers, customer_headers, driver_headers


def _make_driver(client) -> str:
    r = client.post(
        "/drivers",
        json={"full_name": "KM Driver", "phone_number": f"+1{uuid.uuid4().int % 10**10:010d}"},
        headers=admin_headers(),
    )
    return r.json()["driver_id"]


def _make_vehicle(client, driver_id: str | None = None, next_maintenance_km: int | None = None):
    mt = client.post(
        "/maintenance-types",
        json={
            "name": f"cycle-{uuid.uuid4().hex[:6]}",
            "interval_km": 10000,
            "steps": ["small", "big"],
        },
        headers=admin_headers(),
    ).json()
    plate = f"KM-{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/vehicles",
        json={"licensing_plate": plate, "driver_id": driver_id, "maintenance_type_id": mt["id"]},
        headers=admin_headers(),
    )
    vehicle_id = r.json()["vehicle_id"]

    if next_maintenance_km is not None:
        client.post(
            "/vehicle_care",
            json={
                "vehicle_id": vehicle_id,
                "service_date": "2025-01-01",
                "maintenance_type": "small",
                "km_at_service": next_maintenance_km - 10_000,
            },
            headers=admin_headers(),
        )

    return vehicle_id, plate


def test_km_update_admin(client):
    vehicle_id, _ = _make_vehicle(client)
    r = client.post(
        "/km",
        json={"vehicle_id": vehicle_id, "km": 15000, "source": "admin_ui"},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert "km_update_id" in data
    assert "maintenance_event_created" in data


def test_km_update_driver_own(client):
    driver_id = _make_driver(client)
    vehicle_id, _ = _make_vehicle(client, driver_id=driver_id)
    r = client.post(
        "/km",
        json={"vehicle_id": vehicle_id, "km": 5000, "source": "telegram"},
        headers=driver_headers(driver_id),
    )
    assert r.status_code == 200


def test_km_update_driver_not_own(client):
    other_driver_id = str(uuid.uuid4())
    vehicle_id, _ = _make_vehicle(client)
    r = client.post(
        "/km",
        json={"vehicle_id": vehicle_id, "km": 5000, "source": "telegram"},
        headers=driver_headers(other_driver_id),
    )
    assert r.status_code == 403


def test_km_update_customer_forbidden(client):
    vehicle_id, _ = _make_vehicle(client)
    r = client.post(
        "/km",
        json={"vehicle_id": vehicle_id, "km": 5000, "source": "telegram"},
        headers=customer_headers(str(uuid.uuid4())),
    )
    assert r.status_code == 403


def test_km_update_triggers_maintenance_event(client):
    """When km >= next_maintenance_km - buffer, maintenance_due event is created."""
    driver_id = _make_driver(client)
    # Create vehicle with next_maintenance_km set via care record
    vehicle_id, _ = _make_vehicle(client, driver_id=driver_id, next_maintenance_km=10000)

    # After _make_vehicle with next_maintenance_km=10000, a care was logged at km=0 -> next at 10000
    # Actually _make_vehicle sets km_at_service = next_maintenance_km - 10000 = 0
    # So next_maintenance_km = 0 + 10000 = 10000
    # buffer default = 500
    # trigger at km >= 10000 - 500 = 9500
    r = client.post(
        "/km",
        json={"vehicle_id": vehicle_id, "km": 9600, "source": "admin_ui"},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    assert r.json()["maintenance_event_created"] is True


def test_km_update_dedups_open_maintenance_event(client):
    """A second km report past the threshold does not open a second maintenance_due."""
    vehicle_id, _ = _make_vehicle(client, next_maintenance_km=10000)
    first = client.post(
        "/km", json={"vehicle_id": vehicle_id, "km": 9600, "source": "admin_ui"},
        headers=admin_headers(),
    )
    assert first.json()["maintenance_event_created"] is True
    second = client.post(
        "/km", json={"vehicle_id": vehicle_id, "km": 9700, "source": "admin_ui"},
        headers=admin_headers(),
    )
    assert second.json()["maintenance_event_created"] is False


def test_km_update_no_trigger_below_buffer(client):
    driver_id = _make_driver(client)
    vehicle_id, _ = _make_vehicle(client, driver_id=driver_id, next_maintenance_km=10000)
    r = client.post(
        "/km",
        json={"vehicle_id": vehicle_id, "km": 9000, "source": "admin_ui"},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    assert r.json()["maintenance_event_created"] is False


def _post_km(client, vehicle_id, km):
    return client.post(
        "/km", json={"vehicle_id": vehicle_id, "km": km, "source": "telegram"},
        headers=admin_headers(),
    )


def test_km_update_rejects_below_current(client):
    vehicle_id, _ = _make_vehicle(client)
    assert _post_km(client, vehicle_id, 20000).status_code == 200
    r = _post_km(client, vehicle_id, 19000)
    assert r.status_code == 422
    assert r.json()["detail"] == "km_below_current"


def test_km_update_rejects_large_increment(client):
    vehicle_id, _ = _make_vehicle(client)
    assert _post_km(client, vehicle_id, 20000).status_code == 200
    r = _post_km(client, vehicle_id, 20000 + 10001)  # default cap is 10000
    assert r.status_code == 422
    assert r.json()["detail"] == "km_increment_too_large"


def test_km_update_allows_within_increment(client):
    vehicle_id, _ = _make_vehicle(client)
    assert _post_km(client, vehicle_id, 20000).status_code == 200
    assert _post_km(client, vehicle_id, 29000).status_code == 200  # +9000, under cap


def test_km_update_honors_custom_threshold(client):
    client.put("/config/km_max_increment", json={"config_value": 100}, headers=admin_headers())
    vehicle_id, _ = _make_vehicle(client)
    assert _post_km(client, vehicle_id, 20000).status_code == 200
    assert _post_km(client, vehicle_id, 20050).status_code == 200  # +50, under custom cap
    assert _post_km(client, vehicle_id, 20200).status_code == 422  # +200, over custom cap
