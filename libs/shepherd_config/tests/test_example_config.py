from pathlib import Path

from shepherd_config import get_config

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_example_config_loads(monkeypatch):
    example = REPO_ROOT / "config.example.toml"
    monkeypatch.setenv("SHEPHERD_CONFIG", str(example))
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/s")
    monkeypatch.setenv("FLEET_API_URL", "http://fleet-api:8000")
    get_config.cache_clear()
    cfg = get_config()
    assert cfg.database.url == "postgresql+psycopg://u:p@db:5432/s"
    assert cfg.database.shared_schema == "public"
    assert cfg.services.fleet_api_url == "http://fleet-api:8000"
    assert {c.slug for c in cfg.companies} == {"default", "internal"}
