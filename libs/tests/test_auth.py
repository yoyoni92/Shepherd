import pytest
from pydantic import ValidationError
from shepherd_contracts import CallerContext, Role


def test_admin_needs_no_ids():
    ctx = CallerContext(role=Role.admin)
    assert ctx.role is Role.admin


def test_driver_requires_driver_id():
    CallerContext(role=Role.driver, driver_id="d-1")
    with pytest.raises(ValidationError):
        CallerContext(role=Role.driver)


def test_customer_requires_customer_id():
    CallerContext(role=Role.customer, customer_id="c-1")
    with pytest.raises(ValidationError):
        CallerContext(role=Role.customer)


def test_invalid_role_rejected():
    with pytest.raises(ValidationError):
        CallerContext(role="superuser")
