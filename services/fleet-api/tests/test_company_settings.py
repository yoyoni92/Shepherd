"""Feature 5 - per-tenant settings: Drive config (validate-then-persist) + attendance flag.

All Google calls are faked via tests.fakes so nothing touches the network.
"""
import uuid

from app import drive

from tests.conftest import (
    company_admin_headers,
    company_headers,
    superadmin_headers,
)
from tests.fakes import fake_build_service

_CREDS = '{"type": "service_account", "client_email": "svc@proj.iam.gserviceaccount.com"}'


def _new_company(client) -> str:
    r = client.post(
        "/companies", headers=superadmin_headers(), json={"name": f"Co {uuid.uuid4().hex[:8]}"}
    )
    assert r.status_code == 201
    return r.json()["company_id"]


# --- Admin-only access ---


def test_get_settings_admin_only(client):
    company_id = _new_company(client)
    ok = client.get(f"/companies/{company_id}/settings", headers=superadmin_headers())
    assert ok.status_code == 200
    body = ok.json()
    assert body["gdrive_configured"] is False
    assert body["gdrive_folder_id"] is None
    assert body["feature_flags"] == {}

    forbidden = client.get(
        f"/companies/{company_id}/settings", headers=company_admin_headers(company_id)
    )
    assert forbidden.status_code == 403


def test_patch_settings_forbidden_for_company_admin(client):
    company_id = _new_company(client)
    r = client.patch(
        f"/companies/{company_id}/settings",
        headers=company_admin_headers(company_id),
        json={"feature_flags": {"attendance": True}},
    )
    assert r.status_code == 403


# --- Drive: validate-then-persist ---


def test_invalid_drive_credentials_rejected_and_not_persisted(client, monkeypatch):
    company_id = _new_company(client)
    # Folder fetch raises -> validation fails with the folder-not-accessible message.
    monkeypatch.setattr(
        drive, "_build_service", fake_build_service(get_exc=RuntimeError("404 file not found"))
    )
    r = client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"gdrive_folder_id": "bad-folder", "gdrive_credentials_json": _CREDS},
    )
    assert r.status_code == 400
    assert "not accessible" in r.json()["detail"].lower()

    # Nothing was stored.
    after = client.get(f"/companies/{company_id}/settings", headers=superadmin_headers())
    assert after.json()["gdrive_configured"] is False
    assert after.json()["gdrive_folder_id"] is None


def test_invalid_credentials_json_rejected(client, monkeypatch):
    company_id = _new_company(client)
    # Real _build_service runs json.loads on a non-JSON blob -> JSONDecodeError mapped to 400.
    r = client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"gdrive_folder_id": "folder", "gdrive_credentials_json": "not-json"},
    )
    assert r.status_code == 400
    assert "json" in r.json()["detail"].lower()


def test_partial_drive_config_rejected(client):
    company_id = _new_company(client)
    # Folder without credentials can't be validated.
    r = client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"gdrive_folder_id": "folder-only"},
    )
    assert r.status_code == 400
    assert "required" in r.json()["detail"].lower()


def test_valid_drive_credentials_persist(client, monkeypatch):
    company_id = _new_company(client)
    monkeypatch.setattr(drive, "_build_service", fake_build_service())
    r = client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"gdrive_folder_id": "folder-123", "gdrive_credentials_json": _CREDS},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gdrive_configured"] is True
    assert body["gdrive_folder_id"] == "folder-123"
    # The raw credentials blob is never echoed back.
    assert "gdrive_credentials_json" not in body


def test_feature_flags_merge(client):
    company_id = _new_company(client)
    client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"feature_flags": {"attendance": True}},
    )
    r = client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"feature_flags": {"beta": True}},
    )
    assert r.status_code == 200
    assert r.json()["feature_flags"] == {"attendance": True, "beta": True}


# --- Attendance gate driven by the flag ---


def test_attendance_gate_reads(client):
    company_id = _new_company(client)
    headers = company_headers(company_id)

    # Off by default -> 403.
    off = client.get("/attendance/2026-06", headers=headers)
    assert off.status_code == 403
    assert off.json()["detail"] == "attendance disabled"

    # Toggle on via settings -> 200.
    client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"feature_flags": {"attendance": True}},
    )
    on = client.get("/attendance/2026-06", headers=headers)
    assert on.status_code == 200


def test_attendance_gate_clock_endpoints(client):
    company_id = _new_company(client)
    # A driver in this company (clock endpoints resolve the company from the driver).
    phone = f"+97250{uuid.uuid4().int % 10_000_000:07d}"
    drv = client.post(
        "/drivers",
        headers=company_headers(company_id),
        json={"full_name": "Clock Driver", "phone_number": phone},
    )
    driver_id = drv.json()["driver_id"]

    # Off -> typed "disabled" result (not an HTTP error, so the bot's response stays typed).
    blocked = client.post("/attendance/clock-in", json={"driver_id": driver_id})
    assert blocked.status_code == 200
    assert blocked.json()["result"] == "disabled"

    # On -> clock-in proceeds.
    client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"feature_flags": {"attendance": True}},
    )
    ok = client.post("/attendance/clock-in", json={"driver_id": driver_id})
    assert ok.status_code == 200
    assert ok.json()["result"] == "ok"


# --- Flag exposure: login response carries the company's flags ---


def test_login_includes_company_feature_flags(client):
    company_id = _new_company(client)
    client.patch(
        f"/companies/{company_id}/settings",
        headers=superadmin_headers(),
        json={"feature_flags": {"attendance": True}},
    )
    email = f"ca-{uuid.uuid4().hex[:8]}@fleetops.io"
    created = client.post(
        "/app-users",
        headers=superadmin_headers(),
        json={
            "email": email,
            "password": "pw-secret",
            "role": "company_admin",
            "company_id": company_id,
        },
    )
    assert created.status_code == 201

    r = client.post("/auth/login", json={"email": email, "password": "pw-secret"})
    assert r.status_code == 200
    assert r.json()["feature_flags"] == {"attendance": True}


def test_login_system_admin_has_empty_flags(client):
    email = f"sa-{uuid.uuid4().hex[:8]}@fleetops.io"
    client.post(
        "/app-users",
        headers=superadmin_headers(),
        json={"email": email, "password": "pw-secret", "role": "admin"},
    )
    r = client.post("/auth/login", json={"email": email, "password": "pw-secret"})
    assert r.status_code == 200
    assert r.json()["feature_flags"] == {}
