"""Document types (Image Analyser classes) + per-type extracted-field schemas."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class DocType(str, Enum):
    insurance_cert = "insurance_cert"
    annual_license = "annual_license"
    traffic_ticket = "traffic_ticket"
    vehicle_photo = "vehicle_photo"
    other = "other"


class InsuranceFields(BaseModel):
    insurer: str | None = None
    policy_number: str | None = None
    plate_number: str | None = None
    coverage_type: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class LicenseFields(BaseModel):
    plate_number: str | None = None
    owner_name: str | None = None
    vendor: str | None = None
    model: str | None = None
    year: int | None = None
    valid_to: date | None = None


class TicketFields(BaseModel):
    plate_number: str | None = None
    ticket_type: str | None = None
    violation_desc: str | None = None
    amount: float | None = None
    issued_ts: datetime | None = None
    due_date: date | None = None
    authority: str | None = None


class ExtractionResult(BaseModel):
    doc_type: DocType
    fields: dict
    confidence: float
    raw: str | None = None
