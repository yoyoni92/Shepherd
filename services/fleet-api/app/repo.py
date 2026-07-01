"""Data access layer - SQLAlchemy ORM, all Postgres writes go through here."""
from datetime import UTC, date
from uuid import UUID

from shepherd_db.logic import next_maintenance
from shepherd_db.models import (
    Accident,
    AccidentAttachment,
    AppUser,
    AttendanceRecord,
    BotAuthorization,
    BotUser,
    Company,
    CompanySettings,
    Customer,
    Driver,
    Event,
    ImpersonationAudit,
    KmUpdate,
    KpiDaily,
    MaintenanceType,
    Report,
    SystemConfig,
    Vehicle,
    VehicleCare,
)
from shepherd_db.security import hash_password
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

def get_vehicle_by_plate(
    session: Session, plate: str, *, company_id: UUID | None = None
) -> Vehicle | None:
    stmt = select(Vehicle).where(Vehicle.licensing_plate == plate)
    if company_id is not None:
        stmt = stmt.where(Vehicle.company_id == company_id)
    return session.execute(stmt).scalar_one_or_none()


def get_vehicle_by_id(session: Session, vehicle_id: UUID) -> Vehicle | None:
    return session.get(Vehicle, vehicle_id)


def list_vehicles(
    session: Session,
    *,
    driver_id: UUID | None = None,
    customer_id: UUID | None = None,
    company_id: UUID | None = None,
) -> list[Vehicle]:
    stmt = select(Vehicle)
    if company_id is not None:
        stmt = stmt.where(Vehicle.company_id == company_id)
    if driver_id is not None:
        stmt = stmt.where(Vehicle.driver_id == driver_id)
    elif customer_id is not None:
        stmt = stmt.where(Vehicle.customer_id == customer_id)
    return list(session.execute(stmt).scalars())


def apply_cycle_position(vehicle: Vehicle) -> dict:
    """Recompute next_* service fields from the vehicle's last_maintenance_* and its cycle.

    Pointer-set only: writes next_maintenance_type/_km/_date on the vehicle and returns the
    next_maintenance() result. Does not create care rows or touch events.
    """
    mtype = vehicle.maintenance_type
    steps = mtype.steps if mtype else [vehicle.last_maintenance_type]
    interval_km = mtype.interval_km if mtype else 10_000
    interval_months = mtype.interval_months if mtype else None
    nm = next_maintenance(
        vehicle.last_maintenance_type,
        steps,
        last_km=vehicle.last_maintenance_km or 0,
        interval_km=interval_km,
        last_date=vehicle.last_maintenance_date,
        interval_months=interval_months,
    )
    vehicle.next_maintenance_km = nm["next_km"]
    vehicle.next_maintenance_date = nm["next_date"]
    vehicle.next_maintenance_type = nm["next_type"]
    return nm


