"""Shared driver-field validation for update-details (4.4) and update-driver (5.4)."""

from __future__ import annotations

import re
from datetime import datetime

from app import texts

PHONE_RE = re.compile(r"^0\d{8,9}$")

# Callback (from either flow's field keyboard) -> canonical field key.
CANONICAL = {
    "ud_license_valid": "license_valid",
    "ud_license_number": "license_number",
    "ud_phone": "phone",
    "ud2_field_license_valid": "license_valid",
    "ud2_field_license_number": "license_number",
    "ud2_field_phone": "phone",
}

_VALUE_PROMPT = {
    "license_valid": texts.UPDATE_VALUE_DATE,
    "license_number": texts.UPDATE_VALUE_LICENSE,
    "phone": texts.UPDATE_VALUE_PHONE,
}


def field_from_callback(cb: str | None) -> str | None:
    if cb is None:
        return None
    return CANONICAL.get(cb)


def value_prompt(field: str | None) -> str:
    if field is None:
        return ""
    return _VALUE_PROMPT.get(field, "")


def validate(field: str | None, value: str | None) -> tuple[bool, str | None, str | None]:
    """Return (ok, db_column, normalized_value)."""
    if field is None:
        return (False, None, None)
    value = (value or "").strip()
    if field == "license_valid":
        try:
            d = datetime.strptime(value, "%d/%m/%Y").date()
        except ValueError:
            return (False, None, None)
        return (True, "license_valid_to", d.isoformat())
    if field == "phone":
        if not PHONE_RE.match(value):
            return (False, None, None)
        return (True, "phone_number", value)
    if field == "license_number":
        if not value:
            return (False, None, None)
        return (True, "license_number", value)
    return (False, None, None)
