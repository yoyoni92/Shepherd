"""Caller context + roles, resolved upstream and trusted by Fleet API only via internal token."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, model_validator


class Role(str, Enum):
    admin = "admin"
    driver = "driver"
    customer = "customer"


class CallerContext(BaseModel):
    role: Role
    driver_id: str | None = None
    customer_id: str | None = None

    @model_validator(mode="after")
    def _ids_match_role(self) -> CallerContext:
        if self.role is Role.driver and not self.driver_id:
            raise ValueError("driver role requires driver_id")
        if self.role is Role.customer and not self.customer_id:
            raise ValueError("customer role requires customer_id")
        return self
