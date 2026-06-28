from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from shepherd_contracts.auth import Role

from app import repo
from app.auth import Action, assert_company, assert_permitted
from app.deps import Caller, Db
from app.schemas import (
    AccidentAttachmentOut,
    AccidentCreate,
    AccidentListItem,
    AccidentRead,
)

router = APIRouter(prefix="/accidents", tags=["accidents"])


def _to_list_item(a) -> AccidentListItem:
    return AccidentListItem(
        accident_id=a.accident_id,
        vehicle_id=a.vehicle_id,
        driver_id=a.driver_id,
        datetime=a.datetime,
        location=a.location,
        description=a.description,
        another_driver_licensing_plate=a.another_driver_licensing_plate,
        another_driver_phone_number=a.another_driver_phone_number,
        another_driver_id_number=a.another_driver_id_number,
        attachments=[
            AccidentAttachmentOut(
                attachment_id=att.attachment_id,
                category=att.category,
                file_url=att.file_url,
                uploaded_ts=att.uploaded_ts,
            )
            for att in a.attachments
        ],
    )


@router.get(
    "",
    response_model=list[AccidentListItem],
    summary="List all accidents",
    description="Returns all accidents ordered by datetime desc, with attachments. Admin only.",
)
def list_accidents(session: Db, caller: Caller) -> list[AccidentListItem]:
    assert_permitted(caller.role, Action.READ_ACCIDENTS)
    company_id = UUID(caller.company_id) if caller.company_id else None
    return [_to_list_item(a) for a in repo.list_accidents(session, company_id=company_id)]


@router.post(
    "",
    response_model=AccidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log accident",
    description=(
        "Record an accident with optional attachments. "
        "Admin can log for any vehicle and supply driver_id; "
        "driver only for their own vehicle. "
        "Emits an accident_logged event."
    ),
)
def log_accident(body: AccidentCreate, session: Db, caller: Caller) -> AccidentRead:
    vehicle = repo.get_vehicle_by_id(session, body.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    assert_company(vehicle, caller)

    if caller.role == Role.driver:
        is_owner = str(vehicle.driver_id) == caller.driver_id
    else:
        is_owner = True
    assert_permitted(caller.role, Action.LOG_ACCIDENT, is_owner=is_owner)

    if caller.role == Role.driver:
        driver_id = caller.driver_id
    else:
        driver_id = str(body.driver_id) if body.driver_id else None

    data = {
        "vehicle_id": body.vehicle_id,
        "driver_id": driver_id,
        "company_id": vehicle.company_id,
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
