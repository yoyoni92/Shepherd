"""T2 - Permission matrix unit tests (pure, no DB needed).
T3 - Ownership scoping via matrix.
"""
import pytest

from app.auth import Action, can
from shepherd_contracts.auth import Role


@pytest.mark.parametrize("role,action,is_owner,expected", [
    # Admin ignores ownership everywhere
    (Role.admin, Action.MANAGE_VEHICLES, True,  True),
    (Role.admin, Action.MANAGE_VEHICLES, False, True),
    (Role.admin, Action.KM_UPDATE,       True,  True),
    (Role.admin, Action.KM_UPDATE,       False, True),
    (Role.admin, Action.READ_VEHICLES,   True,  True),
    (Role.admin, Action.READ_VEHICLES,   False, True),
    (Role.admin, Action.LOG_ACCIDENT,    True,  True),
    (Role.admin, Action.LOG_ACCIDENT,    False, True),
    (Role.admin, Action.LOG_CARE,        True,  True),
    (Role.admin, Action.EDIT_CONFIG,     True,  True),
    (Role.admin, Action.READ_CONFIG,     True,  True),

    # Driver - can only do ownership-scoped writes
    (Role.driver, Action.MANAGE_VEHICLES, True,  False),
    (Role.driver, Action.MANAGE_VEHICLES, False, False),
    (Role.driver, Action.KM_UPDATE,       True,  True),   # own vehicle
    (Role.driver, Action.KM_UPDATE,       False, False),  # not own
    (Role.driver, Action.LOG_ACCIDENT,    True,  True),
    (Role.driver, Action.LOG_ACCIDENT,    False, False),
    (Role.driver, Action.READ_VEHICLES,   True,  True),
    (Role.driver, Action.READ_VEHICLES,   False, False),
    (Role.driver, Action.LOG_CARE,        True,  False),  # driver cannot log care
    (Role.driver, Action.EDIT_CONFIG,     True,  False),
    (Role.driver, Action.READ_CONFIG,     True,  True),   # all can read config
    (Role.driver, Action.WRITE_REPORTS,   True,  False),
    (Role.driver, Action.SUBMIT_DOCUMENT, True,  True),
    (Role.driver, Action.SUBMIT_DOCUMENT, False, False),

    # Customer - read-only + submit own docs
    (Role.customer, Action.MANAGE_VEHICLES, True,  False),
    (Role.customer, Action.KM_UPDATE,       True,  False),  # customer cannot update km
    (Role.customer, Action.LOG_ACCIDENT,    True,  False),  # customer cannot log accidents
    (Role.customer, Action.LOG_CARE,        True,  False),
    (Role.customer, Action.READ_VEHICLES,   True,  True),
    (Role.customer, Action.READ_VEHICLES,   False, False),
    (Role.customer, Action.SUBMIT_DOCUMENT, True,  True),
    (Role.customer, Action.SUBMIT_DOCUMENT, False, False),
    (Role.customer, Action.EDIT_CONFIG,     True,  False),
    (Role.customer, Action.READ_CONFIG,     True,  True),
    (Role.customer, Action.WRITE_REPORTS,   True,  False),
])
def test_can(role, action, is_owner, expected):
    assert can(role, action, is_owner=is_owner) == expected
