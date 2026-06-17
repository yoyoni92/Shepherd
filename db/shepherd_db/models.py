"""SQLAlchemy 2.x declarative models for the Shepherd fleet database."""

import enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship
from sqlalchemy.sql import text


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AllowedDriverEnum(str, enum.Enum):
    all_drivers = "all_drivers"
    specific_driver_only = "specific_driver_only"


class MaintenanceTypeEnum(str, enum.Enum):
    one_small_then_one_big = "1_small_then_1_big"
    two_small_then_one_big = "2_small_then_1_big"


class LastMaintenanceTypeEnum(str, enum.Enum):
    small = "small"      # used by 1_small_then_1_big
    small_1 = "small_1"  # first small in 2_small_then_1_big
    small_2 = "small_2"  # second small in 2_small_then_1_big
    big = "big"


class DriverStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class CustomerStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class KmUpdateSourceEnum(str, enum.Enum):
    telegram = "telegram"
    admin_ui = "admin_ui"


class AccidentAttachmentCategoryEnum(str, enum.Enum):
    another_driver_insurance = "another_driver_insurance"
    another_car_registration = "another_car_registration"
    photo_our_vehicle = "photo_our_vehicle"
    photo_other_vehicle = "photo_other_vehicle"
    photo_accident_area = "photo_accident_area"


class TicketTypeEnum(str, enum.Enum):
    traffic = "traffic"
    parking = "parking"


class ReportStatusEnum(str, enum.Enum):
    unpaid = "unpaid"
    paid = "paid"
    contested = "contested"
    transferred_to_driver = "transferred_to_driver"


class EventTypeEnum(str, enum.Enum):
    maintenance_due = "maintenance_due"
    license_expiring = "license_expiring"
    insurance_expiring = "insurance_expiring"
    ticket_received = "ticket_received"
    accident_logged = "accident_logged"


class EventSeverityEnum(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class EventSourceTypeEnum(str, enum.Enum):
    km_updates = "km_updates"
    scheduler = "scheduler"
    accidents = "accidents"
    reports = "reports"


class EventStatusEnum(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"
    dismissed = "dismissed"


class ChannelEnum(str, enum.Enum):
    telegram = "telegram"
    whatsapp = "whatsapp"
    webapp = "webapp"


class ChannelStatusEnum(str, enum.Enum):
    linked = "linked"
    revoked = "revoked"


# ---------------------------------------------------------------------------
# SQLAlchemy Enum type helpers (named types matching PG enum names)
# ---------------------------------------------------------------------------

allowed_driver_type = SAEnum(
    AllowedDriverEnum,
    name="allowed_driver_enum",
    create_type=False,
)
maintenance_type_type = SAEnum(
    MaintenanceTypeEnum,
    name="maintenance_type_enum",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)
last_maintenance_type_type = SAEnum(
    LastMaintenanceTypeEnum,
    name="last_maintenance_type_enum",
    create_type=False,
)
driver_status_type = SAEnum(
    DriverStatusEnum,
    name="driver_status_enum",
    create_type=False,
)
customer_status_type = SAEnum(
    CustomerStatusEnum,
    name="customer_status_enum",
    create_type=False,
)
km_update_source_type = SAEnum(
    KmUpdateSourceEnum,
    name="km_update_source_enum",
    create_type=False,
)
accident_attachment_category_type = SAEnum(
    AccidentAttachmentCategoryEnum,
    name="accident_attachment_category_enum",
    create_type=False,
)
ticket_type_type = SAEnum(
    TicketTypeEnum,
    name="ticket_type_enum",
    create_type=False,
)
report_status_type = SAEnum(
    ReportStatusEnum,
    name="report_status_enum",
    create_type=False,
)
event_type_type = SAEnum(
    EventTypeEnum,
    name="event_type_enum",
    create_type=False,
)
event_severity_type = SAEnum(
    EventSeverityEnum,
    name="event_severity_enum",
    create_type=False,
)
event_source_type_type = SAEnum(
    EventSourceTypeEnum,
    name="event_source_type_enum",
    create_type=False,
)
event_status_type = SAEnum(
    EventStatusEnum,
    name="event_status_enum",
    create_type=False,
)
channel_type = SAEnum(
    ChannelEnum,
    name="channel_enum",
    create_type=False,
)
channel_status_type = SAEnum(
    ChannelStatusEnum,
    name="channel_status_enum",
    create_type=False,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class Driver(Base):
    __tablename__ = "drivers"

    driver_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    full_name = mapped_column(Text, nullable=False)
    phone_number = mapped_column(Text, unique=True, nullable=False)
    license_number = mapped_column(Text, nullable=True)
    status = mapped_column(
        driver_status_type,
        nullable=False,
        server_default="active",
    )


class Customer(Base):
    __tablename__ = "customers"

    customer_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    full_name = mapped_column(Text, nullable=False)
    phone_number = mapped_column(Text, nullable=True)
    email = mapped_column(Text, nullable=True)
    status = mapped_column(
        customer_status_type,
        nullable=False,
        server_default="active",
    )


class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    licensing_plate = mapped_column(Text, unique=True, nullable=False)
    nickname = mapped_column(Text, nullable=True)
    inseration_ts = mapped_column(DateTime(timezone=True), nullable=True)
    insurance_valid_to = mapped_column(Date, nullable=True)
    license_valid_to = mapped_column(Date, nullable=True)
    insurance_file_url = mapped_column(Text, nullable=True)
    registration_file_url = mapped_column(Text, nullable=True)
    allowed_driver = mapped_column(allowed_driver_type, nullable=True)
    vendor = mapped_column(Text, nullable=True)
    model = mapped_column(Text, nullable=True)
    last_maintenance_date = mapped_column(Date, nullable=True)
    last_maintenance_type = mapped_column(last_maintenance_type_type, nullable=True)
    last_maintenance_km = mapped_column(Integer, nullable=True)
    next_maintenance_km = mapped_column(Integer, nullable=True)
    next_maintenance_type = mapped_column(last_maintenance_type_type, nullable=True)
    current_km = mapped_column(Integer, nullable=True)
    driver_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=True,
    )
    maintenance_type = mapped_column(maintenance_type_type, nullable=True)
    customer_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.customer_id"),
        nullable=True,
    )

    driver = relationship("Driver", foreign_keys=[driver_id])
    customer = relationship("Customer", foreign_keys=[customer_id])


class Accident(Base):
    __tablename__ = "accidents"

    accident_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False,
    )
    driver_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=True,
    )
    datetime = mapped_column(DateTime(timezone=True), nullable=False)
    location = mapped_column(Text, nullable=True)
    description = mapped_column(Text, nullable=True)
    another_driver_licensing_plate = mapped_column(Text, nullable=True)
    another_driver_phone_number = mapped_column(Text, nullable=True)
    another_driver_id_number = mapped_column(Text, nullable=True)

    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id])
    driver = relationship("Driver", foreign_keys=[driver_id])


