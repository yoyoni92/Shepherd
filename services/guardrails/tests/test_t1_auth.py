"""T1 - Deterministic auth pre-check."""
from unittest.mock import MagicMock

from shepherd_db.models import ChannelStatusEnum, DriverStatusEnum

from app.deterministic import auth


def _db(identity, driver=None):
    db = MagicMock()
    # always provide two items - auth() queries identity then driver when identity is linked
    db.query.return_value.filter_by.return_value.first.side_effect = [identity, driver]
    return db


def test_unknown_phone_fails():
    result = auth("+972500000000", _db(None))
    assert result["pass"] is False
    assert result["reason"] == "not registered"


def test_blocked_driver_fails():
    identity = MagicMock(status=ChannelStatusEnum.revoked)
    result = auth("+972501111111", _db(identity))
    assert result["pass"] is False
    assert result["reason"] == "blocked"


def test_valid_active_driver_passes_with_role():
    identity = MagicMock(status=ChannelStatusEnum.linked)
    driver = MagicMock(status=DriverStatusEnum.active)
    result = auth("+972502222222", _db(identity, driver))
    assert result["pass"] is True
    assert result["role"] == "driver"


def test_linked_non_driver_passes_with_user_role():
    identity = MagicMock(status=ChannelStatusEnum.linked)
    result = auth("+972503333333", _db(identity, None))
    assert result["pass"] is True
    assert result["role"] == "user"
