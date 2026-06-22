from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db, verify_internal_token
from app.schemas import (
    AttendanceDayRead,
    AttendancePatch,
    AttendanceRecordRead,
    ClockRequest,
    ClockResponse,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])

_IL_TZ = ZoneInfo("Asia/Jerusalem")


def _to_read(r) -> AttendanceRecordRead:
    return AttendanceRecordRead(
        driver_id=r.driver_id,
        work_date=r.work_date,
        clock_in=r.clock_in,
        clock_out=r.clock_out,
        status=r.status.value,
    )


def _window(session) -> tuple[bool, str, str]:
    """Read the attendance reporting window from system_config (feature flag off by default)."""
    def val(key):
        c = repo.get_config_key(session, key)
        return c.config_value if c else None

    enabled = val("attendance_window_enabled")
    enabled = enabled is True or enabled == "true"
    start = str(val("attendance_window_start") or "00:00")
    end = str(val("attendance_window_end") or "23:59")
    return enabled, start, end


def _outside_window(now: datetime, start: str, end: str) -> bool:
    cur = now.hour * 60 + now.minute
    sh, sm = (int(x) for x in start.split(":"))
    eh, em = (int(x) for x in end.split(":"))
    return cur < sh * 60 + sm or cur > eh * 60 + em


# --- Bot self-service clock in/out (internal service only; window enforced here) ---


@router.post(
    "/clock-in",
    response_model=ClockResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Driver clock-in (internal; idempotent, window-enforced)",
)
def clock_in(body: ClockRequest, session: Db) -> ClockResponse:
    now = datetime.now(_IL_TZ)
    enabled, start, end = _window(session)
    if enabled and _outside_window(now, start, end):
        return ClockResponse(result="blocked", window_start=start, window_end=end)
    result, t = repo.attendance_clock_in(session, body.driver_id, now.strftime("%H:%M"), now.date())
    return ClockResponse(result=result, time=t, window_start=start, window_end=end)


@router.post(
    "/clock-out",
    response_model=ClockResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Driver clock-out (internal; window-enforced)",
)
def clock_out(body: ClockRequest, session: Db) -> ClockResponse:
    now = datetime.now(_IL_TZ)
    enabled, start, end = _window(session)
    if enabled and _outside_window(now, start, end):
        return ClockResponse(result="blocked", window_start=start, window_end=end)
    result, t, hours = repo.attendance_clock_out(session, body.driver_id, now.strftime("%H:%M"), now.date())
    return ClockResponse(result=result, time=t, hours=hours, window_start=start, window_end=end)


# --- Reads ---


@router.get(
    "/today",
    response_model=list[AttendanceDayRead],
    summary="Today's attendance with driver names (admin only)",
)
def list_today(session: Db, caller: Caller) -> list[AttendanceDayRead]:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    today = datetime.now(_IL_TZ).date()
    return [
        AttendanceDayRead(
            driver_id=r.driver_id,
            driver_name=name,
            clock_in=r.clock_in,
            clock_out=r.clock_out,
            status=r.status.value,
        )
        for r, name in repo.list_attendance_day(session, today)
    ]


@router.get(
    "/{month}",
    response_model=list[AttendanceRecordRead],
    summary="List attendance for a month (admin only)",
    description="month is YYYY-MM. Optional driver_id filters to one driver.",
)
def list_month(
    month: str, session: Db, caller: Caller, driver_id: UUID | None = None
) -> list[AttendanceRecordRead]:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    try:
        d = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be YYYY-MM")
    return [_to_read(r) for r in repo.list_attendance_month(session, d.year, d.month, driver_id)]


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
