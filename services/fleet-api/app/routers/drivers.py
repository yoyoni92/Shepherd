from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import DriverCreate, DriverRead

router = APIRouter(prefix="/drivers", tags=["drivers"])


def _to_read(d) -> DriverRead:
    return DriverRead(
        driver_id=d.driver_id,
        full_name=d.full_name,
        phone_number=d.phone_number,
        license_number=d.license_number,
        license_valid_to=d.license_valid_to,
        status=d.status.value,
    )


@router.get(
    "",
    response_model=list[DriverRead],
    summary="List drivers (admin only)",
    description="Return all drivers in the system.",
)
def list_drivers(session: Db, caller: Caller) -> list[DriverRead]:
    assert_permitted(caller.role, Action.MANAGE_DRIVERS)
    return [_to_read(d) for d in repo.list_drivers(session)]


@router.get(
    "/{driver_id}",
    response_model=DriverRead,
    summary="Get driver by ID (admin only)",
)
def get_driver(driver_id: UUID, session: Db, caller: Caller) -> DriverRead:
    assert_permitted(caller.role, Action.MANAGE_DRIVERS)
    driver = repo.get_driver(session, driver_id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return _to_read(driver)


@router.post(
    "",
    response_model=DriverRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create driver (admin only)",
    description="Register a new driver. Phone number must be unique.",
)
def create_driver(body: DriverCreate, session: Db, caller: Caller) -> DriverRead:
    assert_permitted(caller.role, Action.MANAGE_DRIVERS)
    return _to_read(repo.create_driver(session, body.model_dump()))


@router.delete(
    "/{driver_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete driver (admin only)",
)
def delete_driver(driver_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_DRIVERS)
    if not repo.delete_driver(session, driver_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
