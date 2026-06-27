"""Permission matrix + ownership enforcement for Fleet API."""
from enum import Enum

from fastapi import HTTPException, status

from shepherd_contracts.auth import CallerContext, Role


class Action(str, Enum):
    READ_VEHICLES = "read_vehicles"
    MANAGE_VEHICLES = "manage_vehicles"
    MANAGE_DRIVERS = "manage_drivers"
    MANAGE_CUSTOMERS = "manage_customers"
    KM_UPDATE = "km_update"
    LOG_ACCIDENT = "log_accident"
    READ_ACCIDENTS = "read_accidents"
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
    MANAGE_MAINTENANCE_TYPES = "manage_maintenance_types"
    MANAGE_BOT_USERS = "manage_bot_users"
    MANAGE_BOT_INVITES = "manage_bot_invites"
    MANAGE_APP_USERS = "manage_app_users"
    MANAGE_COMPANIES = "manage_companies"


# {action: {role: ownership_required}}
# None = forbidden; False = allowed regardless of ownership; True = only if is_owner
# company_admin mirrors admin for operational actions (F1's repo scoping enforces
# per-company isolation), incl. bot management scoped to its own company
# (MANAGE_BOT_USERS, MANAGE_BOT_INVITES - repo filters + assert_company isolate),
# but is denied system-wide management: MANAGE_APP_USERS, MANAGE_COMPANIES, EDIT_CONFIG.
_MATRIX: dict[Action, dict[Role, bool | None]] = {
    Action.READ_VEHICLES:    {Role.admin: False, Role.driver: True,  Role.customer: True, Role.company_admin: False},
    Action.MANAGE_VEHICLES:  {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.MANAGE_DRIVERS:   {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.MANAGE_CUSTOMERS: {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.KM_UPDATE:        {Role.admin: False, Role.driver: True,  Role.customer: None, Role.company_admin: False},
    Action.LOG_ACCIDENT:     {Role.admin: False, Role.driver: True,  Role.customer: None, Role.company_admin: False},
    Action.READ_ACCIDENTS:   {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.LOG_CARE:         {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.SUBMIT_DOCUMENT:  {Role.admin: False, Role.driver: True,  Role.customer: True, Role.company_admin: False},
    Action.WRITE_REPORTS:    {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.READ_REPORTS:     {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.READ_EVENTS:      {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.WRITE_EVENTS:     {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.READ_CONFIG:      {Role.admin: False, Role.driver: False,  Role.customer: False, Role.company_admin: False},
    Action.EDIT_CONFIG:      {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: None},
    Action.READ_KPI:         {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.MANAGE_ATTENDANCE: {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.MANAGE_MAINTENANCE_TYPES: {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.MANAGE_BOT_USERS:         {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.MANAGE_BOT_INVITES:       {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: False},
    Action.MANAGE_APP_USERS:         {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: None},
    Action.MANAGE_COMPANIES:         {Role.admin: False, Role.driver: None,  Role.customer: None, Role.company_admin: None},
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


def assert_company(row: object, caller: CallerContext) -> None:
    """Tenant isolation for by-PK reads/writes.

    When the caller is company-scoped (``caller.company_id`` set), a row whose
    ``company_id`` differs is treated as if it did not exist (404, not 403) so one
    tenant cannot probe another tenant's row existence. A caller with no company
    (system superadmin) passes through unfiltered.
    """
    if caller.company_id is None:
        return
    if row is None or str(getattr(row, "company_id", None)) != caller.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
