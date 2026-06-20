from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import AttendancePatch, AttendanceRecordRead

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _to_read(r) -> AttendanceRecordRead:
    return AttendanceRecordRead(
        driver_id=r.driver_id,
        work_date=r.work_date,
        clock_in=r.clock_in,
        clock_out=r.clock_out,
        status=r.status.value,
    )


@router.get(
    "/{month}",
    response_model=list[AttendanceRecordRead],
    summary="List attendance for a month (admin only)",
    description="month is YYYY-MM. Returns stored records across all drivers for that month.",
)
def list_month(month: str, session: Db, caller: Caller) -> list[AttendanceRecordRead]:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    try:
        d = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be YYYY-MM")
    return [_to_read(r) for r in repo.list_attendance_month(session, d.year, d.month)]


@router.patch(
    "/{driver_id}/{day}",
    response_model=AttendanceRecordRead,
    summary="Upsert one attendance day (admin only)",
    description="day is YYYY-MM-DD. Creates or updates the (driver, date) record.",
)
def upsert_day(driver_id: UUID, day: str, body: AttendancePatch, session: Db, caller: Caller) -> AttendanceRecordRead:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    try:
        work_date = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="day must be YYYY-MM-DD")
    rec = repo.upsert_attendance(session, driver_id, work_date, body.model_dump())
    return _to_read(rec)
