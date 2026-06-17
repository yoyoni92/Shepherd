from fastapi import APIRouter, HTTPException, status
from shepherd_contracts.auth import Role

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import AccidentCreate, AccidentRead

router = APIRouter(prefix="/accidents", tags=["accidents"])


@router.post(
    "",
    response_model=AccidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log accident",
    description=(
        "Record an accident with optional attachments. "
        "Admin can log for any vehicle; driver only for their own vehicle. "
        "Emits an accident_logged event."
    ),
)
def log_accident(body: AccidentCreate, session: Db, caller: Caller) -> AccidentRead:
    vehicle = repo.get_vehicle_by_id(session, body.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    if caller.role == Role.driver:
        is_owner = str(vehicle.driver_id) == caller.driver_id
    else:
        is_owner = True
    assert_permitted(caller.role, Action.LOG_ACCIDENT, is_owner=is_owner)

    driver_id = caller.driver_id if caller.role == Role.driver else None
    data = {
        "vehicle_id": body.vehicle_id,
        "driver_id": driver_id,
        "datetime": body.datetime,
        "location": body.location,
        "description": body.description,
        "another_driver_licensing_plate": body.another_driver_licensing_plate,
        "another_driver_phone_number": body.another_driver_phone_number,
        "another_driver_id_number": body.another_driver_id_number,
    }
    attachments = [a.model_dump() for a in body.attachments]
    accident_id = repo.create_accident(session, data, attachments)
    return AccidentRead(accident_id=accident_id)
