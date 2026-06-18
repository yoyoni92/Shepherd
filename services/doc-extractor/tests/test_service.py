"""Service endpoint tests (FastAPI TestClient)."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from shepherd_contracts import DocType, ExtractionResult

from app.service import app

client = TestClient(app)


def _mock_extractor(confidence: float = 0.95):
    extractor = MagicMock()
    extractor.extract.return_value = ExtractionResult(
        doc_type=DocType.insurance_cert,
        fields={"plate_number": "12-345-67", "valid_to": "2025-01-01"},
        confidence=confidence,
    )
    return extractor


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_extract_success():
    fleet_resp = {"status": "updated", "event_id": None, "report_id": None}
    with (
        patch("app.service.get_extractor", return_value=_mock_extractor()),
        patch("app.service.reconcile", return_value=fleet_resp),
    ):
        resp = client.post("/extract", json={
            "s3_key": "docs/ins.pdf",
            "doc_type": "insurance_cert",
            "confidence_min": 0.7,
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "updated"
    assert body["confidence"] == 0.95


def test_extract_extraction_error_returns_422():
    from app.base import ExtractionError
    extractor = MagicMock()
    extractor.extract.side_effect = ExtractionError("parse failed", reason="parse_error")
    with patch("app.service.get_extractor", return_value=extractor):
        resp = client.post("/extract", json={
            "s3_key": "docs/bad.pdf",
            "doc_type": "insurance_cert",
        })
    assert resp.status_code == 422


def test_extract_low_confidence_returns_422():
    from app.base import ExtractionError
    with (
        patch("app.service.get_extractor", return_value=_mock_extractor(confidence=0.3)),
        patch("app.service.reconcile", side_effect=ExtractionError("low", reason="low_confidence")),
    ):
        resp = client.post("/extract", json={
            "s3_key": "docs/ins.pdf",
            "doc_type": "insurance_cert",
            "confidence_min": 0.7,
        })
    assert resp.status_code == 422
