"""System-admin (Telegram operator) endpoints.

Gated inline: a company-less ``admin`` caller (``role == admin`` and ``company_id is
None``) is the system admin. There is no ``is_system_admin`` on CallerContext, so this
shape is the contract; anything else is 403.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from shepherd_contracts.auth import Role

from app import repo
from app.deps import Caller, Db
from app.routers.app_users import _to_read as _app_user_read
from app.routers.drivers import _to_read as _driver_read
from app.schemas import (
    AppUserRead,
    CompanyRead,
    DriverRead,
    ImpersonationAuditCreate,
    SystemOverview,
    SystemOverviewItem,
)

router = APIRouter(prefix="/sysadmin", tags=["sysadmin"])


def _assert_system_admin(caller) -> None:
    if not (caller.role == Role.admin and caller.company_id is None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _company_read(c) -> CompanyRead:
    return CompanyRead(
        company_id=c.company_id, name=c.name, is_active=c.is_active, created_at=c.created_at
    )


@router.get("/overview", response_model=SystemOverview, summary="Cross-company overview")
def overview(session: Db, caller: Caller) -> SystemOverview:
    _assert_system_admin(caller)
    return SystemOverview(
        companies=[SystemOverviewItem(**item) for item in repo.system_overview(session)]
    )


@router.get(
    "/companies",
    response_model=list[CompanyRead],
    summary="Real companies for the Customer-Live picker (excludes internal)",
)
def companies(session: Db, caller: Caller) -> list[CompanyRead]:
    _assert_system_admin(caller)
    return [_company_read(c) for c in repo.list_companies(session)]


@router.get(
    "/companies/{company_id}/admins",
    response_model=list[AppUserRead],
    summary="A company's company_admin app users",
)
def company_admins(company_id: UUID, session: Db, caller: Caller) -> list[AppUserRead]:
    _assert_system_admin(caller)
    return [_app_user_read(u) for u in repo.list_company_admins(session, company_id)]


@router.get(
    "/companies/{company_id}/drivers",
    response_model=list[DriverRead],
    summary="A company's drivers",
)
def company_drivers(company_id: UUID, session: Db, caller: Caller) -> list[DriverRead]:
    _assert_system_admin(caller)
    return [_driver_read(d) for d in repo.list_drivers(session, company_id=company_id)]


@router.post(
    "/impersonation-audit",
    status_code=status.HTTP_201_CREATED,
    summary="Record a Customer-Live impersonation action (start/stop/write)",
)
def write_impersonation_audit(
    body: ImpersonationAuditCreate, session: Db, caller: Caller
) -> dict:
    _assert_system_admin(caller)
    # The operator is carried in CallerContext.impersonator while acting as someone else.
    if caller.impersonator is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="operator (impersonator) required"
        )
    repo.write_impersonation_audit(
        session,
        operator_id=UUID(caller.impersonator),
        company_id=body.company_id,
        effective_role=body.effective_role,
        effective_id=body.effective_id,
        action=body.action,
        detail=body.detail,
    )
    return {"status": "ok"}