class AccidentAttachment(Base):
    __tablename__ = "accident_attachments"

    attachment_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    accident_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accidents.accident_id"),
        nullable=False,
    )
    category = mapped_column(accident_attachment_category_type, nullable=False)
    file_url = mapped_column(Text, nullable=False)
    uploaded_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    accident = relationship("Accident", foreign_keys=[accident_id])


class KmUpdate(Base):
    __tablename__ = "km_updates"

    km_update_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False,
    )
    km = mapped_column(Integer, nullable=False)
    recorded_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    driver_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=True,
    )
    source = mapped_column(km_update_source_type, nullable=False)

    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id])
    driver = relationship("Driver", foreign_keys=[driver_id])


class VehicleCare(Base):
    __tablename__ = "vehicle_care"

    care_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False,
    )
    service_date = mapped_column(Date, nullable=False)
    maintenance_type = mapped_column(last_maintenance_type_type, nullable=False)
    km_at_service = mapped_column(Integer, nullable=False)
    description = mapped_column(Text, nullable=True)
    cost = mapped_column(Numeric(10, 2), nullable=True)
    garage = mapped_column(Text, nullable=True)
    invoice_file_url = mapped_column(Text, nullable=True)
    next_maintenance_km = mapped_column(Integer, nullable=True)
    driver_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=True,
    )
    created_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id])
    driver = relationship("Driver", foreign_keys=[driver_id])


class Report(Base):
    __tablename__ = "reports"

    report_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False,
    )
    driver_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=True,
    )
    ticket_type = mapped_column(ticket_type_type, nullable=False)
    violation_desc = mapped_column(Text, nullable=True)
    amount = mapped_column(Numeric(10, 2), nullable=True)
    issued_ts = mapped_column(DateTime(timezone=True), nullable=True)
    due_date = mapped_column(Date, nullable=True)
    status = mapped_column(
        report_status_type,
        nullable=False,
        server_default="unpaid",
    )
    location = mapped_column(Text, nullable=True)
    authority = mapped_column(Text, nullable=True)
    file_url = mapped_column(Text, nullable=True)
    created_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id])
    driver = relationship("Driver", foreign_keys=[driver_id])


class Event(Base):
    __tablename__ = "events"

    event_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=True,
    )
    event_type = mapped_column(event_type_type, nullable=False)
    severity = mapped_column(event_severity_type, nullable=False)
    message = mapped_column(Text, nullable=False)
    payload_json = mapped_column(JSONB, nullable=True)
    source_type = mapped_column(event_source_type_type, nullable=True)
    source_id = mapped_column(UUID(as_uuid=True), nullable=True)
    status = mapped_column(
        event_status_type,
        nullable=False,
        server_default="open",
    )
    notified = mapped_column(Boolean, nullable=False, server_default="false")
    triggered_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id])


class SystemConfig(Base):
    __tablename__ = "system_config"

    config_key = mapped_column(Text, primary_key=True)
    config_value = mapped_column(JSONB, nullable=False)
    description = mapped_column(Text, nullable=True)
    updated_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_by = mapped_column(Text, nullable=True)


class ChannelIdentity(Base):
    __tablename__ = "channel_identities"

    identity_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    channel = mapped_column(channel_type, nullable=False)
    external_id = mapped_column(Text, nullable=False)
    phone_number = mapped_column(Text, nullable=False)
    status = mapped_column(
        channel_status_type,
        nullable=False,
        server_default="linked",
    )
    linked_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (UniqueConstraint("channel", "external_id"),)
