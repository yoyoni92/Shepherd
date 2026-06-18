from datetime import date

from app.profile import build_profile


def test_build_profile_fields():
    text = build_profile(
        vehicle_id="v1",
        plate="123-45-678",
        driver_name="יוסי כהן",
        customer_name="ABC Corp",
        insurance_valid_to=date(2025, 12, 31),
        license_valid_to=date(2026, 6, 30),
        last_maintenance_date=date(2024, 10, 1),
        last_maintenance_type="small",
        next_maintenance_km=60000,
        current_km=55000,
        open_tickets=2,
        recent_accidents=[{"date": "2024-05-10", "location": "Tel Aviv"}],
        open_events=[{"type": "insurance_expiring", "message": "expires soon"}],
    )
    assert "123-45-678" in text
    assert "יוסי כהן" in text      # Hebrew name preserved
    assert "ABC Corp" in text
    assert "2025-12-31" in text
    assert "2026-06-30" in text
    assert "2024-10-01" in text
    assert "60000" in text
    assert "55000" in text
    assert "2" in text              # open tickets
    assert "Tel Aviv" in text
    assert "insurance_expiring" in text


def test_build_profile_minimal():
    text = build_profile(vehicle_id="v2", plate="000-00-000")
    assert "000-00-000" in text
    assert "N/A" in text
