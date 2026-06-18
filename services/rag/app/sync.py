from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shepherd_db.models import Accident, Report, Vehicle

from app.profile import build_profile


def _vehicle_doc(session: Session, v: Vehicle) -> tuple[str, dict]:
    accidents = session.scalars(
        select(Accident)
        .where(Accident.vehicle_id == v.vehicle_id)
        .order_by(Accident.datetime.desc())
        .limit(5)
    ).all()
    open_tickets = session.scalar(
        select(func.count(Report.report_id)).where(
            Report.vehicle_id == v.vehicle_id,
            Report.status == "unpaid",
        )
    ) or 0
    text = build_profile(
        vehicle_id=str(v.vehicle_id),
        plate=v.licensing_plate,
        driver_name=v.driver.full_name if v.driver else None,
        customer_name=v.customer.full_name if v.customer else None,
        insurance_valid_to=v.insurance_valid_to,
        license_valid_to=v.license_valid_to,
        last_maintenance_date=v.last_maintenance_date,
        last_maintenance_type=v.last_maintenance_type.value if v.last_maintenance_type else None,
        next_maintenance_km=v.next_maintenance_km,
        current_km=v.current_km,
        open_tickets=open_tickets,
        recent_accidents=[
            {"date": str(a.datetime.date()), "location": a.location or ""}
            for a in accidents
        ],
    )
    meta = {
        "vehicle_id": str(v.vehicle_id),
        "plate": v.licensing_plate,
        "driver_id": str(v.driver_id) if v.driver_id else "",
        "customer_id": str(v.customer_id) if v.customer_id else "",
    }
    return text, meta


def bulk(session: Session, collection) -> int:
    vehicles = list(session.scalars(select(Vehicle)))
    for v in vehicles:
        text, meta = _vehicle_doc(session, v)
        collection.upsert(documents=[text], metadatas=[meta], ids=[str(v.vehicle_id)])
    return len(vehicles)


def upsert(session: Session, collection, vehicle_id: str) -> None:
    v = session.get(Vehicle, vehicle_id)
    if not v:
        collection.delete(ids=[vehicle_id])
        return
    text, meta = _vehicle_doc(session, v)
    collection.upsert(documents=[text], metadatas=[meta], ids=[vehicle_id])
