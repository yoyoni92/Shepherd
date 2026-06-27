"""Attendance endpoints + driver licence expiry (Phase 3).

Drivers double as employees: PATCH upserts one (driver, date) row, GET returns a month.
"""
import uuid

import pytest

from tests.conftest import (
    DEFAULT_COMPANY_ID,
    admin_headers,
    driver_headers,
    superadmin_headers,
)


@pytest.fixture(autouse=True)
def _enable_attendance(client):
    # Attendance defaults OFF per company (Feature 5); these tests opt the Default
    # Company in. feature_flags-only patches skip Drive validation, so no mocking needed.
    r = client.patch(
        f"/companies/{DEFAULT_COMPANY_ID}/settings",
        headers=superadmin_headers(),
        json={"feature_flags": {"attendance": True}},
    )
    assert r.status_code == 200


def _make_driver(client) -> str:
    # unique phone per call — the test DB persists across tests in the session
    phone = f"+97250{uuid.uuid4().int % 10_000_000:07d}"
    resp = client.post(
        "/drivers",
        headers=admin_headers(),
        json={"full_name": "נהג נוכחות", "phone_number": phone, "license_valid_to": "2027-03-01"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["license_valid_to"] == "2027-03-01"  # 3.1: optional licence expiry round-trips
    return body["driver_id"]


def test_attendance_upsert_and_month_read(client):
    driver_id = _make_driver(client)

    # upsert a day
    patch = client.patch(
        f"/attendance/{driver_id}/2026-06-15",
        headers=admin_headers(),
        json={"clock_in": "08:05", "clock_out": "17:00", "status": "present"},
    )
    assert patch.status_code == 200
    assert patch.json()["clock_in"] == "08:05"

    # update the same day (still one row)
    patch2 = client.patch(
        f"/attendance/{driver_id}/2026-06-15",
        headers=admin_headers(),
        json={"clock_in": "09:30", "clock_out": "17:00", "status": "late"},
    )
    assert patch2.status_code == 200
    assert patch2.json()["status"] == "late"

    # month read includes it exactly once
    month = client.get("/attendance/2026-06", headers=admin_headers())
    assert month.status_code == 200
    rows = [r for r in month.json() if r["driver_id"] == driver_id]
    assert len(rows) == 1
    assert rows[0]["status"] == "late"


def test_attendance_other_month_excludes_record(client):
    driver_id = _make_driver(client)
    client.patch(
        f"/attendance/{driver_id}/2026-06-15",
        headers=admin_headers(),
        json={"clock_in": "08:00", "clock_out": "17:00", "status": "present"},
    )
    other = client.get("/attendance/2026-07", headers=admin_headers())
    assert other.status_code == 200
    assert all(r["driver_id"] != driver_id for r in other.json())


def test_attendance_forbidden_for_driver(client):
    resp = client.get("/attendance/2026-06", headers=driver_headers("00000000-0000-0000-0000-000000000000"))
    assert resp.status_code == 403


def test_attendance_bad_month_rejected(client):
    resp = client.get("/attendance/2026-13", headers=admin_headers())
    assert resp.status_code == 400
