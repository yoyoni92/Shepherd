from uuid import UUID

from fastapi import APIRouter

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import ReportCreate, ReportRead

router = APIRouter(prefix="/reports", tags=["reports"])


def _company(caller) -> UUID | None:
    return UUID(caller.company_id) if caller.company_id else None


def _to_read(r) -> ReportRead:
    return ReportRead(
        report_id=r.report_id,
        vehicle_id=r.vehicle_id,
        ticket_type=r.ticket_type.value,
        status=r.status.value,
        amount=r.amount,
    )


@router.get(
    "",
    response_model=list[ReportRead],
    summary="List reports (admin only)",
    description="Return all traffic/parking ticket reports.",
)
def list_reports(session: Db, caller: Caller) -> list[ReportRead]:
    assert_permitted(caller.role, Action.READ_REPORTS)
    return [_to_read(r) for r in repo.list_reports(session, company_id=_company(caller))]


@router.post(
    "",
    response_model=ReportRead,
    status_code=201,
    summary="Create report (admin only)",
    description="Record a traffic or parking ticket.",
)
def create_report(body: ReportCreate, session: Db, caller: Caller) -> ReportRead:
    assert_permitted(caller.role, Action.WRITE_REPORTS)
    data = body.model_dump()
    data["company_id"] = caller.company_id
    return _to_read(repo.create_report(session, data))
