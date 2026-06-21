"""Maintenance cycle helper logic for Shepherd fleet management.

A maintenance type is an ordered list of unique step labels plus a fixed km interval.
Services advance through the steps in order, wrapping back to the first after the last.
"""


def next_maintenance(last_step, steps, *, last_km=0, interval_km=10_000):
    """Determine the next service step and km threshold from a data-driven cycle.

    Args:
        last_step: Label of the last service performed, or None for the first service.
        steps: Ordered list of unique step labels for the vehicle's maintenance type.
        last_km: Odometer at the last service.
        interval_km: Fixed km between any two consecutive services (per maintenance type).

    Returns:
        dict: {"next_type": str, "next_km": int}
    """
    if not steps:
        raise ValueError("steps must be a non-empty list")

    if last_step is None or last_step not in steps:
        next_step = steps[0]
    else:
        next_step = steps[(steps.index(last_step) + 1) % len(steps)]

    return {"next_type": next_step, "next_km": last_km + interval_km}
