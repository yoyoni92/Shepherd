"""T6 - Accidents + attachments + accident_logged event."""
import uuid
from datetime import datetime, timezone

from tests.conftest import admin_headers, customer_headers, driver_headers


def _make_driver(client) -> str:
    r = client.post(
        "/drivers",
        json={"full_name": "Accident Driver", "phone_number": f"+1{uuid.uuid4().int % 10**10:010d}"},
        headers=admin_headers(),
    )
    return r.json()["driver_id"]


def _make_vehicle(client, driver_id: str | None = None) -> str:
    plate = f"ACC-{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/vehicles",
        json={"licensing_plate": plate, "driver_id": driver_id},
        headers=admin_headers(),
    )
    return r.json()["vehicle_id"]


def test_log_accident_admin(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/accidents",
        json={
            "vehicle_id": vehicle_id,
            "datetime": datetime.now(tz=timezone.utc).isoformat(),
            "location": "Tel Aviv",
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201
    assert "accident_id" in r.json()


def test_log_accident_with_attachments(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/accidents",
        json={
            "vehicle_id": vehicle_id,
            "datetime": datetime.now(tz=timezone.utc).isoformat(),
            "attachments": [
                {"category": "photo_our_vehicle", "file_url": "s3://bucket/photo.jpg"},
                {"category": "another_driver_insurance", "file_url": "s3://bucket/ins.pdf"},
            ],
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201


def test_log_accident_driver_own(client):
    driver_id = _make_driver(client)
    vehicle_id = _make_vehicle(client, driver_id=driver_id)
    r = client.post(
        "/accidents",
        json={"vehicle_id": vehicle_id, "datetime": datetime.now(tz=timezone.utc).isoformat()},
        headers=driver_headers(driver_id),
    )
    assert r.status_code == 201


def test_log_accident_driver_not_own(client):
    other_driver_id = str(uuid.uuid4())
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/accidents",
        json={"vehicle_id": vehicle_id, "datetime": datetime.now(tz=timezone.utc).isoformat()},
        headers=driver_headers(other_driver_id),
    )
    assert r.status_code == 403


def test_log_accident_customer_forbidden(client):
    vehicle_id = _make_vehicle(client)
    r = client.post(
        "/accidents",
        json={"vehicle_id": vehicle_id, "datetime": datetime.now(tz=timezone.utc).isoformat()},
        headers=customer_headers(str(uuid.uuid4())),
    )
    assert r.status_code == 403
