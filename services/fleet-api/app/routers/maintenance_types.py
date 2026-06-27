from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_company, assert_permitted
from app.deps import Caller, Db
from app.schemas import MaintenanceTypeCreate, MaintenanceTypeRead, MaintenanceTypeUpdate

router = APIRouter(prefix="/maintenance-types", tags=["maintenance-types"])

_ACTION = Action.MANAGE_MAINTENANCE_TYPES


def _company(caller) -> UUID | None:
    return UUID(caller.company_id) if caller.company_id else None


def _to_read(m) -> MaintenanceTypeRead:
    return MaintenanceTypeRead(
        id=m.id,
        name=m.name,
        description=m.description,
        interval_km=m.interval_km,
        steps=m.steps,
    )


@router.get("", response_model=list[MaintenanceTypeRead], summary="List maintenance types (admin only)")
def list_types(session: Db, caller: Caller) -> list[MaintenanceTypeRead]:
    assert_permitted(caller.role, _ACTION)
    return [_to_read(m) for m in repo.list_maintenance_types(session, company_id=_company(caller))]


@router.post("", response_model=MaintenanceTypeRead, status_code=201, summary="Create maintenance type (admin only)")
def create_type(body: MaintenanceTypeCreate, session: Db, caller: Caller) -> MaintenanceTypeRead:
    assert_permitted(caller.role, _ACTION)
    data = body.model_dump()
    data["company_id"] = caller.company_id
    return _to_read(repo.create_maintenance_type(session, data))


@router.patch("/{type_id}", response_model=MaintenanceTypeRead, summary="Update maintenance type (admin only)")
def update_type(type_id: UUID, body: MaintenanceTypeUpdate, session: Db, caller: Caller) -> MaintenanceTypeRead:
    assert_permitted(caller.role, _ACTION)
    existing = repo.get_maintenance_type(session, type_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance type not found")
    assert_company(existing, caller)
    mtype = repo.update_maintenance_type(session, type_id, body.model_dump(exclude_unset=True))
    return _to_read(mtype)


@router.delete(
    "/{type_id}",
    status_code=204,
    summary="Delete maintenance type (admin only)",
    description="Blocked with 409 if any vehicle still uses this type.",
)
def delete_type(type_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, _ACTION)
    existing = repo.get_maintenance_type(session, type_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance type not found")
    assert_company(existing, caller)
    in_use = repo.count_vehicles_for_maintenance_type(session, type_id)
    if in_use > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{in_use} רכבים משתמשים בסוג טיפול זה",
        )
    repo.delete_maintenance_type(session, type_id)
