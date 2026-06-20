"""Pydantic request/response schemas for Fleet API."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


# --- Vehicles ---

class VehicleCreate(BaseModel):
    licensing_plate: str
    nickname: str | None = None
    vendor: str | None = None
    model: str | None = None
    allowed_driver: str | None = None
    driver_id: UUID | None = None
    customer_id: UUID | None = None
    maintenance_type: str | None = None
    insurance_valid_to: date | None = None
    license_valid_to: date | None = None


class VehicleRead(BaseModel):
    vehicle_id: UUID
    licensing_plate: str
    nickname: str | None = None
    vendor: str | None = None
    model: str | None = None
    current_km: int | None = None
    insurance_valid_to: date | None = None
    license_valid_to: date | None = None
    driver_id: UUID | None = None
    customer_id: UUID | None = None
    next_maintenance_km: int | None = None
    next_maintenance_type: str | None = None
    last_maintenance_type: str | None = None
    last_maintenance_km: int | None = None
    last_maintenance_date: date | None = None
    maintenance_type: str | None = None
    allowed_driver: str | None = None


# --- Drivers ---

class DriverCreate(BaseModel):
    full_name: str
    phone_number: str
    license_number: str | None = None


class DriverRead(BaseModel):
    driver_id: UUID
    full_name: str
    phone_number: str
    license_number: str | None = None
    status: str


# --- Customers ---

class CustomerCreate(BaseModel):
    full_name: str
    phone_number: str | None = None
    email: str | None = None


class CustomerRead(BaseModel):
    customer_id: UUID
    full_name: str
    phone_number: str | None = None
    email: str | None = None
    status: str


# --- KM Update ---

class KmUpdateRequest(BaseModel):
    vehicle_id: UUID
    km: int
    source: str  # "telegram" | "admin_ui"


class KmUpdateResponse(BaseModel):
    km_update_id: UUID
    maintenance_event_created: bool


# --- Accidents ---

class AccidentAttachmentIn(BaseModel):
    category: str
    file_url: str


class AccidentCreate(BaseModel):
    vehicle_id: UUID
    datetime: datetime
    location: str | None = None
    description: str | None = None
    another_driver_licensing_plate: str | None = None
    another_driver_phone_number: str | None = None
    another_driver_id_number: str | None = None
    attachments: list[AccidentAttachmentIn] = []


class AccidentRead(BaseModel):
    accident_id: UUID


# --- Vehicle Care ---

class VehicleCareCreate(BaseModel):
    vehicle_id: UUID
    service_date: date
    maintenance_type: str
    km_at_service: int
    description: str | None = None
    cost: Decimal | None = None
    garage: str | None = None
    invoice_file_url: str | None = None


class VehicleCareRead(BaseModel):
    care_id: UUID
    vehicle_id: UUID
    next_maintenance_km: int
    next_maintenance_type: str


# --- Documents Extracted ---

class DocumentExtractedRequest(BaseModel):
    doc_type: str  # "insurance" | "license" | "ticket"
    licensing_plate: str
    insurance_valid_to: date | None = None
    insurance_file_url: str | None = None
    license_valid_to: date | None = None
    license_file_url: str | None = None
    ticket_type: str | None = None
    violation_desc: str | None = None
    amount: Decimal | None = None
    issued_ts: datetime | None = None
    due_date: date | None = None
    authority: str | None = None
    ticket_file_url: str | None = None


class DocumentExtractedResponse(BaseModel):
    status: str  # "updated" | "review_required"
    event_id: UUID | None = None
    report_id: UUID | None = None


# --- Reports ---

class ReportCreate(BaseModel):
    vehicle_id: UUID
    driver_id: UUID | None = None
    ticket_type: str
    violation_desc: str | None = None
    amount: Decimal | None = None
    issued_ts: datetime | None = None
    due_date: date | None = None
    location: str | None = None
    authority: str | None = None
    file_url: str | None = None


class ReportRead(BaseModel):
    report_id: UUID
    vehicle_id: UUID
    ticket_type: str
    status: str
    amount: Decimal | None = None


# --- Events ---

class EventCreate(BaseModel):
    vehicle_id: UUID | None = None
    event_type: str
    severity: str
    message: str
    payload_json: dict | None = None
    source_type: str | None = None
    source_id: UUID | None = None


class EventRead(BaseModel):
    event_id: UUID
    vehicle_id: UUID | None = None
    event_type: str
    severity: str
    message: str
    status: str
    triggered_ts: datetime


# --- Config ---

class ConfigRead(BaseModel):
    config_key: str
    config_value: object
    description: str | None = None


class ConfigUpdate(BaseModel):
    config_value: object


# --- KPI daily rollup ---

class KpiDailyRead(BaseModel):
    snapshot_date: date
    total_km_7d: int | None = None
    avg_km_per_driver_7d: Decimal | None = None
    avg_days_between_maintenance: Decimal | None = None
    maintenance_due_count: int | None = None
    docs_expiring_count: int | None = None
    top_customer_id: UUID | None = None
    top_customer_km: int | None = None
    top_customer_vehicle_count: int | None = None
    computed_ts: datetime