def create_vehicle(session: Session, data: dict) -> Vehicle:
    vehicle = Vehicle(**data)
    session.add(vehicle)
    session.flush()
    if vehicle.last_maintenance_type is not None:
        apply_cycle_position(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


def update_vehicle(session: Session, vehicle_id: UUID, data: dict) -> Vehicle | None:
    vehicle = session.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None
    for key, value in data.items():
        setattr(vehicle, key, value)
    session.commit()
    session.refresh(vehicle)
    return vehicle


def delete_vehicle(session: Session, vehicle_id: UUID) -> bool:
    vehicle = session.get(Vehicle, vehicle_id)
    if vehicle is None:
        return False
    session.delete(vehicle)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

def get_driver(session: Session, driver_id: UUID) -> Driver | None:
    return session.get(Driver, driver_id)


def list_drivers(session: Session, *, company_id: UUID | None = None) -> list[Driver]:
    stmt = select(Driver)
    if company_id is not None:
        stmt = stmt.where(Driver.company_id == company_id)
    return list(session.execute(stmt).scalars())


def create_driver(session: Session, data: dict) -> Driver:
    driver = Driver(**data)
    session.add(driver)
    session.commit()
    session.refresh(driver)
    return driver


def update_driver(session: Session, driver_id: UUID, data: dict) -> Driver | None:
    driver = session.get(Driver, driver_id)
    if driver is None:
        return None
    for key, value in data.items():
        setattr(driver, key, value)
    session.commit()
    session.refresh(driver)
    return driver


def delete_driver(session: Session, driver_id: UUID) -> bool:
    driver = session.get(Driver, driver_id)
    if driver is None:
        return False
    session.delete(driver)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def get_customer(session: Session, customer_id: UUID) -> Customer | None:
    return session.get(Customer, customer_id)


def list_customers(session: Session, *, company_id: UUID | None = None) -> list[Customer]:
    stmt = select(Customer)
    if company_id is not None:
        stmt = stmt.where(Customer.company_id == company_id)
    return list(session.execute(stmt).scalars())


def create_customer(session: Session, data: dict) -> Customer:
    customer = Customer(**data)
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


def update_customer(session: Session, customer_id: UUID, data: dict) -> Customer | None:
    customer = session.get(Customer, customer_id)
    if customer is None:
        return None
    for key, value in data.items():
        setattr(customer, key, value)
    session.commit()
    session.refresh(customer)
    return customer


def delete_customer(session: Session, customer_id: UUID) -> bool:
    customer = session.get(Customer, customer_id)
    if customer is None:
        return False
    # cascade: unlink the customer from any vehicles before removing (FK would block)
    session.execute(
        update(Vehicle).where(Vehicle.customer_id == customer_id).values(customer_id=None)
    )
    session.delete(customer)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# KM updates
# ---------------------------------------------------------------------------

def get_maintenance_buffer(session: Session, company_id: UUID | None = None) -> int:
    cfg = session.get(SystemConfig, (company_id, "maintenance_km_buffer"))
    return int(cfg.config_value) if cfg is not None else 500


def get_km_max_increment(session: Session, company_id: UUID | None = None) -> int:
    """Max KM a single update may add over current_km (typo guard). Per-company config."""
    cfg = session.get(SystemConfig, (company_id, "km_max_increment"))
    return int(cfg.config_value) if cfg is not None else 10000


def _has_open_maintenance_due(session: Session, vehicle_id: UUID) -> bool:
    """True if the vehicle already has an unresolved maintenance_due event."""
    return session.scalar(
        select(Event.event_id)
        .where(
            Event.vehicle_id == vehicle_id,
            Event.event_type == "maintenance_due",
            Event.status == "open",
        )
        .limit(1)
    ) is not None


def update_km(
    session: Session,
    vehicle_id: UUID,
    km: int,
    *,
    driver_id: UUID | None,
    source: str,
) -> tuple[UUID, bool]:
    """Insert km_update row, update vehicle.current_km.

    Returns (km_update_id, maintenance_triggered).
    """
    # Load the vehicle first so the km_update + any derived event inherit its company_id.
    vehicle = session.get(Vehicle, vehicle_id)
    assert vehicle is not None, f"Vehicle {vehicle_id} not found"
    km_update = KmUpdate(
        vehicle_id=vehicle_id, km=km, driver_id=driver_id, source=source,
        company_id=vehicle.company_id,
    )
    session.add(km_update)
    session.flush()  # get km_update_id before checking trigger

    vehicle.current_km = km

    triggered = False
    if vehicle.next_maintenance_km is not None:
        buffer = get_maintenance_buffer(session, vehicle.company_id)
        # One open maintenance_due per cycle: skip if the cron or a prior km report
        # already opened one (resolved by create_care on the next service).
        if (
            km >= vehicle.next_maintenance_km - buffer
            and not _has_open_maintenance_due(session, vehicle_id)
        ):
            event = Event(
                vehicle_id=vehicle_id,
                event_type="maintenance_due",
                severity="warning",
                message="Maintenance due soon",
                source_type="km_updates",
                source_id=km_update.km_update_id,
                company_id=vehicle.company_id,
                payload_json={"trigger": "km"},
            )
            session.add(event)
            triggered = True

    session.commit()
    return km_update.km_update_id, triggered


# ---------------------------------------------------------------------------
# Accidents
# ---------------------------------------------------------------------------

def create_accident(session: Session, data: dict, attachments: list[dict]) -> UUID:
    # data carries company_id (router copies it off the loaded vehicle); attachments
    # and the derived event inherit it from the accident.
    accident = Accident(**data)
    session.add(accident)
    session.flush()

    for att in attachments:
        session.add(AccidentAttachment(
            accident_id=accident.accident_id, company_id=accident.company_id, **att
        ))

    session.add(Event(
        vehicle_id=accident.vehicle_id,
        event_type="accident_logged",
        severity="critical",
        message="Accident logged",
        source_type="accidents",
        source_id=accident.accident_id,
        company_id=accident.company_id,
    ))
    session.commit()
    return accident.accident_id


def list_accidents(session: Session, *, company_id: UUID | None = None) -> list[Accident]:
    stmt = (
        select(Accident)
        .options(selectinload(Accident.attachments))
        .order_by(Accident.datetime.desc())
    )
    if company_id is not None:
        stmt = stmt.where(Accident.company_id == company_id)
    return list(session.scalars(stmt))


# ---------------------------------------------------------------------------
# Vehicle care
# ---------------------------------------------------------------------------

def create_care(session: Session, data: dict) -> VehicleCare:
    # Care inherits company_id from its vehicle (set before flush - it's NOT NULL).
    vehicle = session.get(Vehicle, data["vehicle_id"])
    assert vehicle is not None, f"Vehicle {data['vehicle_id']} not found"
    care = VehicleCare(**data, company_id=vehicle.company_id)
    session.add(care)
    session.flush()

    vehicle.last_maintenance_date = care.service_date
    vehicle.last_maintenance_type = care.maintenance_type
    vehicle.last_maintenance_km = care.km_at_service
    nm = apply_cycle_position(vehicle)

    # Cycle reset: resolve any open maintenance_due event so the next due (km or
    # time, whichever first) can emit a fresh one.
    for ev in session.scalars(
        select(Event).where(
            Event.vehicle_id == care.vehicle_id,
            Event.event_type == "maintenance_due",
            Event.status == "open",
        )
    ):
        ev.status = "resolved"

    session.commit()
    session.refresh(care)
    # Attach computed next values for the API response; not persisted to DB.
    # These are runtime-only instance attrs on the ORM object.
    care._next_km = nm["next_km"]  # type: ignore[attr-defined]
    care._next_date = nm["next_date"]  # type: ignore[attr-defined]
    care._next_type = nm["next_type"]  # type: ignore[attr-defined]
    return care


# ---------------------------------------------------------------------------
# Documents extracted
# ---------------------------------------------------------------------------

def process_extracted_doc(
    session: Session, payload: dict, *, company_id: UUID | None = None
) -> tuple[str, UUID | None, UUID | None]:
    """Apply extracted document to DB. Returns (status, event_id, report_id).

    The matched vehicle's company_id is inherited by the report + events. When the
    plate is not found there is no vehicle, so the review event is tagged with the
    caller's company_id instead.
    """
    plate = payload["licensing_plate"]
    vehicle = get_vehicle_by_plate(session, plate, company_id=company_id)

    if vehicle is None:
        event = Event(
            event_type="ticket_received",
            severity="warning",
            message="Extracted doc plate not found in fleet",
            payload_json={"plate": plate},
            company_id=company_id,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return "review_required", event.event_id, None

    doc_type = payload["doc_type"]
    report_id = None

    if doc_type == "insurance":
        if payload.get("insurance_valid_to"):
            vehicle.insurance_valid_to = payload["insurance_valid_to"]
        if payload.get("insurance_file_url"):
            vehicle.insurance_file_url = payload["insurance_file_url"]
    elif doc_type == "license":
        if payload.get("license_valid_to"):
            vehicle.license_valid_to = payload["license_valid_to"]
    elif doc_type == "ticket":
        report = Report(
            vehicle_id=vehicle.vehicle_id,
            ticket_type=payload.get("ticket_type", "traffic"),
            violation_desc=payload.get("violation_desc"),
            amount=payload.get("amount"),
            issued_ts=payload.get("issued_ts"),
            due_date=payload.get("due_date"),
            authority=payload.get("authority"),
            file_url=payload.get("ticket_file_url"),
            company_id=vehicle.company_id,
        )
        session.add(report)
        session.flush()
        session.add(Event(
            vehicle_id=vehicle.vehicle_id,
            event_type="ticket_received",
            severity="warning",
            message="Ticket received via doc extraction",
            source_type="reports",
            source_id=report.report_id,
            company_id=vehicle.company_id,
        ))
        report_id = report.report_id

    session.commit()
    return "updated", None, report_id


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def list_reports(session: Session, *, company_id: UUID | None = None) -> list[Report]:
    stmt = select(Report).order_by(Report.created_ts.desc())
    if company_id is not None:
        stmt = stmt.where(Report.company_id == company_id)
    return list(session.execute(stmt).scalars())


def create_report(session: Session, data: dict) -> Report:
    report = Report(**data)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def list_events(
    session: Session, vehicle_id: UUID | None = None, *, company_id: UUID | None = None
) -> list[Event]:
    stmt = select(Event).order_by(Event.triggered_ts.desc())
    if company_id is not None:
        stmt = stmt.where(Event.company_id == company_id)
    if vehicle_id is not None:
        stmt = stmt.where(Event.vehicle_id == vehicle_id)
    return list(session.execute(stmt).scalars())


def create_event(session: Session, data: dict) -> Event:
    event = Event(**data)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


# ---------------------------------------------------------------------------
# System config
# ---------------------------------------------------------------------------

def get_all_config(session: Session, company_id: UUID | None = None) -> list[SystemConfig]:
    stmt = select(SystemConfig).order_by(SystemConfig.config_key)
    if company_id is not None:
        stmt = stmt.where(SystemConfig.company_id == company_id)
    return list(session.execute(stmt).scalars())


def get_config_key(
    session: Session, key: str, company_id: UUID | None = None
) -> SystemConfig | None:
    return session.get(SystemConfig, (company_id, key))


# ---------------------------------------------------------------------------
# Maintenance types (admin-managed catalog)
# ---------------------------------------------------------------------------

def list_maintenance_types(
    session: Session, *, company_id: UUID | None = None
) -> list[MaintenanceType]:
    stmt = select(MaintenanceType).order_by(MaintenanceType.name)
    if company_id is not None:
        stmt = stmt.where(MaintenanceType.company_id == company_id)
    return list(session.execute(stmt).scalars())


def get_maintenance_type(session: Session, type_id: UUID) -> MaintenanceType | None:
    return session.get(MaintenanceType, type_id)


def create_maintenance_type(session: Session, data: dict) -> MaintenanceType:
    mtype = MaintenanceType(**data)
    session.add(mtype)
    session.commit()
    session.refresh(mtype)
    return mtype


def update_maintenance_type(session: Session, type_id: UUID, data: dict) -> MaintenanceType | None:
    mtype = session.get(MaintenanceType, type_id)
    if mtype is None:
        return None
    for key, value in data.items():
        setattr(mtype, key, value)
    session.commit()
    session.refresh(mtype)
    return mtype


def count_vehicles_for_maintenance_type(session: Session, type_id: UUID) -> int:
    return session.scalar(
        select(func.count()).select_from(Vehicle).where(Vehicle.maintenance_type_id == type_id)
    ) or 0


def delete_maintenance_type(session: Session, type_id: UUID) -> bool:
    mtype = session.get(MaintenanceType, type_id)
    if mtype is None:
        return False
    session.delete(mtype)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Attendance (drivers as employees)
# ---------------------------------------------------------------------------

def list_attendance_month(
    session: Session, year: int, month: int, driver_id: UUID | None = None,
    *, company_id: UUID | None = None,
) -> list[AttendanceRecord]:
    from calendar import monthrange
    from datetime import date

    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    stmt = select(AttendanceRecord).where(AttendanceRecord.work_date.between(start, end))
    if company_id is not None:
        stmt = stmt.where(AttendanceRecord.company_id == company_id)
    if driver_id is not None:
        stmt = stmt.where(AttendanceRecord.driver_id == driver_id)
    return list(session.execute(stmt.order_by(AttendanceRecord.work_date)).scalars())


def list_attendance_day(
    session: Session, work_date, *, company_id: UUID | None = None
) -> list[tuple[AttendanceRecord, str]]:
    """Records for a single day joined with driver names (for the admin view)."""
    stmt = (
        select(AttendanceRecord, Driver.full_name)
        .join(Driver, Driver.driver_id == AttendanceRecord.driver_id)
        .where(AttendanceRecord.work_date == work_date)
        .order_by(AttendanceRecord.clock_in)
    )
    if company_id is not None:
        stmt = stmt.where(AttendanceRecord.company_id == company_id)
    return [(r, name) for r, name in session.execute(stmt).all()]


def attendance_clock_in(
    session: Session, driver_id: UUID, time_str: str, work_date
) -> tuple[str, str | None]:
    rec = session.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.driver_id == driver_id,
            AttendanceRecord.work_date == work_date,
        )
    ).scalar_one_or_none()
    if rec is not None and rec.clock_in:
        return ("already_in", rec.clock_in)
    if rec is None:
        driver = session.get(Driver, driver_id)
        rec = AttendanceRecord(
            driver_id=driver_id, work_date=work_date, clock_in=time_str, status="present",
            company_id=driver.company_id if driver else None,
        )
        session.add(rec)
    else:
        rec.clock_in = time_str
    session.commit()
    return ("ok", time_str)


