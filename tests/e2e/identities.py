"""Stable test identities for the cross-system integration suite.

Deterministic UUIDs/phones/chats in a dedicated namespace so the suite can seed its own
fleet graph (driver + assigned vehicle + customer + maintenance type + admin
authorization) into the live Postgres and clean it up without touching demo data.
"""

from __future__ import annotations

import uuid

_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "shepherd-e2e")


def _sid(name: str) -> uuid.UUID:
    return uuid.uuid5(_NS, name)


# Seeded fleet rows (created once per session, cleaned at the end).
DRIVER_ID = _sid("driver")
VEHICLE_ID = _sid("vehicle")
CUSTOMER_ID = _sid("customer")
MAINTENANCE_TYPE_ID = _sid("maintenance-type")
AUTHORIZATION_ID = _sid("authorization")

# Telegram chats (one per user type). High numbers to avoid colliding with real users.
DRIVER_CHAT = 990001
ADMIN_CHAT = 990002
UNKNOWN_CHAT = 990003

# Phones. Fleet normalizes to digits with +972 -> 0, so the seeded "+972..." driver/admin
# phones match the "0..." numbers a Telegram contact share delivers.
DRIVER_PHONE = "+972500000077"
ADMIN_PHONE = "+972500000088"
DRIVER_CONTACT = "0500000077"
ADMIN_CONTACT = "0500000088"
UNKNOWN_CONTACT = "0500009999"  # matches no driver or authorization

PLATE = "E2E-PLATE-01"
MAINTENANCE_TYPE_NAME = "E2E Service"
SEED_CURRENT_KM = 60000
SEED_NEXT_MAINTENANCE_KM = 50000  # current >= next, so the vehicle reads as overdue
