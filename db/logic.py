"""Maintenance cycle helper logic for Shepherd fleet management."""

_VALID_LAST_TYPES = (None, "small", "small_1", "small_2", "big")


def next_maintenance(last_type, cycle, *, last_km=0, interval_km=10_000):
    """
    Determine the next maintenance service type and km threshold.

    Each service is exactly interval_km from the previous one.

    Cycles:
      1_small_then_1_big  -> small, big, small, big, ...
      2_small_then_1_big  -> small_1, small_2, big, small_1, small_2, big, ...

    Args:
        last_type: Last service type ("small"|"small_1"|"small_2"|"big") or None (first).
        cycle: "1_small_then_1_big" or "2_small_then_1_big".
        last_km: Odometer at last service.
        interval_km: Fixed km between any two consecutive services.

    Returns:
        dict: {"next_type": str, "next_km": int}
    """
    if last_type not in _VALID_LAST_TYPES:
        raise ValueError(f"Unknown last_type: {last_type!r}")

    if cycle == "1_small_then_1_big":
        next_type = "small" if (last_type is None or last_type == "big") else "big"
    elif cycle == "2_small_then_1_big":
        if last_type is None or last_type == "big":
            next_type = "small_1"
        elif last_type == "small_1":
            next_type = "small_2"
        else:  # small_2
            next_type = "big"
    else:
        raise ValueError(f"Unknown cycle: {cycle!r}")

    return {"next_type": next_type, "next_km": last_km + interval_km}
