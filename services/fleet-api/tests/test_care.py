"""T7 - vehicle_care advances the maintenance cycle."""
import uuid

from tests.conftest import admin_headers, driver_headers


def _make_vehicle(client) -> str:
    # admin-defined cycle: small -> big, 10000 km interval
    mt = client.post(
        "/maintenance-types",
        json={"name": f"cycle-{uuid.uuid4().hex[:6]}", "interval_km": 10000, "steps": ["small", "big"]},
        headers=admin_headers(),
    ).json()
    plate = f"CARE-{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/vehicles",
        json={"licensing_plate": plate, "maintenance_type_id": mt["id"]},
        headers=admin_headers(),
    )
    return r.json()["vehicle_id"]


def test_log_care_admin(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/vehicle_care",
        json={
            "vehicle_id": vehicle_id,
            "service_date": "2025-06-01",
            "maintenance_type": "small",
            "km_at_service": 10000,
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert "care_id" in data
    assert data["next_maintenance_km"] == 20000  # 10000 + 10000 interval
    assert data["next_maintenance_type"] == "big"


def test_log_care_advances_cycle(client):
    vehicle_id = _make_vehicle(client)
    # First service: small -> next should be big
    r1 = client.post(
        "/vehicle_care",
        json={"vehicle_id": vehicle_id, "service_date": "2025-01-01", "maintenance_type": "small", "km_at_service": 5000},
        headers=admin_headers(),
    )
    assert r1.json()["next_maintenance_type"] == "big"

    # Second service: big -> next should be small
    r2 = client.post(
        "/vehicle_care",
        json={"vehicle_id": vehicle_id, "service_date": "2025-06-01", "maintenance_type": "big", "km_at_service": 15000},
        headers=admin_headers(),
    )
    assert r2.json()["next_maintenance_type"] == "small"


def test_log_care_driver_forbidden(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/vehicle_care",
        json={"vehicle_id": vehicle_id, "service_date": "2025-06-01", "maintenance_type": "small", "km_at_service": 5000},
        headers=driver_headers(str(uuid.uuid4())),
    )
    assert r.status_code == 403
