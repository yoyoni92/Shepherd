from datetime import date

from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_company, assert_permitted
from app.deps import Caller, Db
from app.schemas import VehicleCareCreate, VehicleCareRead

router = APIRouter(prefix="/vehicle_care", tags=["care"])


@router.post(
    "",
    response_model=VehicleCareRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log maintenance service (admin only)",
    description=(
        "Record a completed maintenance service. Updates vehicle's last/next maintenance fields "
        "using the vehicle's configured maintenance cycle."
    ),
)
def log_care(body: VehicleCareCreate, session: Db, caller: Caller) -> VehicleCareRead:
    assert_permitted(caller.role, Action.LOG_CARE)

    vehicle = repo.get_vehicle_by_id(session, body.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    assert_company(vehicle, caller)

    # A service reading is a live odometer reading: it may not be below current_km
    # (that would downgrade the odometer) and may not be in the future. create_care
    # advances current_km to it.
    if vehicle.current_km is not None and body.km_at_service < vehicle.current_km:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="km_below_current"
        )
    if body.service_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_date cannot be in the future",
        )

    care = repo.create_care(session, body.model_dump())
    return VehicleCareRead(
        care_id=care.care_id,
        vehicle_id=care.vehicle_id,
        next_maintenance_km=care._next_km,  # type: ignore[attr-defined]
        next_maintenance_date=care._next_date,  # type: ignore[attr-defined]
        next_maintenance_type=care._next_type,  # type: ignore[attr-defined]
    )
