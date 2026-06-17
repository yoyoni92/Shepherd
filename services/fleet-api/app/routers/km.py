from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from shepherd_contracts.auth import Role

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import KmUpdateRequest, KmUpdateResponse

router = APIRouter(prefix="/km", tags=["km"])


@router.post(
    "",
    response_model=KmUpdateResponse,
    summary="Report KM update",
    description=(
        "Update vehicle odometer. Admin can update any vehicle. "
        "Driver can only update their own assigned vehicle. "
        "Emits a maintenance_due event when km nears next_maintenance_km."
    ),
)
def update_km(body: KmUpdateRequest, session: Db, caller: Caller) -> KmUpdateResponse:
    vehicle = repo.get_vehicle_by_id(session, body.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    if caller.role == Role.driver:
        is_owner = str(vehicle.driver_id) == caller.driver_id
    else:
        is_owner = True
    assert_permitted(caller.role, Action.KM_UPDATE, is_owner=is_owner)

    driver_id = UUID(caller.driver_id) if caller.role == Role.driver and caller.driver_id else None
    km_id, triggered = repo.update_km(session, body.vehicle_id, body.km, driver_id=driver_id, source=body.source)
    return KmUpdateResponse(km_update_id=km_id, maintenance_event_created=triggered)
