"""T5 - Identity binding & role resolution."""
import uuid
from unittest.mock import MagicMock

from shepherd_contracts import CallerContext, Role
from shepherd_db.models import ChannelEnum, ChannelIdentity, ChannelStatusEnum, Customer, Driver


def _mock_db():
    return MagicMock()


def _linked_row(phone: str) -> ChannelIdentity:
    row = MagicMock(spec=ChannelIdentity)
    row.phone_number = phone
    row.status = ChannelStatusEnum.linked
    return row


def _revoked_row() -> ChannelIdentity:
    row = MagicMock(spec=ChannelIdentity)
    row.phone_number = "+972500000000"
    row.status = ChannelStatusEnum.revoked
    return row


def _driver_row(phone: str) -> Driver:
    row = MagicMock(spec=Driver)
    row.driver_id = uuid.uuid4()
    row.phone_number = phone
    return row


def _customer_row(phone: str) -> Customer:
    row = MagicMock(spec=Customer)
    row.customer_id = uuid.uuid4()
    row.phone_number = phone
    return row


# --- resolve_phone ---

def test_resolve_phone_returns_phone_when_bound():
    from app.identity import resolve_phone

    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.return_value = _linked_row("+972501234567")

    assert resolve_phone("telegram", "123", db) == "+972501234567"


def test_resolve_phone_returns_none_when_unbound():
    from app.identity import resolve_phone

    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.return_value = None

    assert resolve_phone("telegram", "999", db) is None


def test_resolve_phone_returns_none_when_revoked():
    from app.identity import resolve_phone

    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.return_value = _revoked_row()

    assert resolve_phone("telegram", "123", db) is None


# --- bind ---

def test_bind_creates_new_row():
    from app.identity import bind

    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.return_value = None

    result = bind("telegram", "987654321", "+972501234567", db)
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_bind_updates_existing_row():
    from app.identity import bind

    existing = _linked_row("+972500000000")
    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.return_value = existing

    bind("telegram", "987654321", "+972501234567", db)
    assert existing.phone_number == "+972501234567"
    db.add.assert_not_called()
    db.flush.assert_called_once()


# --- resolve_caller ---

def test_resolve_caller_driver_only():
    from app.identity import resolve_caller

    driver = _driver_row("+972501234567")
    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.side_effect = [driver, None]

    ctx = resolve_caller("+972501234567", db)
    assert ctx is not None
    assert ctx.role == Role.driver
    assert ctx.driver_id == str(driver.driver_id)


def test_resolve_caller_customer_only():
    from app.identity import resolve_caller

    customer = _customer_row("+972501234567")
    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.side_effect = [None, customer]

    ctx = resolve_caller("+972501234567", db)
    assert ctx is not None
    assert ctx.role == Role.customer
    assert ctx.customer_id == str(customer.customer_id)


def test_resolve_caller_union_permissions():
    from app.identity import resolve_caller

    driver = _driver_row("+972501234567")
    customer = _customer_row("+972501234567")
    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.side_effect = [driver, customer]

    ctx = resolve_caller("+972501234567", db)
    assert ctx is not None
    assert ctx.role == Role.driver
    assert ctx.driver_id == str(driver.driver_id)
    assert ctx.customer_id == str(customer.customer_id)


def test_resolve_caller_unknown_phone_returns_none():
    from app.identity import resolve_caller

    db = _mock_db()
    db.query.return_value.filter_by.return_value.first.side_effect = [None, None]

    assert resolve_caller("+972509999999", db) is None
