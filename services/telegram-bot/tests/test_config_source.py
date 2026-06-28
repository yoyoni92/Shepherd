import importlib

from shepherd_config import get_config


def test_config_sources_db_and_fleet_url(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        '[database]\n'
        'url = "postgresql+psycopg://u:p@db:5432/s"\n'
        '\n'
        '[services]\n'
        'fleet_api_url = "http://fleet-api:9999"\n'
    )
    monkeypatch.setenv("SHEPHERD_CONFIG", str(cfg_file))
    get_config.cache_clear()
    import app.config as config

    importlib.reload(config)
    assert config.settings.database_url == "postgresql+psycopg://u:p@db:5432/s"
    assert config.settings.fleet_api_url == "http://fleet-api:9999"
