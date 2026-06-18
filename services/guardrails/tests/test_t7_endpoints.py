"""T7 - Endpoints: shape, short-circuit, no LLM call on deterministic fail."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset(mocker):
    """Override DB dependency and reset provider singleton between tests."""
    app.dependency_overrides[get_db] = lambda: MagicMock()
    mocker.patch("app.main._provider", None)
    yield
    app.dependency_overrides.clear()


def test_check_input_pass_returns_correct_shape(mocker):
    mocker.patch("app.main.auth", return_value={"pass": True, "reason": "ok", "role": "driver"})
    mocker.patch("app.main._get_allowed_languages", return_value=["he", "en"])
    mocker.patch("app.main.language", return_value={"pass": True, "reason": "he"})
    mock_provider = MagicMock()
    mock_provider.check_input.return_value = {"pass": True, "reason": "ok"}
    mocker.patch("app.main._get_provider", return_value=mock_provider)

    resp = client.post("/check/input", json={"phone": "+972501234567", "text": "עדכון קמ", "context": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert "pass" in data
    assert "reason" in data


def test_auth_fail_short_circuits_before_llm(mocker):
    mocker.patch("app.main.auth", return_value={"pass": False, "reason": "not registered"})
    mock_provider = MagicMock()
    mocker.patch("app.main._get_provider", return_value=mock_provider)

    resp = client.post("/check/input", json={"phone": "+972999999999", "text": "test", "context": {}})
    assert resp.status_code == 200
    assert resp.json()["pass"] is False
    assert resp.json()["reason"] == "not registered"
    mock_provider.check_input.assert_not_called()


def test_language_fail_short_circuits_before_llm(mocker):
    mocker.patch("app.main.auth", return_value={"pass": True, "reason": "ok", "role": "driver"})
    mocker.patch("app.main._get_allowed_languages", return_value=["he", "en"])
    mocker.patch("app.main.language", return_value={"pass": False, "reason": "language 'fr' not allowed"})
    mock_provider = MagicMock()
    mocker.patch("app.main._get_provider", return_value=mock_provider)

    resp = client.post("/check/input", json={"phone": "+972501234567", "text": "bonjour", "context": {}})
    assert resp.status_code == 200
    assert resp.json()["pass"] is False
    mock_provider.check_input.assert_not_called()


def test_check_output_returns_correct_shape(mocker):
    mock_provider = MagicMock()
    mock_provider.check_output.return_value = {"pass": True, "reason": "ok"}
    mocker.patch("app.main._get_provider", return_value=mock_provider)

    resp = client.post("/check/output", json={"text": "Vehicle has 50000 km", "sources": ["50000 km"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "pass" in data
    assert "reason" in data


def test_get_allowed_languages_returns_default():
    from unittest.mock import MagicMock

    from app.main import _get_allowed_languages

    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None
    assert _get_allowed_languages(db) == ["he", "en"]


def test_get_allowed_languages_from_config():
    from unittest.mock import MagicMock

    from app.main import _get_allowed_languages

    db = MagicMock()
    config_row = MagicMock()
    config_row.config_value = ["he", "en", "ar"]
    db.query.return_value.filter_by.return_value.first.return_value = config_row
    assert _get_allowed_languages(db) == ["he", "en", "ar"]


def test_get_provider_creates_singleton():
    import app.main as main_module

    main_module._provider = None
    p1 = main_module._get_provider()
    p2 = main_module._get_provider()
    assert p1 is p2
    main_module._provider = None  # cleanup


def test_get_db_yields_and_closes(mocker):
    import os

    import app.main as main_module

    main_module._SessionLocal = None
    mock_session = MagicMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mocker.patch("app.main.create_engine")
    mocker.patch("app.main.sessionmaker", return_value=mock_session_factory)
    mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://fake/db"})

    gen = main_module.get_db()
    db = next(gen)
    assert db is mock_session
    try:
        next(gen)
    except StopIteration:
        pass
    mock_session.close.assert_called_once()
    main_module._SessionLocal = None  # cleanup


def test_check_output_fail_includes_safe_text(mocker):
    mock_provider = MagicMock()
    mock_provider.check_output.return_value = {
        "pass": False,
        "reason": "unsupported claim",
        "safe_text": "[REDACTED]",
    }
    mocker.patch("app.main._get_provider", return_value=mock_provider)

    resp = client.post("/check/output", json={"text": "fabricated fine of 500", "sources": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pass"] is False
    assert data["safe_text"] == "[REDACTED]"
