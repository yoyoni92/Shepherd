"""Tests for the data-driven maintenance cycle logic."""

from datetime import date

import pytest
from shepherd_db.logic import next_maintenance

TWO = ["קטן", "גדול"]
THREE = ["קטן א׳", "קטן ב׳", "גדול"]


def test_first_service_is_the_first_step():
    assert next_maintenance(None, TWO, last_km=0, interval_km=4) == {
        "next_type": "קטן",
        "next_km": 4,
        "next_date": None,
    }


def test_two_step_cycle_advances_and_wraps():
    assert next_maintenance("קטן", TWO, last_km=4, interval_km=4)["next_type"] == "גדול"
    assert next_maintenance("גדול", TWO, last_km=8, interval_km=4)["next_type"] == "קטן"


def test_three_step_cycle():
    assert next_maintenance("קטן א׳", THREE)["next_type"] == "קטן ב׳"
    assert next_maintenance("קטן ב׳", THREE)["next_type"] == "גדול"
    assert next_maintenance("גדול", THREE)["next_type"] == "קטן א׳"


def test_unknown_step_starts_from_the_beginning():
    assert next_maintenance("missing", TWO)["next_type"] == "קטן"


def test_interval_drives_next_km():
    assert next_maintenance("קטן", TWO, last_km=50000, interval_km=15000)["next_km"] == 65000


def test_km_only_cycle_has_no_due_date():
    nm = next_maintenance("קטן", TWO, last_km=50000, interval_km=15000)
    assert nm["next_date"] is None


def test_months_interval_drives_next_date():
    nm = next_maintenance(None, TWO, last_date=date(2026, 1, 15), interval_months=12)
    assert nm["next_date"] == date(2027, 1, 15)
    assert nm["next_km"] is None


def test_month_add_clamps_to_month_end():
    # 31 Jan + 1 month -> 28 Feb (no 31 Feb)
    assert next_maintenance(None, TWO, last_date=date(2026, 1, 31), interval_months=1)["next_date"] == date(2026, 2, 28)


def test_no_anchor_date_means_no_due_date():
    assert next_maintenance(None, TWO, interval_months=12)["next_date"] is None


def test_whichever_first_sets_both_thresholds():
    nm = next_maintenance("קטן", TWO, last_km=10000, interval_km=15000, last_date=date(2026, 6, 1), interval_months=12)
    assert nm["next_km"] == 25000
    assert nm["next_date"] == date(2027, 6, 1)


def test_empty_steps_raises():
    with pytest.raises(ValueError):
        next_maintenance(None, [])