def attendance_clock_out(
    session: Session, driver_id: UUID, time_str: str, work_date
) -> tuple[str, str | None, str | None]:
    rec = session.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.driver_id == driver_id,
            AttendanceRecord.work_date == work_date,
            AttendanceRecord.clock_in.is_not(None),
            AttendanceRecord.clock_out.is_(None),
        )
    ).scalar_one_or_none()
    if rec is None:
        return ("no_open", None, None)
    rec.clock_out = time_str
    ih, im = (int(x) for x in rec.clock_in.split(":"))
    oh, om = (int(x) for x in time_str.split(":"))
    hours = f"{((oh * 60 + om) - (ih * 60 + im)) / 60:.2f}"
    session.commit()
    return ("ok", time_str, hours)


def upsert_attendance(session: Session, driver_id: UUID, work_date, data: dict) -> AttendanceRecord:
    rec = session.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.driver_id == driver_id,
            AttendanceRecord.work_date == work_date,
        )
    ).scalar_one_or_none()
    if rec is None:
        driver = session.get(Driver, driver_id)
        rec = AttendanceRecord(
            driver_id=driver_id, work_date=work_date,
            company_id=driver.company_id if driver else None, **data,
        )
        session.add(rec)
    else:
        for key, value in data.items():
            setattr(rec, key, value)
    session.commit()
    session.refresh(rec)
    return rec


