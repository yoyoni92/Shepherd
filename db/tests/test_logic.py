"""Tests for maintenance cycle logic."""

import pytest
from logic import next_maintenance

# (last_type, cycle, last_km, interval_km, expected_type, expected_km)
CASES = [
    # 1_small_then_1_big: small <-> big every 4 units
    (None,    "1_small_then_1_big", 0,  4, "small", 4),
    ("small", "1_small_then_1_big", 4,  4, "big",   8),
    ("big",   "1_small_then_1_big", 8,  4, "small", 12),
    ("big",   "1_small_then_1_big", 12, 4, "small", 16),

    # 2_small_then_1_big: small_1 -> small_2 -> big every 5 units
    (None,      "2_small_then_1_big", 0,  5, "small_1", 5),
    ("small_1", "2_small_then_1_big", 5,  5, "small_2", 10),
    ("small_2", "2_small_then_1_big", 10, 5, "big",     15),
    ("big",     "2_small_then_1_big", 15, 5, "small_1", 20),
]


@pytest.mark.parametrize(
    "last_type,cycle,last_km,interval_km,expected_type,expected_km",
    CASES,
)
def test_next_maintenance(last_type, cycle, last_km, interval_km, expected_type, expected_km):
    result = next_maintenance(last_type, cycle, last_km=last_km, interval_km=interval_km)
    assert result["next_type"] == expected_type
    assert result["next_km"] == expected_km


def test_next_maintenance_invalid_last_type():
    with pytest.raises(ValueError):
        next_maintenance("typo", "1_small_then_1_big", last_km=0)
