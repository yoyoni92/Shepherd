"""Permission matrix + ownership enforcement for Fleet API."""
from enum import Enum

from fastapi import HTTPException, status

from shepherd_contracts.auth import Role


class Action(str, Enum):
    READ_VEHICLES = "read_vehicles"
    MANAGE_VEHICLES = "manage_vehicles"
    MANAGE_DRIVERS = "manage_drivers"
    MANAGE_CUSTOMERS = "manage_customers"
    KM_UPDATE = "km_update"
    LOG_ACCIDENT = "log_accident"
    LOG_CARE = "log_care"
    SUBMIT_DOCUMENT = "submit_document"
    WRITE_REPORTS = "write_reports"
    READ_REPORTS = "read_reports"
    READ_EVENTS = "read_events"
    WRITE_EVENTS = "write_events"
    READ_CONFIG = "read_config"
    EDIT_CONFIG = "edit_config"
    READ_KPI = "read_kpi"
    MANAGE_ATTENDANCE = "manage_attendance"


# {action: {role: ownership_required}}
# None = forbidden; False = allowed regardless of ownership; True = only if is_owner
_MATRIX: dict[Action, dict[Role, bool | None]] = {
    Action.READ_VEHICLES:    {Role.admin: False, Role.driver: True,  Role.customer: True},
    Action.MANAGE_VEHICLES:  {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.MANAGE_DRIVERS:   {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.MANAGE_CUSTOMERS: {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.KM_UPDATE:        {Role.admin: False, Role.driver: True,  Role.customer: None},
    Action.LOG_ACCIDENT:     {Role.admin: False, Role.driver: True,  Role.customer: None},
    Action.LOG_CARE:         {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.SUBMIT_DOCUMENT:  {Role.admin: False, Role.driver: True,  Role.customer: True},
    Action.WRITE_REPORTS:    {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.READ_REPORTS:     {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.READ_EVENTS:      {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.WRITE_EVENTS:     {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.READ_CONFIG:      {Role.admin: False, Role.driver: False,  Role.customer: False},
    Action.EDIT_CONFIG:      {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.READ_KPI:         {Role.admin: False, Role.driver: None,  Role.customer: None},
    Action.MANAGE_ATTENDANCE: {Role.admin: False, Role.driver: None,  Role.customer: None},
}


def can(role: Role, action: Action, *, is_owner: bool = True) -> bool:
    cell = _MATRIX[action].get(role)
    if cell is None:
        return False
    if cell is True:
        return is_owner
    return True


def assert_permitted(role: Role, action: Action, *, is_owner: bool = True) -> None:
    if not can(role, action, is_owner=is_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
