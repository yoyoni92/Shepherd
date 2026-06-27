"""Caller context + roles, resolved upstream and trusted by Fleet API only via internal token."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, model_validator


class Role(str, Enum):
    admin = "admin"
    driver = "driver"
    customer = "customer"
    company_admin = "company_admin"


class CallerContext(BaseModel):
    role: Role
    driver_id: str | None = None
    customer_id: str | None = None
    # ponytail: presence (not the role) drives tenant scoping; admin+company_id = the
    # system-admin "acting within a company" case, company_admin always carries it (Feature 2).
    company_id: str | None = None

    @model_validator(mode="after")
    def _ids_match_role(self) -> CallerContext:
        if self.role is Role.driver and not self.driver_id:
            raise ValueError("driver role requires driver_id")
        if self.role is Role.customer and not self.customer_id:
            raise ValueError("customer role requires customer_id")
        if self.role is Role.company_admin and not self.company_id:
            raise ValueError("company_admin role requires company_id")
        return self
