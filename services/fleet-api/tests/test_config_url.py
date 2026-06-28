from app import deps
from shepherd_config import get_config


def test_get_engine_uses_config_url(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        '[database]\n'
        'url = "sqlite+pysqlite:///:memory:"\n'
        '\n'
        '[services]\n'
        'fleet_api_url = "http://fleet-api:8000"\n'
    )
    monkeypatch.setenv("SHEPHERD_CONFIG", str(cfg_file))
    get_config.cache_clear()
    deps._engine = None
    engine = deps.get_engine()
    assert engine.url.drivername == "sqlite+pysqlite"