# ---------------------------------------------------------------------------
# KPI daily rollup (read-only; populated by refresh_kpi_daily())
# ---------------------------------------------------------------------------

def list_kpi_daily(
    session: Session, limit: int = 2, *, company_id: UUID | None = None
) -> list[KpiDaily]:
    stmt = select(KpiDaily).order_by(KpiDaily.snapshot_date.desc())
    if company_id is not None:
        stmt = stmt.where(KpiDaily.company_id == company_id)
    return list(session.execute(stmt.limit(limit)).scalars())


# ---------------------------------------------------------------------------
# Bot users, enrollment, and authorizations
# ---------------------------------------------------------------------------

def get_bot_user_by_chat_id(session: Session, chat_id: int) -> BotUser | None:
    return session.execute(
        select(BotUser).where(BotUser.telegram_chat_id == chat_id)
    ).scalar_one_or_none()


def list_bot_users(
    session: Session, role: str | None = None, *, company_id: UUID | None = None
) -> list[BotUser]:
    stmt = select(BotUser)
    # company_id is nullable on bot tables (writers land in Feature 3); only filter when given.
    if company_id is not None:
        stmt = stmt.where(BotUser.company_id == company_id)
    if role is not None:
        stmt = stmt.where(BotUser.role == role)
    return list(session.execute(stmt).scalars())


