"""T5 - Reconcile by plate."""
import pytest
import respx
import httpx

from shepherd_contracts import DocType, ExtractionResult
from app.base import ExtractionError
from app.reconcile import reconcile

FLEET_URL = "http://fleet-test:8000"


def _result(doc_type: DocType, plate: str, confidence: float, extra: dict | None = None) -> ExtractionResult:
    fields: dict = {"plate_number": plate}
    if doc_type == DocType.insurance_cert:
        fields.update({"insurer": "Harel", "valid_to": "2025-01-01", "policy_number": "P1",
                        "coverage_type": "comprehensive", "valid_from": "2024-01-01"})
    elif doc_type == DocType.annual_license:
        fields.update({"owner_name": "Moshe", "vendor": "Toyota", "model": "Corolla",
                        "year": 2020, "valid_to": "2025-06-30"})
    elif doc_type == DocType.traffic_ticket:
        fields.update({"ticket_type": "speeding", "violation_desc": "90 in 70",
                        "amount": 1000, "issued_ts": "2024-03-15T09:30:00",
                        "due_date": "2024-04-15", "authority": "Police"})
    if extra:
        fields.update(extra)
    return ExtractionResult(doc_type=doc_type, fields=fields, confidence=confidence)


def test_low_confidence_aborts_before_api_call():
    result = _result(DocType.insurance_cert, "12-345-67", confidence=0.5)
    with pytest.raises(ExtractionError) as exc:
        reconcile(result, "docs/ins.pdf", confidence_min=0.7, fleet_api_url=FLEET_URL)
    assert exc.value.reason == "low_confidence"


def test_low_confidence_does_not_call_fleet_api():
    result = _result(DocType.insurance_cert, "12-345-67", confidence=0.4)
    with respx.mock(base_url=FLEET_URL, assert_all_called=False) as mock:
        mock.post("/documents/extracted")
        with pytest.raises(ExtractionError) as exc:
            reconcile(result, "docs/ins.pdf", confidence_min=0.7, fleet_api_url=FLEET_URL)
        assert exc.value.reason == "low_confidence"
        assert not mock.calls


@respx.mock
def test_plate_found_calls_fleet_api():
    respx.post(f"{FLEET_URL}/documents/extracted").mock(
        return_value=httpx.Response(200, json={"status": "updated", "event_id": None, "report_id": None})
    )
    result = _result(DocType.insurance_cert, "12-345-67", confidence=0.95)
    resp = reconcile(result, "docs/ins.pdf", confidence_min=0.7, fleet_api_url=FLEET_URL, fleet_token="tok")
    assert resp["status"] == "updated"


@respx.mock
def test_plate_not_found_returns_review_required():
    respx.post(f"{FLEET_URL}/documents/extracted").mock(
        return_value=httpx.Response(200, json={"status": "review_required", "event_id": "abc", "report_id": None})
    )
    result = _result(DocType.insurance_cert, "UNKNOWN-PLATE", confidence=0.95)
    resp = reconcile(result, "docs/ins.pdf", confidence_min=0.7, fleet_api_url=FLEET_URL)
    assert resp["status"] == "review_required"


@respx.mock
def test_reconcile_payload_insurance():
    route = respx.post(f"{FLEET_URL}/documents/extracted").mock(
        return_value=httpx.Response(200, json={"status": "updated"})
    )
    result = _result(DocType.insurance_cert, "12-345-67", confidence=0.95)
    reconcile(result, "docs/ins.pdf", confidence_min=0.7, fleet_api_url=FLEET_URL)
    payload = route.calls[0].request.content
    import json
    body = json.loads(payload)
    assert body["doc_type"] == "insurance"
    assert body["licensing_plate"] == "12-345-67"
    assert body["insurance_valid_to"] == "2025-01-01"


@respx.mock
def test_reconcile_payload_ticket():
    route = respx.post(f"{FLEET_URL}/documents/extracted").mock(
        return_value=httpx.Response(200, json={"status": "updated", "report_id": "r1"})
    )
    result = _result(DocType.traffic_ticket, "12-345-67", confidence=0.9)
    reconcile(result, "docs/ticket.pdf", confidence_min=0.7, fleet_api_url=FLEET_URL)
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["doc_type"] == "ticket"
    assert body["amount"] == "1000"
