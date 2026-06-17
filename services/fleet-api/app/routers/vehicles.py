from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from shepherd_contracts.auth import Role

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import VehicleCreate, VehicleRead

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _to_read(v) -> VehicleRead:
    return VehicleRead(
        vehicle_id=v.vehicle_id,
        licensing_plate=v.licensing_plate,
        nickname=v.nickname,
        vendor=v.vendor,
        model=v.model,
        current_km=v.current_km,
        insurance_valid_to=v.insurance_valid_to,
        license_valid_to=v.license_valid_to,
        driver_id=v.driver_id,
        customer_id=v.customer_id,
        next_maintenance_km=v.next_maintenance_km,
        next_maintenance_type=v.next_maintenance_type.value if v.next_maintenance_type else None,
        last_maintenance_type=v.last_maintenance_type.value if v.last_maintenance_type else None,
        last_maintenance_km=v.last_maintenance_km,
        last_maintenance_date=v.last_maintenance_date,
        maintenance_type=v.maintenance_type.value if v.maintenance_type else None,
        allowed_driver=v.allowed_driver.value if v.allowed_driver else None,
    )


@router.get(
    "",
    response_model=list[VehicleRead],
    summary="List vehicles (ownership-filtered)",
    description="Admin sees all vehicles. Driver/customer see only their assigned vehicles.",
)
def list_vehicles(session: Db, caller: Caller) -> list[VehicleRead]:
    assert_permitted(caller.role, Action.READ_VEHICLES)
    if caller.role == Role.driver:
        vehicles = repo.list_vehicles(session, driver_id=UUID(caller.driver_id))
    elif caller.role == Role.customer:
        vehicles = repo.list_vehicles(session, customer_id=UUID(caller.customer_id))
    else:
        vehicles = repo.list_vehicles(session)
    return [_to_read(v) for v in vehicles]


@router.get(
    "/{plate}",
    response_model=VehicleRead,
    summary="Get vehicle by licensing plate",
    description="Returns vehicle details. Driver/customer must own the vehicle.",
)
def get_vehicle(plate: str, session: Db, caller: Caller) -> VehicleRead:
    vehicle = repo.get_vehicle_by_plate(session, plate)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    if caller.role == Role.driver:
        is_owner = str(vehicle.driver_id) == caller.driver_id
    elif caller.role == Role.customer:
        is_owner = str(vehicle.customer_id) == caller.customer_id
    else:
        is_owner = True
    assert_permitted(caller.role, Action.READ_VEHICLES, is_owner=is_owner)

    return _to_read(vehicle)


@router.post(
    "",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create vehicle (admin only)",
    description="Add a new vehicle to the fleet. Plate must be unique.",
)
def create_vehicle(body: VehicleCreate, session: Db, caller: Caller) -> VehicleRead:
    assert_permitted(caller.role, Action.MANAGE_VEHICLES)

    if repo.get_vehicle_by_plate(session, body.licensing_plate):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plate already exists")

    vehicle = repo.create_vehicle(session, body.model_dump())
    return _to_read(vehicle)


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete vehicle (admin only)",
    description="Permanently remove a vehicle from the fleet.",
)
def delete_vehicle(vehicle_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_VEHICLES)
    if not repo.delete_vehicle(session, vehicle_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
