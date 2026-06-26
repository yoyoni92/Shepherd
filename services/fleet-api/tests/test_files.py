"""POST /files - forwards uploaded bytes to Drive and returns the public link."""
from app import drive


def test_upload_forwards_to_drive_and_returns_link(client, monkeypatch):
    captured = {}

    def fake_upload(key, data, content_type):
        captured.update(key=key, data=data, content_type=content_type)
        return "https://drive.google.com/file/d/abc/view"

    monkeypatch.setattr(drive, "upload", fake_upload)

    r = client.post(
        "/files",
        data={"key": "accidents/123/photo.jpg"},
        files={"file": ("photo.jpg", b"raw-bytes", "image/jpeg")},
    )

    assert r.status_code == 200
    assert r.json() == {"file_url": "https://drive.google.com/file/d/abc/view"}
    assert captured == {
        "key": "accidents/123/photo.jpg",
        "data": b"raw-bytes",
        "content_type": "image/jpeg",
    }


def test_upload_rejects_without_internal_token(raw_client, monkeypatch):
    monkeypatch.setattr(drive, "upload", lambda *a, **k: "nope")
    r = raw_client.post(
        "/files",
        data={"key": "accidents/123/photo.jpg"},
        files={"file": ("photo.jpg", b"raw-bytes", "image/jpeg")},
    )
    assert r.status_code == 401
