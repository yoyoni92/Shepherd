"""Data access layer - SQLAlchemy ORM, all Postgres writes go through here."""
import json
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from shepherd_db.logic import next_maintenance
from shepherd_db.models import (
    Accident,
    AccidentAttachment,
    AttendanceRecord,
    BotInviteToken,
    BotUser,
    Event,
    KmUpdate,
    KpiDaily,
    MaintenanceType,
    Report,
    SystemConfig,
    Vehicle,
    VehicleCare,
    Driver,
    Customer,
)


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

def get_vehicle_by_plate(session: Session, plate: str) -> Vehicle | None:
    return session.execute(
        select(Vehicle).where(Vehicle.licensing_plate == plate)
    ).scalar_one_or_none()


def get_vehicle_by_id(session: Session, vehicle_id: UUID) -> Vehicle | None:
    return session.get(Vehicle, vehicle_id)


def list_vehicles(
    session: Session,
    *,
    driver_id: UUID | None = None,
    customer_id: UUID | None = None,
) -> list[Vehicle]:
    stmt = select(Vehicle)
    if driver_id is not None:
        stmt = stmt.where(Vehicle.driver_id == driver_id)
    elif customer_id is not None:
        stmt = stmt.where(Vehicle.customer_id == customer_id)
    return list(session.execute(stmt).scalars())


def create_vehicle(session: Session, data: dict) -> Vehicle:
    vehicle = Vehicle(**data)
    session.add(vehicle)
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


def list_drivers(session: Session) -> list[Driver]:
    return list(session.execute(select(Driver)).scalars())


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

def list_customers(session: Session) -> list[Customer]:
    return list(session.execute(select(Customer)).scalars())


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

def get_maintenance_buffer(session: Session) -> int:
    cfg = session.get(SystemConfig, "maintenance_km_buffer")
    return int(cfg.config_value) if cfg is not None else 500


def update_km(
    session: Session,
    vehicle_id: UUID,
    km: int,
    *,
    driver_id: UUID | None,
    source: str,
) -> tuple[UUID, bool]:
    """Insert km_update row, update vehicle.current_km. Returns (km_update_id, maintenance_triggered)."""
    km_update = KmUpdate(vehicle_id=vehicle_id, km=km, driver_id=driver_id, source=source)
    session.add(km_update)
    session.flush()  # get km_update_id before checking trigger

    vehicle = session.get(Vehicle, vehicle_id)
    vehicle.current_km = km

    triggered = False
    if vehicle.next_maintenance_km is not None:
        buffer = get_maintenance_buffer(session)
        if km >= vehicle.next_maintenance_km - buffer:
            event = Event(
                vehicle_id=vehicle_id,
                event_type="maintenance_due",
                severity="warning",
                message="Maintenance due soon",
                source_type="km_updates",
                source_id=km_update.km_update_id,
            )
            session.add(event)
            triggered = True

    session.commit()
    return km_update.km_update_id, triggered


# ---------------------------------------------------------------------------
# Accidents
# ---------------------------------------------------------------------------

def create_accident(session: Session, data: dict, attachments: list[dict]) -> UUID:
    accident = Accident(**data)
    session.add(accident)
    session.flush()

    for att in attachments:
        session.add(AccidentAttachment(accident_id=accident.accident_id, **att))

    session.add(Event(
        vehicle_id=accident.vehicle_id,
        event_type="accident_logged",
        severity="critical",
        message="Accident logged",
        source_type="accidents",
        source_id=accident.accident_id,
    ))
    session.commit()
    return accident.accident_id


# ---------------------------------------------------------------------------
# Vehicle care
# ---------------------------------------------------------------------------

def create_care(session: Session, data: dict) -> VehicleCare:
    care = VehicleCare(**data)
    session.add(care)
    session.flush()

    vehicle = session.get(Vehicle, care.vehicle_id)
    # Cycle is data-driven: read the assigned maintenance type's steps + interval.
    mtype = vehicle.maintenance_type
    steps = mtype.steps if mtype else [care.maintenance_type]
    interval_km = mtype.interval_km if mtype else 10_000
    nm = next_maintenance(care.maintenance_type, steps, last_km=care.km_at_service, interval_km=interval_km)

    vehicle.last_maintenance_date = care.service_date
    vehicle.last_maintenance_type = care.maintenance_type
    vehicle.last_maintenance_km = care.km_at_service
    vehicle.next_maintenance_km = nm["next_km"]
    vehicle.next_maintenance_type = nm["next_type"]

    session.commit()
    session.refresh(care)
    # attach computed next values for the response
    care._next_km = nm["next_km"]
    care._next_type = nm["next_type"]
    return care


# ---------------------------------------------------------------------------
# Documents extracted
# ---------------------------------------------------------------------------

