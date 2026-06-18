from datetime import date
from typing import Optional


def build_profile(
    vehicle_id: str,
    plate: str,
    driver_name: Optional[str] = None,
    customer_name: Optional[str] = None,
    insurance_valid_to: Optional[date] = None,
    license_valid_to: Optional[date] = None,
    last_maintenance_date: Optional[date] = None,
    last_maintenance_type: Optional[str] = None,
    next_maintenance_km: Optional[int] = None,
    current_km: Optional[int] = None,
    open_tickets: int = 0,
    recent_accidents: Optional[list[dict]] = None,
    open_events: Optional[list[dict]] = None,
) -> str:
    lines = [
        f"Vehicle: {plate}",
        f"Driver: {driver_name or 'N/A'}",
        f"Customer: {customer_name or 'N/A'}",
        f"Insurance valid to: {insurance_valid_to or 'N/A'}",
        f"License valid to: {license_valid_to or 'N/A'}",
        f"Last maintenance: {last_maintenance_date or 'N/A'} ({last_maintenance_type or 'N/A'})",
        f"Next maintenance at km: {next_maintenance_km or 'N/A'} (current: {current_km or 'N/A'} km)",
        f"Open tickets: {open_tickets}",
    ]
    for acc in (recent_accidents or []):
        lines.append(f"Accident on {acc.get('date', 'N/A')} at {acc.get('location', 'N/A')}")
    for ev in (open_events or []):
        lines.append(f"Event: {ev.get('type', 'N/A')} - {ev.get('message', '')}")
    return "\n".join(lines)
