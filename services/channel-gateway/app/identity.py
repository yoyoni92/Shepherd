from __future__ import annotations

from sqlalchemy.orm import Session

from shepherd_contracts import CallerContext, Role
from shepherd_db.models import (
    ChannelEnum,
    ChannelIdentity,
    ChannelStatusEnum,
    Customer,
    Driver,
)


def resolve_phone(channel: str, external_id: str, db: Session) -> str | None:
    row = (
        db.query(ChannelIdentity)
        .filter_by(channel=ChannelEnum[channel], external_id=external_id)
        .first()
    )
    if row is None or row.status == ChannelStatusEnum.revoked:
        return None
    return row.phone_number


def bind(channel: str, external_id: str, phone: str, db: Session) -> ChannelIdentity:
    channel_enum = ChannelEnum[channel]
    row = (
        db.query(ChannelIdentity)
        .filter_by(channel=channel_enum, external_id=external_id)
        .first()
    )
    if row:
        row.phone_number = phone
        row.status = ChannelStatusEnum.linked
    else:
        row = ChannelIdentity(
            channel=channel_enum, external_id=external_id, phone_number=phone
        )
        db.add(row)
    db.flush()
    return row


def resolve_caller(phone: str, db: Session) -> CallerContext | None:
    driver = db.query(Driver).filter_by(phone_number=phone).first()
    customer = db.query(Customer).filter_by(phone_number=phone).first()

    if driver is None and customer is None:
        return None
    if driver and customer:
        return CallerContext(
            role=Role.driver,
            driver_id=str(driver.driver_id),
            customer_id=str(customer.customer_id),
        )
    if driver:
        return CallerContext(role=Role.driver, driver_id=str(driver.driver_id))
    return CallerContext(role=Role.customer, customer_id=str(customer.customer_id))
