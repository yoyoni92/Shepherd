"""Data access layer - SQLAlchemy ORM, all Postgres writes go through here."""
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from shepherd_db.logic import next_maintenance
from shepherd_db.models import (
    Accident,
    AccidentAttachment,
    Event,
    KmUpdate,
    KpiDaily,
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


def delete_customer(session: Session, customer_id: UUID) -> bool:
    customer = session.get(Customer, customer_id)
    if customer is None:
        return False
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
    mt = vehicle.maintenance_type
    cycle = (mt.value if hasattr(mt, "value") else mt) if mt else "1_small_then_1_big"
    ct = care.maintenance_type
    care_type_str = ct.value if hasattr(ct, "value") else ct
    nm = next_maintenance(care_type_str, cycle, last_km=care.km_at_service)

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
# KPI daily rollup (read-only; populated by refresh_kpi_daily())
# ---------------------------------------------------------------------------

def list_kpi_daily(session: Session, limit: int = 2) -> list[KpiDaily]:
    stmt = select(KpiDaily).order_by(KpiDaily.snapshot_date.desc()).limit(limit)
    return list(session.execute(stmt).scalars())


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
