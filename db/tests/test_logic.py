"""Tests for the data-driven maintenance cycle logic."""

import pytest
from shepherd_db.logic import next_maintenance

TWO = ["קטן", "גדול"]
THREE = ["קטן א׳", "קטן ב׳", "גדול"]


def test_first_service_is_the_first_step():
    assert next_maintenance(None, TWO, last_km=0, interval_km=4) == {"next_type": "קטן", "next_km": 4}


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


def test_empty_steps_raises():
    with pytest.raises(ValueError):
        next_maintenance(None, [])
