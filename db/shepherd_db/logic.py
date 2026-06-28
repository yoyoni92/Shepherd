"""Maintenance cycle helper logic for Shepherd fleet management.

A maintenance type is an ordered list of unique step labels plus an optional km
interval and/or an optional month interval. Services advance through the steps in
order, wrapping back to the first after the last. The next service is due by km, by
date, or whichever comes first.
"""

import calendar
from datetime import date


def _add_months(d: date, months: int) -> date:
    """Shift d forward by `months`, clamping the day to the target month's end."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_maintenance(
    last_step,
    steps,
    *,
    last_km=0,
    interval_km=None,
    last_date=None,
    interval_months=None,
):
    """Determine the next service step, km threshold, and due date from a cycle.

    Args:
        last_step: Label of the last service performed, or None for the first service.
        steps: Ordered list of unique step labels for the vehicle's maintenance type.
        last_km: Odometer at the last service.
        interval_km: Km between services, or None for a time-only cycle.
        last_date: Date of the last service, or None when never serviced.
        interval_months: Months between services, or None for a km-only cycle.

    Returns:
        dict: {"next_type": str, "next_km": int | None, "next_date": date | None}
    """
    if not steps:
        raise ValueError("steps must be a non-empty list")

    if last_step is None or last_step not in steps:
        next_step = steps[0]
    else:
        next_step = steps[(steps.index(last_step) + 1) % len(steps)]

    next_km = last_km + interval_km if interval_km is not None else None
    next_date = (
        _add_months(last_date, interval_months)
        if interval_months is not None and last_date is not None
        else None
    )
    return {"next_type": next_step, "next_km": next_km, "next_date": next_date}
