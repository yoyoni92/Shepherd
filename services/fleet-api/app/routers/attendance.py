from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status

from app import repo
from app.auth import Action, assert_company, assert_permitted
from app.deps import Caller, Db, verify_internal_token
from app.schemas import (
    AttendanceDayRead,
    AttendancePatch,
    AttendanceRecordRead,
    AttendanceSettings,
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


def _window(session, company_id) -> tuple[bool, str, str]:
    """Read the attendance reporting window from system_config (feature flag off by default)."""
    def val(key):
        c = repo.get_config_key(session, key, company_id)
        return c.config_value if c else None

    enabled = val("attendance_window_enabled")
    enabled = enabled is True or enabled == "true"
    start = str(val("attendance_window_start") or "00:00")
    end = str(val("attendance_window_end") or "23:59")
    return enabled, start, end


def _work_rules(session, company_id) -> tuple[list[int], bool, bool]:
    """Read the company's working-day rules from system_config (sensible defaults)."""
    def val(key, default):
        c = repo.get_config_key(session, key, company_id)
        return c.config_value if c else default

    work_days = val("attendance_work_days", [0, 1, 2, 3, 4])
    if not isinstance(work_days, list):
        work_days = [0, 1, 2, 3, 4]
    chag = val("attendance_chag_working", False)
    erev = val("attendance_erev_chag_working", True)
    return [int(d) for d in work_days], bool(chag), bool(erev)


def _outside_window(now: datetime, start: str, end: str) -> bool:
    cur = now.hour * 60 + now.minute
    sh, sm = (int(x) for x in start.split(":"))
    eh, em = (int(x) for x in end.split(":"))
    return cur < sh * 60 + sm or cur > eh * 60 + em


def _assert_attendance_enabled(session, caller) -> None:
    """403 when the caller's company has the attendance feature flag off.

    A caller with no company (system superadmin) is cross-company and passes through.
    """
    if caller.company_id and not repo.company_feature_enabled(
        session, UUID(caller.company_id), "attendance"
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="attendance disabled")


# --- Bot self-service clock in/out (internal service only; window enforced here) ---


@router.post(
    "/clock-in",
    response_model=ClockResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Driver clock-in (internal; idempotent, window-enforced)",
)
def clock_in(body: ClockRequest, session: Db) -> ClockResponse:
    now = datetime.now(_IL_TZ)
    driver = repo.get_driver(session, body.driver_id)
    company_id = driver.company_id if driver else None
    # Attendance is gated per company; signal "disabled" in the typed response so the
    # bot doesn't need to special-case an HTTP error here.
    if company_id is None or not repo.company_feature_enabled(session, company_id, "attendance"):
        return ClockResponse(result="disabled")
    enabled, start, end = _window(session, company_id)
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
    driver = repo.get_driver(session, body.driver_id)
    company_id = driver.company_id if driver else None
    if company_id is None or not repo.company_feature_enabled(session, company_id, "attendance"):
        return ClockResponse(result="disabled")
    enabled, start, end = _window(session, company_id)
    if enabled and _outside_window(now, start, end):
        return ClockResponse(result="blocked", window_start=start, window_end=end)
    result, t, hours = repo.attendance_clock_out(
        session, body.driver_id, now.strftime("%H:%M"), now.date()
    )
    return ClockResponse(result=result, time=t, hours=hours, window_start=start, window_end=end)


# --- Settings (company-scoped; managed by the company admin in the Attendance tab) ---


@router.get(
    "/settings",
    response_model=AttendanceSettings,
    summary="Read the attendance clock-in window for the caller's company",
)
def get_settings(session: Db, caller: Caller) -> AttendanceSettings:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    if not caller.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="company context required"
        )
    cid = UUID(caller.company_id)
    enabled, start, end = _window(session, cid)
    work_days, chag, erev = _work_rules(session, cid)
    return AttendanceSettings(
        enabled=enabled, start=start, end=end,
        work_days=work_days, chag_working=chag, erev_chag_working=erev,
    )


@router.put(
    "/settings",
    response_model=AttendanceSettings,
    summary="Update the attendance clock-in window for the caller's company",
)
def put_settings(body: AttendanceSettings, session: Db, caller: Caller) -> AttendanceSettings:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    if not caller.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="company context required"
        )
    cid = UUID(caller.company_id)
    repo.set_config(session, "attendance_window_enabled", body.enabled, cid)
    repo.set_config(session, "attendance_window_start", body.start, cid)
    repo.set_config(session, "attendance_window_end", body.end, cid)
    repo.set_config(session, "attendance_work_days", body.work_days, cid)
    repo.set_config(session, "attendance_chag_working", body.chag_working, cid)
    repo.set_config(session, "attendance_erev_chag_working", body.erev_chag_working, cid)
    return body


# --- Reads ---


@router.get(
    "/today",
    response_model=list[AttendanceDayRead],
    summary="Today's attendance with driver names (admin only)",
)
def list_today(session: Db, caller: Caller) -> list[AttendanceDayRead]:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    _assert_attendance_enabled(session, caller)
    today = datetime.now(_IL_TZ).date()
    company_id = UUID(caller.company_id) if caller.company_id else None
    return [
        AttendanceDayRead(
            driver_id=r.driver_id,
            driver_name=name,
            clock_in=r.clock_in,
            clock_out=r.clock_out,
            status=r.status.value,
        )
        for r, name in repo.list_attendance_day(session, today, company_id=company_id)
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
    _assert_attendance_enabled(session, caller)
    try:
        d = datetime.strptime(month, "%Y-%m")
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="month must be YYYY-MM"
        ) from err
    company_id = UUID(caller.company_id) if caller.company_id else None
    return [
        _to_read(r)
        for r in repo.list_attendance_month(
            session, d.year, d.month, driver_id, company_id=company_id
        )
    ]


@router.patch(
    "/{driver_id}/{day}",
    response_model=AttendanceRecordRead,
    summary="Upsert one attendance day (admin only)",
    description="day is YYYY-MM-DD. Creates or updates the (driver, date) record.",
)
def upsert_day(
    driver_id: UUID, day: str, body: AttendancePatch, session: Db, caller: Caller
) -> AttendanceRecordRead:
    assert_permitted(caller.role, Action.MANAGE_ATTENDANCE)
    try:
        work_date = date.fromisoformat(day)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="day must be YYYY-MM-DD"
        ) from err
    # The record inherits the driver's company, so the driver must be in the caller's company.
    # Tenant isolation (404) is asserted before the feature gate so cross-tenant probes can't
    # learn another company's attendance state.
    driver = repo.get_driver(session, driver_id)
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    assert_company(driver, caller)
    _assert_attendance_enabled(session, caller)
    rec = repo.upsert_attendance(session, driver_id, work_date, body.model_dump())
    return _to_read(rec)
