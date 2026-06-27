"""Pydantic request/response schemas for Fleet API."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

from shepherd_db.models import VehicleTypeEnum


def _validate_steps(v: list[str]) -> list[str]:
    cleaned = [s.strip() for s in v if s and s.strip()]
    if not cleaned:
        raise ValueError("at least one step is required")
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("step labels must be unique")
    return cleaned


# --- Vehicles ---

class VehicleCreate(BaseModel):
    licensing_plate: str
    nickname: str | None = None
    vehicle_type: VehicleTypeEnum | None = None  # motorcycle | car | van | bus | truck
    vendor: str | None = None
    model: str | None = None
    current_km: int | None = None
    allowed_driver: str | None = None
    driver_id: UUID | None = None
    customer_id: UUID | None = None
    maintenance_type_id: UUID | None = None
    insurance_valid_to: date | None = None
    license_valid_to: date | None = None


class VehicleUpdate(BaseModel):
    """PATCH /vehicles/{id} — all fields optional; only provided keys are written."""
    licensing_plate: str | None = None
    nickname: str | None = None
    vehicle_type: VehicleTypeEnum | None = None
    vendor: str | None = None
    model: str | None = None
    current_km: int | None = None
    allowed_driver: str | None = None
    driver_id: UUID | None = None
    customer_id: UUID | None = None
    maintenance_type_id: UUID | None = None
    insurance_valid_to: date | None = None
    license_valid_to: date | None = None


class VehicleRead(BaseModel):
    vehicle_id: UUID
    licensing_plate: str
    nickname: str | None = None
    vehicle_type: VehicleTypeEnum | None = None
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
    maintenance_type_id: UUID | None = None
    maintenance_type_name: str | None = None
    allowed_driver: str | None = None


# --- Drivers ---

class DriverCreate(BaseModel):
    full_name: str
    phone_number: str
    license_number: str | None = None
    license_valid_to: date | None = None


class DriverUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    license_number: str | None = None
    license_valid_to: date | None = None
    status: str | None = None


class DriverRead(BaseModel):
    driver_id: UUID
    full_name: str
    phone_number: str
    license_number: str | None = None
    license_valid_to: date | None = None
    status: str


# --- Customers ---

class CustomerCreate(BaseModel):
    full_name: str
    phone_number: str | None = None
    email: str | None = None


class CustomerUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    email: str | None = None
    status: str | None = None


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
    driver_id: UUID | None = None
    datetime: datetime
    location: str | None = None
    description: str | None = None
    another_driver_licensing_plate: str | None = None
    another_driver_phone_number: str | None = None
    another_driver_id_number: str | None = None
    attachments: list[AccidentAttachmentIn] = []


class AccidentRead(BaseModel):
    accident_id: UUID


class AccidentAttachmentOut(BaseModel):
    attachment_id: UUID
    category: str
    file_url: str
    uploaded_ts: datetime


class AccidentListItem(BaseModel):
    accident_id: UUID
    vehicle_id: UUID
    driver_id: UUID | None
    datetime: datetime
    location: str | None
    description: str | None
    another_driver_licensing_plate: str | None
    another_driver_phone_number: str | None
    another_driver_id_number: str | None
    attachments: list[AccidentAttachmentOut]


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


# --- Maintenance types (admin catalog) ---

class MaintenanceTypeCreate(BaseModel):
    name: str
    description: str | None = None
    interval_km: int
    steps: list[str]

    @field_validator("interval_km")
    @classmethod
    def _interval_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("interval_km must be a positive number")
        return v

    @field_validator("steps")
    @classmethod
    def _steps(cls, v: list[str]) -> list[str]:
        return _validate_steps(v)


class MaintenanceTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    interval_km: int | None = None
    steps: list[str] | None = None

    @field_validator("interval_km")
    @classmethod
    def _interval_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("interval_km must be a positive number")
        return v

    @field_validator("steps")
    @classmethod
    def _steps(cls, v: list[str] | None) -> list[str] | None:
        return _validate_steps(v) if v is not None else v


class MaintenanceTypeRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    interval_km: int
    steps: list[str]


# --- Attendance ---

class AttendanceRecordRead(BaseModel):
    driver_id: UUID
    work_date: date
    clock_in: str | None = None
    clock_out: str | None = None
    status: str


class AttendancePatch(BaseModel):
    clock_in: str | None = None
    clock_out: str | None = None
    status: str  # present | late | leave | absent


class AttendanceDayRead(BaseModel):
    driver_id: UUID
    driver_name: str | None = None
    clock_in: str | None = None
    clock_out: str | None = None
    status: str


class ClockRequest(BaseModel):
    driver_id: UUID


class ClockResponse(BaseModel):
    result: str  # ok | already_in | no_open | blocked | disabled
    time: str | None = None
    hours: str | None = None
    window_start: str | None = None
    window_end: str | None = None


# --- Bot users, enrollment, and authorizations ---

class BotWhoamiResponse(BaseModel):
    role: str
    driver_id: UUID | None = None
    driver_name: str | None = None
    user_id: UUID
    company_id: UUID | None = None
    # Lets the bot hide the clock button when the company has attendance disabled.
    attendance_enabled: bool = False
    # True when the resolved identity is the platform operator (System Admin).
    is_system_admin: bool = False
    # The built-in Playground (is_internal) company id, so the bot's Debug mode knows
    # which company to impersonate within. Only populated for the System Admin.
    playground_company_id: UUID | None = None


class BotEnrollRequest(BaseModel):
    telegram_chat_id: int
    phone_number: str


class BotEnrollResponse(BaseModel):
    role: str
    driver_id: UUID | None = None
    driver_name: str | None = None
    user_id: UUID
    expires_at: datetime | None = None
    is_system_admin: bool = False


class BotAuthorizationCreate(BaseModel):
    phone_number: str
    role: str = "driver"
    driver_id: UUID | None = None
    expires_at: datetime | None = None


class BotAuthorizationRead(BaseModel):
    id: UUID
    phone_number: str
    role: str
    driver_id: UUID | None = None
    driver_name: str | None = None
    expires_at: datetime | None = None
    created_at: datetime


class BotUserRead(BaseModel):
    user_id: UUID
    telegram_chat_id: int
    role: str
    phone_number: str | None = None
    driver_id: UUID | None = None
    driver_name: str | None = None
    expires_at: datetime | None = None
    created_at: datetime


class UserRolePatch(BaseModel):
    role: str


# --- Companies (system-admin only) ---

class CompanyCreate(BaseModel):
    name: str


class CompanyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class CompanyRead(BaseModel):
    company_id: UUID
    name: str
    is_active: bool
    created_at: datetime


# --- Per-company settings (Drive + feature flags; system-admin only) ---

class CompanySettingsRead(BaseModel):
    company_id: UUID
    gdrive_folder_id: str | None = None
    # The raw credentials blob is a secret and is never returned - only whether it's set.
    gdrive_configured: bool
    feature_flags: dict = {}


class CompanySettingsUpdate(BaseModel):
    gdrive_folder_id: str | None = None
    gdrive_credentials_json: str | None = None
    feature_flags: dict | None = None


# --- App users (credentialed identity; system-admin only) ---

class AppUserCreate(BaseModel):
    email: str
    password: str
    role: str  # admin | company_admin
    company_id: UUID | None = None
    name: str | None = None
    is_system_admin: bool = False
    phone_number: str | None = None


class AppUserUpdate(BaseModel):
    password: str | None = None
    is_active: bool | None = None
    name: str | None = None
    is_system_admin: bool | None = None
    phone_number: str | None = None


class AttendanceSettings(BaseModel):
    """Per-company attendance clock-in window (stored in system_config)."""
    enabled: bool = False
    start: str = "00:00"
    end: str = "23:59"


class AppUserRead(BaseModel):
    user_id: UUID
    email: str
    role: str
    company_id: UUID | None = None
    is_active: bool
    name: str | None = None
    is_system_admin: bool = False
    phone_number: str | None = None
    created_at: datetime


# --- Auth / login (channel-agnostic) ---

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user: AppUserRead
    token: str
    # The user's company feature flags (empty for a system admin with no company), so the
    # webui can gate nav without a round-trip.
    feature_flags: dict = {}


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


# --- System admin (Telegram operator) ---

class SystemOverviewItem(BaseModel):
    company_id: UUID
    name: str
    vehicle_count: int
    driver_count: int
    open_event_count: int
    attendance_enabled: bool
    gdrive_configured: bool


class SystemOverview(BaseModel):
    companies: list[SystemOverviewItem]


class ImpersonationAuditCreate(BaseModel):
    company_id: UUID
    effective_role: str
    effective_id: str | None = None
    action: str  # start | stop | write
    detail: str | None = None
