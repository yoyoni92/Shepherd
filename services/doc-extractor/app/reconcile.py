"""Reconcile extracted doc against Fleet API by plate number."""
from __future__ import annotations

import os
from decimal import Decimal

import httpx

from shepherd_contracts import DocType, ExtractionResult
from app.base import ExtractionError

DEFAULT_CONFIDENCE_MIN = 0.7


def reconcile(
    result: ExtractionResult,
    s3_key: str,
    *,
    confidence_min: float = DEFAULT_CONFIDENCE_MIN,
    fleet_api_url: str | None = None,
    fleet_token: str | None = None,
) -> dict:
    """Post extraction result to Fleet API. Raises ExtractionError on low confidence."""
    if result.confidence < confidence_min:
        raise ExtractionError(
            f"Confidence {result.confidence:.2f} below threshold {confidence_min}",
            reason="low_confidence",
        )

    url = (fleet_api_url or os.environ.get("FLEET_API_URL", "http://fleet-api:8000")).rstrip("/")
    token = fleet_token or os.environ.get("INTERNAL_SERVICE_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = _build_payload(result, s3_key)
    response = httpx.post(f"{url}/documents/extracted", json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def _build_payload(result: ExtractionResult, s3_key: str) -> dict:
    f = result.fields
    if result.doc_type == DocType.insurance_cert:
        return {
            "doc_type": "insurance",
            "licensing_plate": f.get("plate_number") or "",
            "insurance_valid_to": f.get("valid_to"),
            "insurance_file_url": s3_key,
        }
    if result.doc_type == DocType.annual_license:
        return {
            "doc_type": "license",
            "licensing_plate": f.get("plate_number") or "",
            "license_valid_to": f.get("valid_to"),
            "license_file_url": s3_key,
        }
    # traffic_ticket
    amount = f.get("amount")
    return {
        "doc_type": "ticket",
        "licensing_plate": f.get("plate_number") or "",
        "ticket_type": f.get("ticket_type"),
        "violation_desc": f.get("violation_desc"),
        "amount": str(Decimal(str(amount))) if amount is not None else None,
        "issued_ts": f.get("issued_ts"),
        "due_date": f.get("due_date"),
        "authority": f.get("authority"),
        "ticket_file_url": s3_key,
    }