def update_bot_user_role(session: Session, user_id: UUID, role: str) -> BotUser | None:
    user = session.get(BotUser, user_id)
    if user is None:
        return None
    user.role = role
    session.commit()
    session.refresh(user)
    return user


def _normalize_phone(p: str) -> str:
    import re
    digits = re.sub(r'\D', '', p)
    if digits.startswith('972'):
        digits = '0' + digits[3:]
    return digits


def _registered_schemas(session: Session) -> list[str]:
    """Distinct schema_names from company_settings, plus the shared schema."""
    from shepherd_config import get_config

    rows = session.execute(
        select(CompanySettings.schema_name).distinct()
    ).scalars().all()
    # Exclude NULL and '__pending__' (companies awaiting provisioning, same
    # guard as _resolve_schema in deps.py).
    schemas = {s for s in rows if s and s != "__pending__"}
    schemas.add(get_config().database.shared_schema)
    return sorted(schemas)


def find_enrollment_by_phone(session: Session, phone: str):
    """(role, driver_id, expires_at, company_id) for a phone, or None.

    An active driver wins (permanent driver role); otherwise a non-expired
    bot_authorization. Drivers live in per-company schemas, so the driver match
    scans every registered schema (the bounded cross-schema exception for this
    company-less read); bot_authorizations is public and scanned once on the
    request session.

    # ponytail: O(schemas x drivers) phone scan - fleets are small and schemas
    # few; a normalized phone index per schema is the ceiling if a deployment
    # ever grows large.
    """
    from datetime import datetime

    from shepherd_config import get_config

    target = _normalize_phone(phone)
    shared = get_config().database.shared_schema
    # session.bind is the connection; .engine gives the engine so we can open
    # schema-translated connections without going through the DI graph.
    from sqlalchemy import Connection as SAConnection
    assert isinstance(session.bind, SAConnection), "session.bind must be a Connection here"
    engine = session.bind.engine
    # Drivers live only in tenant (company) schemas. _registered_schemas() also appends the
    # shared schema, which holds no tenant tables, so search the distinct company schema_names
    # directly - querying <shared>.drivers would raise UndefinedTable.
    rows = session.execute(select(CompanySettings.schema_name).distinct()).scalars().all()
    company_schemas = sorted({s for s in rows if s and s != "__pending__"})
    for schema in company_schemas:
        with engine.connect() as conn:
            tconn = conn.execution_options(
                schema_translate_map={"tenant": schema, None: shared}
            )
            with Session(bind=tconn) as s:
                for d in s.execute(
                    select(Driver).where(Driver.status == "active")
                ).scalars():
                    if _normalize_phone(d.phone_number) == target:
                        return ("driver", d.driver_id, None, d.company_id)
    now = datetime.now(UTC)
    for a in session.execute(
        select(BotAuthorization).where(
            (BotAuthorization.expires_at.is_(None)) | (BotAuthorization.expires_at > now)
        )
    ).scalars():
        if _normalize_phone(a.phone_number) == target:
            role = a.role.value if hasattr(a.role, "value") else a.role
            return (role, a.driver_id, a.expires_at, a.company_id)
    return None


