"""POST /files - resolves the caller's company, then forwards bytes to that company's Drive."""
from app import drive

from tests.conftest import DEFAULT_COMPANY_ID, TEST_TOKEN, admin_headers, superadmin_headers
from tests.fakes import fake_build_service

_CREDS = '{"type": "service_account", "client_email": "x@y.iam"}'


def _configure_default_drive(client, monkeypatch):
    """Configure the Default Company's Drive via the settings endpoint (no real network)."""
    monkeypatch.setattr(drive, "_build_service", fake_build_service())
    r = client.patch(
        f"/companies/{DEFAULT_COMPANY_ID}/settings",
        headers=superadmin_headers(),
        json={"gdrive_folder_id": "folder-123", "gdrive_credentials_json": _CREDS},
    )
    assert r.status_code == 200
    assert r.json()["gdrive_configured"] is True


def test_upload_forwards_to_drive_and_returns_link(client, monkeypatch):
    _configure_default_drive(client, monkeypatch)

    captured = {}

    def fake_upload(key, data, content_type, *, credentials_json, folder_id):
        captured.update(
            key=key, data=data, content_type=content_type,
            credentials_json=credentials_json, folder_id=folder_id,
        )
        return "https://drive.google.com/file/d/abc/view"

    monkeypatch.setattr(drive, "upload", fake_upload)

    r = client.post(
        "/files",
        headers=admin_headers(),
        data={"key": "accidents/123/photo.jpg"},
        files={"file": ("photo.jpg", b"raw-bytes", "image/jpeg")},
    )

    assert r.status_code == 200
    assert r.json() == {"file_url": "https://drive.google.com/file/d/abc/view"}
    assert captured["key"] == "accidents/123/photo.jpg"
    assert captured["data"] == b"raw-bytes"
    assert captured["content_type"] == "image/jpeg"
    assert captured["credentials_json"] == _CREDS
    assert captured["folder_id"] == "folder-123"


def test_upload_rejects_unconfigured_company(client, monkeypatch):
    monkeypatch.setattr(drive, "upload", lambda *a, **k: "nope")
    # A fresh company with no settings row at all -> Drive not configured.
    created = client.post("/companies", headers=superadmin_headers(), json={"name": "NoDrive Co"})
    company_id = created.json()["company_id"]

    r = client.post(
        "/files",
        headers={
            "X-Internal-Token": TEST_TOKEN,
            "X-Caller-Context": admin_headers()["X-Caller-Context"].replace(
                DEFAULT_COMPANY_ID, company_id
            ),
        },
        data={"key": "accidents/123/photo.jpg"},
        files={"file": ("photo.jpg", b"raw-bytes", "image/jpeg")},
    )
    assert r.status_code == 400
    assert "not configured" in r.json()["detail"].lower()


def test_upload_rejects_without_internal_token(raw_client, monkeypatch):
    monkeypatch.setattr(drive, "upload", lambda *a, **k: "nope")
    # Caller context present but no internal token -> 401 (auth runs before Drive resolution).
    r = raw_client.post(
        "/files",
        headers={"X-Caller-Context": admin_headers()["X-Caller-Context"]},
        data={"key": "accidents/123/photo.jpg"},
        files={"file": ("photo.jpg", b"raw-bytes", "image/jpeg")},
    )
    assert r.status_code == 401
