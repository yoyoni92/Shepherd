"""T8 - documents/extracted reconcile: matching plate updates fields; mismatched -> review event."""
import uuid

from tests.conftest import admin_headers, driver_headers


def _make_vehicle(client) -> tuple[str, str]:
    plate = f"DOC-{uuid.uuid4().hex[:6]}"
    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    return r.json()["vehicle_id"], plate


def test_extracted_insurance_updates_vehicle(client):
    _, plate = _make_vehicle(client)
    r = client.post(
        "/documents/extracted",
        json={
            "doc_type": "insurance",
            "licensing_plate": plate,
            "insurance_valid_to": "2027-12-31",
            "insurance_file_url": "s3://bucket/ins.pdf",
        },
        headers=admin_headers(),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "updated"

    # Confirm update persisted
    r2 = client.get(f"/vehicles/{plate}", headers=admin_headers())
    assert r2.json()["insurance_valid_to"] == "2027-12-31"


def test_extracted_license_updates_vehicle(client):
    _, plate = _make_vehicle(client)
    r = client.post(
        "/documents/extracted",
        json={"doc_type": "license", "licensing_plate": plate, "license_valid_to": "2028-06-30"},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "updated"


def test_extracted_ticket_creates_report(client):
    _, plate = _make_vehicle(client)
    r = client.post(
        "/documents/extracted",
        json={
            "doc_type": "ticket",
            "licensing_plate": plate,
            "ticket_type": "traffic",
            "violation_desc": "Speeding",
            "amount": "250.00",
        },
        headers=admin_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "updated"
    assert data["report_id"] is not None


def test_extracted_mismatched_plate_creates_review_event(client):
    r = client.post(
        "/documents/extracted",
        json={"doc_type": "insurance", "licensing_plate": "UNKNOWN-PLATE-XYZ"},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "review_required"
    assert data["event_id"] is not None


def test_extracted_driver_forbidden(client):
    r = client.post(
        "/documents/extracted",
        json={"doc_type": "insurance", "licensing_plate": "ANY-PLATE"},
        headers=driver_headers(str(uuid.uuid4())),
    )
    assert r.status_code == 403