def enroll_bot_user(session: Session, telegram_chat_id: int, phone_number: str) -> BotUser | None:
    """Match the phone to a role and upsert the bot user. None when not authorized."""
    match = find_enrollment_by_phone(session, phone_number)
    if match is None:
        return None
    role, driver_id, expires_at, company_id = match
    existing = session.execute(
        select(BotUser).where(BotUser.telegram_chat_id == telegram_chat_id)
    ).scalar_one_or_none()
    if existing is not None:
        session.delete(existing)
        session.flush()
    user = BotUser(
        telegram_chat_id=telegram_chat_id, role=role, driver_id=driver_id,
        phone_number=phone_number, expires_at=expires_at, company_id=company_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_driver_for_bot_user(
    session: Session, company_id: UUID | None, driver_id: UUID | None
) -> tuple[str, str] | None:
    """A bot user's driver as ``(status, full_name)``, read from the company's schema.

    BotUser lives in the shared schema and its ``driver`` relationship cannot lazy-load
    across schemas, so resolve the tenant ``Driver`` on a connection translated to the
    company's schema. Returns None when there is no driver/company or the row is missing.
    """
    from shepherd_config import get_config

    if company_id is None or driver_id is None:
        return None
    settings = get_company_settings(session, company_id)
    if settings is None or not settings.schema_name or settings.schema_name == "__pending__":
        return None
    from sqlalchemy import Connection as SAConnection

    assert isinstance(session.bind, SAConnection), "session.bind must be a Connection here"
    shared = get_config().database.shared_schema
    with session.bind.engine.connect() as conn:
        tconn = conn.execution_options(
            schema_translate_map={"tenant": settings.schema_name, None: shared}
        )
        with Session(bind=tconn) as s:
            d = s.get(Driver, driver_id)
            if d is None:
                return None
            status = d.status.value if hasattr(d.status, "value") else d.status
            return (status, d.full_name)


def get_bot_user(session: Session, user_id: UUID) -> BotUser | None:
    return session.get(BotUser, user_id)


def get_bot_authorization(session: Session, auth_id: UUID) -> BotAuthorization | None:
    return session.get(BotAuthorization, auth_id)


def create_bot_authorization(
    session: Session, phone_number: str, role: str = "driver",
    driver_id: UUID | None = None, expires_at=None, *, company_id: UUID | None = None,
) -> BotAuthorization:
    from sqlalchemy import delete as sa_delete
    # One authorization per (company, phone) - supersede any prior within the same
    # tenant so the table stays clean without touching another company's grants.
    session.execute(
        sa_delete(BotAuthorization).where(
            BotAuthorization.phone_number == phone_number,
            BotAuthorization.company_id == company_id,
        )
    )
    auth = BotAuthorization(
        phone_number=phone_number, role=role, driver_id=driver_id,
        expires_at=expires_at, company_id=company_id,
    )
    session.add(auth)
    session.commit()
    session.refresh(auth)
    return auth


def list_bot_authorizations(
    session: Session, *, company_id: UUID | None = None
) -> list[BotAuthorization]:
    from datetime import datetime
    now = datetime.now(UTC)
    stmt = select(BotAuthorization).where(
        (BotAuthorization.expires_at.is_(None)) | (BotAuthorization.expires_at > now)
    )
    # company_id is nullable on bot tables (writers land in Feature 3); only filter when given.
    if company_id is not None:
        stmt = stmt.where(BotAuthorization.company_id == company_id)
    return list(session.execute(stmt).scalars())


def delete_bot_authorization(session: Session, auth_id: UUID) -> str:
    auth = session.get(BotAuthorization, auth_id)
    if auth is None:
        return "not_found"
    session.delete(auth)
    session.commit()
    return "ok"


# ---------------------------------------------------------------------------
# Companies (system-admin managed)
# ---------------------------------------------------------------------------

def list_companies(
    session: Session, *, include_internal: bool = False
) -> list[Company]:
    stmt = select(Company).order_by(Company.name)
    if not include_internal:
        stmt = stmt.where(Company.is_internal.is_(False))
    return list(session.execute(stmt).scalars())


def get_company(session: Session, company_id: UUID) -> Company | None:
    return session.get(Company, company_id)


def get_internal_company(session: Session) -> Company | None:
    """The built-in Playground (is_internal) company, or None when not seeded."""
    return session.execute(
        select(Company).where(Company.is_internal.is_(True)).order_by(Company.name)
    ).scalars().first()


def create_company(session: Session, data: dict) -> Company:
    company = Company(**data)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def update_company(session: Session, company_id: UUID, data: dict) -> Company | None:
    company = session.get(Company, company_id)
    if company is None:
        return None
    for key, value in data.items():
        setattr(company, key, value)
    session.commit()
    session.refresh(company)
    return company


def delete_company(session: Session, company_id: UUID) -> bool:
    company = session.get(Company, company_id)
    if company is None:
        return False
    session.delete(company)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Company settings (per-tenant config; 1:1 with companies)
# ---------------------------------------------------------------------------

_UNSET = object()


def get_company_settings(session: Session, company_id: UUID) -> CompanySettings | None:
    return session.get(CompanySettings, company_id)


def upsert_company_settings(
    session: Session,
    company_id: UUID,
    *,
    gdrive_folder_id=_UNSET,
    gdrive_credentials_json=_UNSET,
    feature_flags=_UNSET,
) -> CompanySettings:
    """Create-or-update the company's settings row, writing only provided fields."""
    from datetime import datetime

    row = session.get(CompanySettings, company_id)
    if row is None:
        row = CompanySettings(company_id=company_id)
        session.add(row)
    if gdrive_folder_id is not _UNSET:
        row.gdrive_folder_id = gdrive_folder_id
    if gdrive_credentials_json is not _UNSET:
        row.gdrive_credentials_json = gdrive_credentials_json
    if feature_flags is not _UNSET:
        row.feature_flags = feature_flags
    row.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(row)
    return row


def company_feature_enabled(session: Session, company_id: UUID, flag: str) -> bool:
    """True when the company's feature_flags has ``flag`` truthy (default False)."""
    row = session.get(CompanySettings, company_id)
    if row is None or not row.feature_flags:
        return False
    return bool(row.feature_flags.get(flag, False))


# ---------------------------------------------------------------------------
# App users (credentialed identity; system-admin managed)
# ---------------------------------------------------------------------------

def list_app_users(session: Session) -> list[AppUser]:
    return list(session.execute(select(AppUser).order_by(AppUser.email)).scalars())


def get_app_user(session: Session, user_id: UUID) -> AppUser | None:
    return session.get(AppUser, user_id)


def get_app_user_by_email(session: Session, email: str) -> AppUser | None:
    return session.execute(
        select(AppUser).where(AppUser.email == email)
    ).scalar_one_or_none()


def get_app_user_by_telegram_chat_id(session: Session, chat_id: int) -> AppUser | None:
    return session.execute(
        select(AppUser).where(AppUser.telegram_chat_id == chat_id)
    ).scalar_one_or_none()


def get_system_app_user_by_phone(session: Session, phone: str) -> AppUser | None:
    """A system-admin app_user whose phone matches (normalized), or None.

    Phones are normalized both sides like ``find_enrollment_by_phone``; operators are
    few so a scan is fine.
    """
    target = _normalize_phone(phone)
    for u in session.execute(
        select(AppUser).where(AppUser.is_system_admin.is_(True))
    ).scalars():
        if u.phone_number and _normalize_phone(u.phone_number) == target:
            return u
    return None


def link_app_user_telegram(session: Session, user: AppUser, chat_id: int) -> AppUser:
    user.telegram_chat_id = chat_id
    session.commit()
    session.refresh(user)
    return user


def list_company_admins(session: Session, company_id: UUID) -> list[AppUser]:
    return list(
        session.execute(
            select(AppUser)
            .where(AppUser.company_id == company_id, AppUser.role == "company_admin")
            .order_by(AppUser.email)
        ).scalars()
    )


def create_app_user(session: Session, data: dict) -> AppUser:
    data = dict(data)
    data["password_hash"] = hash_password(data.pop("password"))
    user = AppUser(**data)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_app_user(session: Session, user_id: UUID, data: dict) -> AppUser | None:
    user = session.get(AppUser, user_id)
    if user is None:
        return None
    data = dict(data)
    password = data.pop("password", None)
    if password is not None:
        user.password_hash = hash_password(password)
    for key, value in data.items():
        setattr(user, key, value)
    session.commit()
    session.refresh(user)
    return user


def delete_app_user(session: Session, user_id: UUID) -> bool:
    user = session.get(AppUser, user_id)
    if user is None:
        return False
    session.delete(user)
    session.commit()
    return True


def set_config(
    session: Session, key: str, value: object, company_id: UUID | None = None
) -> SystemConfig:
    from datetime import datetime
    cfg = session.get(SystemConfig, (company_id, key))
    if cfg is None:
        cfg = SystemConfig(
            company_id=company_id, config_key=key, config_value=value,
            updated_ts=datetime.now(UTC),
        )
        session.add(cfg)
    else:
        cfg.config_value = value
        cfg.updated_ts = datetime.now(UTC)
    session.commit()
    session.refresh(cfg)
    return cfg


# ---------------------------------------------------------------------------
# System admin (Telegram operator): cross-company overview + impersonation audit
# ---------------------------------------------------------------------------

def system_overview(session: Session) -> list[dict]:
    """Per-company counts + health flags for the system overview.

    All tenant-table counts (vehicles, drivers, events, customers, accidents,
    reports) are run against each company's own Postgres schema using a
    schema_translate_map translated connection - the same pattern used by
    find_enrollment_by_phone and refresh_kpi_daily. Companies whose
    schema_name is '__pending__' (schema not yet provisioned) get 0 for all
    tenant counts. Public-table reads (kpi_daily, BotUser, company_settings)
    stay on the main session.
    """
    from datetime import timedelta

    from shepherd_config import get_config
    from sqlalchemy import Connection as SAConnection
    from sqlalchemy import or_

    shared = get_config().database.shared_schema
    assert isinstance(session.bind, SAConnection), "session.bind must be a Connection"
    engine = session.bind.engine

    today = date.today()
    docs_cutoff = today + timedelta(days=30)

    overview: list[dict] = []
    for c in session.execute(
        select(Company).where(Company.is_internal.is_(False)).order_by(Company.name)
    ).scalars():
        settings = session.get(CompanySettings, c.company_id)
        schema_name = settings.schema_name if settings else shared
        attendance_enabled = bool(
            settings and settings.feature_flags and settings.feature_flags.get("attendance")
        )
        gdrive_configured = bool(settings and settings.gdrive_credentials_json)

        # Public-table reads: BotUser count and latest kpi_daily snapshot.
        bot_user_count = session.scalar(
            select(func.count()).select_from(BotUser).where(
                BotUser.company_id == c.company_id
            )
        ) or 0

        kpi_row = session.execute(
            select(KpiDaily)
            .where(KpiDaily.company_id == c.company_id)
            .order_by(KpiDaily.snapshot_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        total_km_7d = int(kpi_row.total_km_7d) if (kpi_row and kpi_row.total_km_7d) else 0

        # Tenant-table reads: open a schema-translated connection per company.
        if schema_name == "__pending__":
            vehicle_count = driver_count = open_event_count = 0
            customer_count = accident_count = maintenance_due_count = 0
            docs_expiring_count = unpaid_report_count = 0
        else:
            with engine.connect() as conn:
                tconn = conn.execution_options(
                    schema_translate_map={"tenant": schema_name, None: shared}
                )
                with Session(bind=tconn) as s:
                    vehicle_count = s.scalar(
                        select(func.count()).select_from(Vehicle).where(
                            Vehicle.company_id == c.company_id
                        )
                    ) or 0
                    driver_count = s.scalar(
                        select(func.count()).select_from(Driver).where(
                            Driver.company_id == c.company_id
                        )
                    ) or 0
                    open_event_count = s.scalar(
                        select(func.count()).select_from(Event).where(
                            Event.company_id == c.company_id,
                            Event.status == "open",
                        )
                    ) or 0
                    customer_count = s.scalar(
                        select(func.count()).select_from(Customer).where(
                            Customer.company_id == c.company_id
                        )
                    ) or 0
                    accident_count = s.scalar(
                        select(func.count()).select_from(Accident).where(
                            Accident.company_id == c.company_id
                        )
                    ) or 0
                    maintenance_due_count = s.scalar(
                        select(func.count()).select_from(Vehicle).where(
                            Vehicle.company_id == c.company_id,
                            Vehicle.current_km.is_not(None),
                            Vehicle.next_maintenance_km.is_not(None),
                            Vehicle.current_km >= Vehicle.next_maintenance_km,
                        )
                    ) or 0
                    docs_expiring_count = s.scalar(
                        select(func.count()).select_from(Vehicle).where(
                            Vehicle.company_id == c.company_id,
                            or_(
                                Vehicle.insurance_valid_to <= docs_cutoff,
                                Vehicle.license_valid_to <= docs_cutoff,
                            ),
                        )
                    ) or 0
                    unpaid_report_count = s.scalar(
                        select(func.count()).select_from(Report).where(
                            Report.company_id == c.company_id,
                            Report.status == "unpaid",
                        )
                    ) or 0

        overview.append({
            "company_id": c.company_id,
            "name": c.name,
            "is_active": c.is_active,
            "schema_name": schema_name,
            "vehicle_count": vehicle_count,
            "driver_count": driver_count,
            "open_event_count": open_event_count,
            "attendance_enabled": attendance_enabled,
            "gdrive_configured": gdrive_configured,
            "customer_count": customer_count,
            "accident_count": accident_count,
            "maintenance_due_count": maintenance_due_count,
            "docs_expiring_count": docs_expiring_count,
            "unpaid_report_count": unpaid_report_count,
            "total_km_7d": total_km_7d,
            "bot_user_count": bot_user_count,
        })
    return overview


def write_impersonation_audit(
    session: Session,
    *,
    operator_id: UUID,
    company_id: UUID,
    effective_role: str,
    effective_id: str | None,
    action: str,
    detail: str | None = None,
) -> ImpersonationAudit:
    row = ImpersonationAudit(
        operator_id=operator_id,
        company_id=company_id,
        effective_role=effective_role,
        effective_id=effective_id,
        action=action,
        detail=detail,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
