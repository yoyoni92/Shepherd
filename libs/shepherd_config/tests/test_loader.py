import pytest

from shepherd_config import get_config


def test_loads_minimal_config(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        '[database]\n'
        'url = "postgresql+psycopg://u:p@localhost:5432/db"\n'
        'shared_schema = "public"\n'
        '\n'
        '[services]\n'
        'fleet_api_url = "http://fleet-api:8000"\n'
    )
    monkeypatch.setenv("SHEPHERD_CONFIG", str(cfg_file))
    get_config.cache_clear()
    cfg = get_config()
    assert cfg.database.url == "postgresql+psycopg://u:p@localhost:5432/db"
    assert cfg.database.shared_schema == "public"
    assert cfg.services.fleet_api_url == "http://fleet-api:8000"


def test_interpolates_env_var(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        '[database]\n'
        'url = "${DATABASE_URL}"\n'
        '\n'
        '[services]\n'
        'fleet_api_url = "${FLEET_API_URL}"\n'
    )
    monkeypatch.setenv("SHEPHERD_CONFIG", str(cfg_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:y@db:5432/s")
    monkeypatch.setenv("FLEET_API_URL", "http://fleet-api:8000")
    get_config.cache_clear()
    cfg = get_config()
    assert cfg.database.url == "postgresql+psycopg://x:y@db:5432/s"
    assert cfg.services.fleet_api_url == "http://fleet-api:8000"


def test_missing_var_raises_naming_var(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        '[database]\n'
        'url = "${DATABASE_URL}"\n'
        '\n'
        '[services]\n'
        'fleet_api_url = "http://fleet-api:8000"\n'
    )
    monkeypatch.setenv("SHEPHERD_CONFIG", str(cfg_file))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_config.cache_clear()
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_config()