def process_extracted_doc(session: Session, payload: dict) -> tuple[str, UUID | None, UUID | None]:
    """Apply extracted document to DB. Returns (status, event_id, report_id)."""
    plate = payload["licensing_plate"]
    vehicle = get_vehicle_by_plate(session, plate)

    if vehicle is None:
        event = Event(
            event_type="ticket_received",
            severity="warning",
            message="Extracted doc plate not found in fleet",
            payload_json={"plate": plate},
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
        ))
        report_id = report.report_id

    session.commit()
    return "updated", None, report_id


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def list_reports(session: Session) -> list[Report]:
    return list(session.execute(select(Report).order_by(Report.created_ts.desc())).scalars())


def create_report(session: Session, data: dict) -> Report:
    report = Report(**data)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def list_events(session: Session, vehicle_id: UUID | None = None) -> list[Event]:
    stmt = select(Event).order_by(Event.triggered_ts.desc())
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

def get_all_config(session: Session) -> list[SystemConfig]:
    return list(session.execute(select(SystemConfig).order_by(SystemConfig.config_key)).scalars())


def get_config_key(session: Session, key: str) -> SystemConfig | None:
    return session.get(SystemConfig, key)


# ---------------------------------------------------------------------------
# Maintenance types (admin-managed catalog)
# ---------------------------------------------------------------------------

def list_maintenance_types(session: Session) -> list[MaintenanceType]:
    return list(session.execute(select(MaintenanceType).order_by(MaintenanceType.name)).scalars())


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

def list_attendance_month(session: Session, year: int, month: int) -> list[AttendanceRecord]:
    from calendar import monthrange
    from datetime import date

    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    stmt = select(AttendanceRecord).where(AttendanceRecord.work_date.between(start, end))
    return list(session.execute(stmt).scalars())


def upsert_attendance(session: Session, driver_id: UUID, work_date, data: dict) -> AttendanceRecord:
    rec = session.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.driver_id == driver_id,
            AttendanceRecord.work_date == work_date,
        )
    ).scalar_one_or_none()
    if rec is None:
        rec = AttendanceRecord(driver_id=driver_id, work_date=work_date, **data)
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

def list_kpi_daily(session: Session, limit: int = 2) -> list[KpiDaily]:
    stmt = select(KpiDaily).order_by(KpiDaily.snapshot_date.desc()).limit(limit)
    return list(session.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# Bot users and invite tokens
# ---------------------------------------------------------------------------

def get_bot_user_by_chat_id(session: Session, chat_id: int) -> BotUser | None:
    return session.execute(
        select(BotUser).where(BotUser.telegram_chat_id == chat_id)
    ).scalar_one_or_none()


def list_bot_users(session: Session, role: str | None = None) -> list[BotUser]:
    stmt = select(BotUser)
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


def create_bot_invite(
    session: Session, driver_id: UUID | None, token: str, role: str = "driver"
) -> BotInviteToken:
    from datetime import datetime, timezone
    # Only a driver can have a prior token to invalidate; admin invites have no driver.
    if driver_id is not None:
        session.execute(
            update(BotInviteToken)
            .where(BotInviteToken.driver_id == driver_id, BotInviteToken.used_at.is_(None))
            .values(expires_at=datetime.now(timezone.utc))
        )
    invite = BotInviteToken(token=token, driver_id=driver_id, role=role)
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return invite


def claim_bot_invite(session: Session, token: str, telegram_chat_id: int) -> BotUser | None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    invite = session.get(BotInviteToken, token)
    if invite is None or invite.used_at is not None or invite.expires_at < now:
        return None
    invite.used_at = now
    existing = session.execute(
        select(BotUser).where(BotUser.telegram_chat_id == telegram_chat_id)
    ).scalar_one_or_none()
    if existing is not None:
        session.delete(existing)
        session.flush()
    user = BotUser(telegram_chat_id=telegram_chat_id, role=invite.role, driver_id=invite.driver_id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def list_pending_bot_invites(session: Session) -> list[BotInviteToken]:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return list(
        session.execute(
            select(BotInviteToken).where(
                BotInviteToken.used_at.is_(None),
                BotInviteToken.expires_at > now,
            )
        ).scalars()
    )


def revoke_bot_invite(session: Session, token: str) -> str:
    from datetime import datetime, timezone
    invite = session.get(BotInviteToken, token)
    if invite is None:
        return "not_found"
    if invite.used_at is not None:
        return "already_used"
    invite.expires_at = datetime.now(timezone.utc)
    session.commit()
    return "ok"


def set_config(session: Session, key: str, value: object) -> SystemConfig:
    from datetime import datetime, timezone
    cfg = session.get(SystemConfig, key)
    if cfg is None:
        cfg = SystemConfig(config_key=key, config_value=value, updated_ts=datetime.now(timezone.utc))
        session.add(cfg)
    else:
        cfg.config_value = value
        cfg.updated_ts = datetime.now(timezone.utc)
    session.commit()
    session.refresh(cfg)
    return cfg
