# Central Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a single structured `config.toml` as the source of truth for the DB
connection string and the per-company schema map, loaded by a new shared `shepherd_config`
package via a cached, typed Pydantic model with `${VAR}` env interpolation, and adopt it in
fleet-api and telegram-bot. Add the `schema_name` column to `company_settings` (plumbing only;
seeding/provisioning is owned by the schema-per-tenant plan).

**Architecture:** New Poetry package `libs/shepherd_config` (poetry name `shepherd-config`,
import `shepherd_config`), packaged exactly like `shepherd-contracts` (a directory with its own
`pyproject.toml` and an included module dir). It exposes one `functools.lru_cache`-wrapped
`get_config() -> Config`. The loader reads TOML with stdlib `tomllib`, then walks every string
leaf replacing `${VAR}` from `os.environ` (unset var -> `RuntimeError` naming the var), and
validates into Pydantic v2 models. fleet-api and telegram-bot take it as a path dep and read the
DB url / fleet-api url from it. webui stays on env vars (no renderer is built).

**Tech Stack:** Python 3.12, Poetry, Pydantic v2, stdlib tomllib, pytest.

## Global Constraints
- Package dir is `libs/shepherd_config` (poetry name `shepherd-config`, import `shepherd_config`), packaged like `shepherd-contracts`.
- Config file path: env `SHEPHERD_CONFIG`, default `config.toml` at repo root; container path `/etc/shepherd/config.toml`.
- TOML is read with stdlib `tomllib` only - no `toml`/`tomli` dependency is added.
- `get_config()` is wrapped in `functools.lru_cache`; every test calls `get_config.cache_clear()` before loading.
- `${VAR}` interpolation is a small regex over string leaves only - not a templating engine.
- An unset referenced env var raises `RuntimeError` naming the variable.
- Pydantic v2; `CompanyConfig.schema_name = Field(alias="schema")`; the TOML array is `[[company]]`, aliased to the `Config.companies` field (matches the spec and `deploy/config.example.toml`).
- `config.toml` is gitignored; `config.example.toml` is committed at the repo root.
- DB change: `CompanySettings.schema_name = mapped_column(Text, nullable=False)` - column only, no seeding.
- webui is unchanged (keeps reading env vars); deliberate simplifications carry a `# ponytail:` comment.
---

### Task 1: Scaffold `shepherd_config` package and load a minimal config

**Files:**
- create `libs/shepherd_config/pyproject.toml`
- create `libs/shepherd_config/shepherd_config/__init__.py`
- create `libs/shepherd_config/shepherd_config/loader.py`
- test `libs/shepherd_config/tests/test_loader.py`

**Interfaces:**
- Produces: `shepherd_config.get_config() -> Config` (lru_cache'd), `Config(database: DatabaseConfig, services: ServicesConfig)`, `DatabaseConfig(url: str, shared_schema: str = "public")`, `ServicesConfig(fleet_api_url: str)`.
- Consumes: env `SHEPHERD_CONFIG` (path to the TOML file), default `config.toml`.

Steps:

- [x] **Step 1 - Write the failing test.** Create `libs/shepherd_config/tests/test_loader.py`:
```python
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
```

- [x] **Step 2 - Run it, expect FAIL.** `cd libs/shepherd_config && poetry install && poetry run pytest tests/test_loader.py::test_loads_minimal_config -q`
  Expected: `ModuleNotFoundError: No module named 'shepherd_config'` (the package does not exist yet).

- [x] **Step 3 - Minimal implementation.** Create the package.

  `libs/shepherd_config/pyproject.toml`:
```toml
[tool.poetry]
name = "shepherd-config"
version = "0.1.0"
description = "Central config loader (config.toml + ${VAR} env interpolation) for Shepherd services"
authors = ["Shepherd Team <team@shepherd.local>"]
packages = [{ include = "shepherd_config" }]

[tool.poetry.dependencies]
python = "^3.12"
pydantic = "^2.9"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"

[build-system]
requires = ["poetry-core>=1.9"]
build-backend = "poetry.core.masonry.api"
```

  `libs/shepherd_config/shepherd_config/loader.py`:
```python
"""Central config loader: read config.toml, build a typed Config."""
from __future__ import annotations

import functools
import os
import tomllib
from pathlib import Path

from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    url: str
    shared_schema: str = "public"


class ServicesConfig(BaseModel):
    fleet_api_url: str


class Config(BaseModel):
    database: DatabaseConfig
    services: ServicesConfig


def _config_path() -> Path:
    return Path(os.environ.get("SHEPHERD_CONFIG", "config.toml"))


@functools.lru_cache
def get_config() -> Config:
    with _config_path().open("rb") as fh:
        raw = tomllib.load(fh)
    return Config.model_validate(raw)
```

  `libs/shepherd_config/shepherd_config/__init__.py`:
```python
"""Central config package for Shepherd services."""
from .loader import Config, DatabaseConfig, ServicesConfig, get_config

__all__ = [
    "Config",
    "DatabaseConfig",
    "ServicesConfig",
    "get_config",
]
```

- [x] **Step 4 - Run it, expect PASS.** `cd libs/shepherd_config && poetry run pytest tests/test_loader.py::test_loads_minimal_config -q` -> 1 passed.

- [x] **Step 5 - Commit.**
```
git add libs/shepherd_config/pyproject.toml libs/shepherd_config/shepherd_config/__init__.py libs/shepherd_config/shepherd_config/loader.py libs/shepherd_config/tests/test_loader.py
git commit -m "add shepherd_config package with config.toml loader

New libs/shepherd_config Poetry package (poetry name shepherd-config,
import shepherd_config), packaged like shepherd-contracts. Exposes a
single lru_cache-wrapped get_config() that reads the TOML pointed at by
SHEPHERD_CONFIG (default config.toml) into typed Pydantic models."
```

---

### Task 2: Interpolate `${VAR}` env references in string leaves

**Files:**
- modify `libs/shepherd_config/shepherd_config/loader.py`
- test `libs/shepherd_config/tests/test_loader.py`

**Interfaces:**
- Produces: loader resolves `${VAR}` in any string value from `os.environ` before validation.
- Consumes: process environment variables referenced in the TOML.

Steps:

- [ ] **Step 1 - Write the failing test.** Append to `libs/shepherd_config/tests/test_loader.py`:
```python
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
```

- [ ] **Step 2 - Run it, expect FAIL.** `cd libs/shepherd_config && poetry run pytest tests/test_loader.py::test_interpolates_env_var -q`
  Expected: a Pydantic `ValidationError` is NOT raised, but `cfg.database.url == "${DATABASE_URL}"` so the assertion fails: `assert '${DATABASE_URL}' == 'postgresql+psycopg://x:y@db:5432/s'`.

- [ ] **Step 3 - Minimal implementation.** Edit `libs/shepherd_config/shepherd_config/loader.py`. Add `import re` to the imports and the helpers below, and change `get_config` to walk the parsed data first.

  Add after the imports:
```python
_VAR = re.compile(r"\$\{([^}]+)\}")


def _interpolate(value: str) -> str:
    # ponytail: a tiny regex over string leaves, not a templating engine.
    return _VAR.sub(lambda m: os.environ[m.group(1)], value)


def _walk(node):
    if isinstance(node, str):
        return _interpolate(node)
    if isinstance(node, dict):
        return {k: _walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v) for v in node]
    return node
```

  Change the body of `get_config`:
```python
@functools.lru_cache
def get_config() -> Config:
    with _config_path().open("rb") as fh:
        raw = tomllib.load(fh)
    return Config.model_validate(_walk(raw))
```

- [ ] **Step 4 - Run it, expect PASS.** `cd libs/shepherd_config && poetry run pytest tests/test_loader.py -q` -> 2 passed.

- [ ] **Step 5 - Commit.**
```
git add libs/shepherd_config/shepherd_config/loader.py libs/shepherd_config/tests/test_loader.py
git commit -m "interpolate \${VAR} env refs in shepherd_config loader

Walk every string leaf of the parsed TOML and substitute \${VAR} from the
process environment before validation, so secrets live only in the
environment and never in the committed config template."
```

---

### Task 3: Raise a named error when a referenced `${VAR}` is unset

**Files:**
- modify `libs/shepherd_config/shepherd_config/loader.py`
- test `libs/shepherd_config/tests/test_loader.py`

**Interfaces:**
- Produces: unset `${VAR}` -> `RuntimeError` whose message names the variable.

Steps:

- [ ] **Step 1 - Write the failing test.** Append to `libs/shepherd_config/tests/test_loader.py`:
```python
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
```

- [ ] **Step 2 - Run it, expect FAIL.** `cd libs/shepherd_config && poetry run pytest tests/test_loader.py::test_missing_var_raises_naming_var -q`
  Expected: `Failed: DID NOT RAISE <class 'RuntimeError'>` wrapping a `KeyError: 'DATABASE_URL'` (current code raises `KeyError`, not `RuntimeError`).

- [ ] **Step 3 - Minimal implementation.** Edit `libs/shepherd_config/shepherd_config/loader.py`, replacing `_interpolate`:
```python
def _interpolate(value: str) -> str:
    # ponytail: a tiny regex over string leaves, not a templating engine.
    def repl(m: "re.Match[str]") -> str:
        name = m.group(1)
        try:
            return os.environ[name]
        except KeyError:
            raise RuntimeError(
                f"config references unset environment variable: {name}"
            ) from None

    return _VAR.sub(repl, value)
```

- [ ] **Step 4 - Run it, expect PASS.** `cd libs/shepherd_config && poetry run pytest tests/test_loader.py -q` -> 3 passed.

- [ ] **Step 5 - Commit.**
```
git add libs/shepherd_config/shepherd_config/loader.py libs/shepherd_config/tests/test_loader.py
git commit -m "raise on unset \${VAR} in shepherd_config loader

Turn a missing referenced environment variable into a RuntimeError that
names the variable, so a misconfigured deploy fails loudly at load time
instead of surfacing a bare KeyError."
```

---

### Task 4: Parse the `[[company]]` list with the `schema` -> `schema_name` alias

**Files:**
- modify `libs/shepherd_config/shepherd_config/loader.py`
- modify `libs/shepherd_config/shepherd_config/__init__.py`
- test `libs/shepherd_config/tests/test_loader.py`

**Interfaces:**
- Produces: `CompanyConfig(slug: str, schema_name: str = Field(alias="schema"))`, `Config.companies: list[CompanyConfig] = []`.
- Note: the TOML array key is `[[company]]` (matching the spec and `deploy/config.example.toml`), aliased onto the `Config.companies` field; the per-entry key is `schema` (mapped to `schema_name` via alias).

Steps:

- [ ] **Step 1 - Write the failing test.** Append to `libs/shepherd_config/tests/test_loader.py`:
```python
def test_parses_companies_with_schema_alias(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        '[database]\n'
        'url = "postgresql://u:p@db/s"\n'
        '\n'
        '[services]\n'
        'fleet_api_url = "http://fleet-api:8000"\n'
        '\n'
        '[[company]]\n'
        'slug = "default"\n'
        'schema = "co_default"\n'
        '\n'
        '[[company]]\n'
        'slug = "bigcorp-b"\n'
        'schema = "co_bigcorp"\n'
    )
    monkeypatch.setenv("SHEPHERD_CONFIG", str(cfg_file))
    get_config.cache_clear()
    cfg = get_config()
    assert [c.slug for c in cfg.companies] == ["default", "bigcorp-b"]
    assert cfg.companies[0].schema_name == "co_default"
    assert cfg.companies[1].schema_name == "co_bigcorp"
```

- [ ] **Step 2 - Run it, expect FAIL.** `cd libs/shepherd_config && poetry run pytest tests/test_loader.py::test_parses_companies_with_schema_alias -q`
  Expected: `AttributeError: 'Config' object has no attribute 'companies'` (the field does not exist yet).

- [ ] **Step 3 - Minimal implementation.** Edit `libs/shepherd_config/shepherd_config/loader.py`. Change the pydantic import and add the model + field:
```python
from pydantic import BaseModel, ConfigDict, Field
```
  Add the `CompanyConfig` model (above `Config`):
```python
class CompanyConfig(BaseModel):
    slug: str
    schema_name: str = Field(alias="schema")  # TOML key is "schema"; attr is schema_name
```
  Add the field to `Config`. The TOML array key is `[[company]]` (singular, per the spec),
  so the `companies` field reads from the `company` alias; `populate_by_name` keeps the
  attribute name usable too:
```python
class Config(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    database: DatabaseConfig
    services: ServicesConfig
    companies: list[CompanyConfig] = Field(default=[], alias="company")
```
  Update `libs/shepherd_config/shepherd_config/__init__.py`:
```python
"""Central config package for Shepherd services."""
from .loader import (
    CompanyConfig,
    Config,
    DatabaseConfig,
    ServicesConfig,
    get_config,
)

__all__ = [
    "CompanyConfig",
    "Config",
    "DatabaseConfig",
    "ServicesConfig",
    "get_config",
]
```

- [ ] **Step 4 - Run it, expect PASS.** `cd libs/shepherd_config && poetry run pytest tests/test_loader.py -q` -> 4 passed.

- [ ] **Step 5 - Commit.**
```
git add libs/shepherd_config/shepherd_config/loader.py libs/shepherd_config/shepherd_config/__init__.py libs/shepherd_config/tests/test_loader.py
git commit -m "parse companies list in shepherd_config config

Add CompanyConfig (slug + schema_name aliased from the TOML \"schema\"
key) and the Config.companies list so the central config carries the
many-to-one company to schema map."
```

---

### Task 5: Commit `config.example.toml`, gitignore `config.toml`, document `SHEPHERD_CONFIG`

**Files:**
- create `config.example.toml` (repo root)
- modify `.gitignore`
- modify `.env.example`
- test `libs/shepherd_config/tests/test_example_config.py`

**Interfaces:**
- Produces: a committed, loadable config template at the repo root.
- Consumes: `get_config()` against `config.example.toml` with `DATABASE_URL` / `FLEET_API_URL` set.

Steps:

- [ ] **Step 1 - Write the failing test.** Create `libs/shepherd_config/tests/test_example_config.py`:
```python
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
```

- [ ] **Step 2 - Run it, expect FAIL.** `cd libs/shepherd_config && poetry run pytest tests/test_example_config.py -q`
  Expected: `FileNotFoundError: [Errno 2] No such file or directory: '.../config.example.toml'` (the file does not exist yet).

- [ ] **Step 3 - Minimal implementation.** Create `config.example.toml` at the repo root:
```toml
# Shepherd central config (committed template).
# Copy to config.toml (gitignored) and resolve secrets via the environment.
# Secret values use ${VAR} and resolve from the process environment at load time.
[database]
url = "${DATABASE_URL}"            # postgresql+psycopg://...
shared_schema = "public"          # where control-plane tables live

[services]
fleet_api_url = "${FLEET_API_URL}"

# Seeded companies: the schema name is opaque data, never derived from a format.
# The map is many-to-one: several companies may share one schema (subcompanies).
[[company]]
slug = "default"
schema = "co_default"

[[company]]
slug = "internal"                 # playground / sandbox
schema = "co_internal"
```

  Edit `.gitignore`, adding under the `# Env / secrets` block:
```
# Central config: real file is local-only; the committed template is config.example.toml
config.toml
```

  Edit `.env.example`, adding near the top (after the Postgres block):
```
# Central config file (shepherd_config). Path to the structured config.toml that holds the
# DB connection string and the company->schema map. Defaults to ./config.toml at the repo
# root (containers mount it at /etc/shepherd/config.toml). Secrets stay here as ${VAR} refs.
SHEPHERD_CONFIG=config.toml
```

- [ ] **Step 4 - Run it, expect PASS.** `cd libs/shepherd_config && poetry run pytest tests/test_example_config.py -q` -> 1 passed.

- [ ] **Step 5 - Commit.**
```
git add config.example.toml .gitignore .env.example libs/shepherd_config/tests/test_example_config.py
git commit -m "add config.example.toml and SHEPHERD_CONFIG env

Commit a loadable central-config template at the repo root, gitignore the
real config.toml, and document the SHEPHERD_CONFIG path variable in
.env.example."
```

---

### Task 6: Source the fleet-api DB url from `shepherd_config`

**Files:**
- modify `services/fleet-api/pyproject.toml`
- modify `services/fleet-api/app/deps.py`
- test `services/fleet-api/tests/test_config_url.py`

**Interfaces:**
- Consumes: `shepherd_config.get_config().database.url`.
- Produces: `app.deps.get_engine()` builds its engine from the config url instead of `os.environ["DATABASE_URL"]`.

Steps:

- [x] **Step 1 - Write the failing test.** Create `services/fleet-api/tests/test_config_url.py`:
```python
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
```

- [x] **Step 2 - Run it, expect FAIL.** `cd services/fleet-api && poetry run pytest tests/test_config_url.py -q`
  Expected: `ModuleNotFoundError: No module named 'shepherd_config'` (the path dep is not installed yet).

- [x] **Step 3 - Minimal implementation.** Add the path dep to `services/fleet-api/pyproject.toml` under `[tool.poetry.dependencies]`, after the `shepherd-db` line:
```toml
shepherd-config = { path = "../../libs/shepherd_config", develop = true }
```
  Install it: `cd services/fleet-api && poetry lock && poetry install`.

  Edit `services/fleet-api/app/deps.py`. Add the import near the other imports:
```python
from shepherd_config import get_config
```
  Change `get_engine` to read the config url:
```python
def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_config().database.url
        _engine = create_engine(url)
    return _engine
```

- [x] **Step 4 - Run it, expect PASS.** `cd services/fleet-api && poetry run pytest tests/test_config_url.py -q` -> 1 passed.

- [x] **Step 5 - Commit.**
```
git add services/fleet-api/pyproject.toml services/fleet-api/poetry.lock services/fleet-api/app/deps.py services/fleet-api/tests/test_config_url.py
git commit -m "source fleet-api db url from shepherd_config

Take shepherd-config as a path dependency and build the SQLAlchemy engine
from get_config().database.url instead of reading os.environ DATABASE_URL
directly, so the DB connection has a single source of truth."
```

---

### Task 7: Source the telegram-bot DB url and fleet-api url from `shepherd_config`

**Files:**
- modify `services/telegram-bot/pyproject.toml`
- modify `services/telegram-bot/app/config.py`
- test `services/telegram-bot/tests/test_config_source.py`

**Interfaces:**
- Consumes: `shepherd_config.get_config().database.url` and `.services.fleet_api_url`.
- Produces: `app.config.settings.database_url` / `.fleet_api_url` overlaid from the central config when present (env defaults kept when no `config.toml` exists). Bot-only env (token, model keys, internal token) is unchanged.

Steps:

- [ ] **Step 1 - Write the failing test.** Create `services/telegram-bot/tests/test_config_source.py`:
```python
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
```

- [ ] **Step 2 - Run it, expect FAIL.** `cd services/telegram-bot && poetry run pytest tests/test_config_source.py -q`
  Expected: `ModuleNotFoundError: No module named 'shepherd_config'` (the path dep is not installed yet).

- [ ] **Step 3 - Minimal implementation.** Add the path dep to `services/telegram-bot/pyproject.toml` under `[tool.poetry.dependencies]`, after the `pydantic-settings` line:
```toml
shepherd-config = { path = "../../libs/shepherd_config", develop = true }
```
  Install it: `cd services/telegram-bot && poetry lock && poetry install`.

  Edit `services/telegram-bot/app/config.py`. Add the import:
```python
from shepherd_config import get_config
```
  Replace the trailing `settings = Settings()` with:
```python
settings = Settings()

try:
    _cfg = get_config()
except FileNotFoundError:
    _cfg = None  # ponytail: no config.toml in some envs (unit tests) -> keep env defaults
if _cfg is not None:
    settings.database_url = _cfg.database.url
    settings.fleet_api_url = _cfg.services.fleet_api_url
```

- [ ] **Step 4 - Run it, expect PASS.** `cd services/telegram-bot && poetry run pytest tests/test_config_source.py -q` -> 1 passed.

- [ ] **Step 5 - Commit.**
```
git add services/telegram-bot/pyproject.toml services/telegram-bot/poetry.lock services/telegram-bot/app/config.py services/telegram-bot/tests/test_config_source.py
git commit -m "source telegram-bot db and fleet url from config

Take shepherd-config as a path dependency and overlay database_url and
fleet_api_url from the central config when a config.toml is present,
keeping bot-only env (token, model keys) and env defaults intact."
```

---

### Task 8: Add the `schema_name` column to `company_settings`

**Files:**
- modify `db/shepherd_db/models.py`
- test `db/tests/test_company_settings_schema.py`

**Interfaces:**
- Produces: `CompanySettings.schema_name = mapped_column(Text, nullable=False)`.
- Note: seeding/provisioning of the value is OUT OF SCOPE - owned by the schema-per-tenant plan. This task adds the column only.

Steps:

- [ ] **Step 1 - Write the failing test.** Create `db/tests/test_company_settings_schema.py`:
```python
from shepherd_db.models import CompanySettings


def test_company_settings_has_schema_name_column():
    col = CompanySettings.__table__.columns["schema_name"]
    assert col.nullable is False
```

- [ ] **Step 2 - Run it, expect FAIL.** `cd db && poetry run pytest tests/test_company_settings_schema.py -q`
  Expected: `KeyError: 'schema_name'` (the column does not exist yet).

- [ ] **Step 3 - Minimal implementation.** Edit `db/shepherd_db/models.py` in `class CompanySettings`, adding the column after `gdrive_credentials_json`:
```python
    schema_name = mapped_column(Text, nullable=False)  # opaque per-tenant schema; seeded by the schema-per-tenant plan
```

- [ ] **Step 4 - Run it, expect PASS.** `cd db && poetry run pytest tests/test_company_settings_schema.py -q` -> 1 passed.

- [ ] **Step 5 - Commit.**
```
git add db/shepherd_db/models.py db/tests/test_company_settings_schema.py
git commit -m "add schema_name column to company_settings

Add the NOT NULL schema_name column that holds each company's opaque
tenant-schema name (the runtime source of truth). Seeding and
provisioning of the value are owned by the schema-per-tenant plan."
```

---

### Task 9: Expose `schema_name` in the `CompanySettingsRead` contract

**Files:**
- modify `services/fleet-api/app/schemas.py`
- modify `services/fleet-api/app/routers/companies.py`
- test `services/fleet-api/tests/test_settings_read_schema.py`

**Interfaces:**
- Produces: `CompanySettingsRead.schema_name: str | None = None`, populated by `_settings_read`.
- Note: only the read contract gains the field. `CompanySettingsUpdate` is unchanged because the value is provisioning-owned, not user-editable.

Steps:

- [x] **Step 1 - Write the failing test.** Create `services/fleet-api/tests/test_settings_read_schema.py`:
```python
from types import SimpleNamespace
from uuid import uuid4

from app.routers.companies import _settings_read


def test_settings_read_exposes_schema_name():
    s = SimpleNamespace(
        gdrive_folder_id=None,
        gdrive_credentials_json=None,
        feature_flags={},
        schema_name="co_acme",
    )
    out = _settings_read(uuid4(), s)
    assert out.schema_name == "co_acme"
```

- [x] **Step 2 - Run it, expect FAIL.** `cd services/fleet-api && poetry run pytest tests/test_settings_read_schema.py -q`
  Expected: `AttributeError: 'CompanySettingsRead' object has no attribute 'schema_name'` (the field does not exist yet).

- [x] **Step 3 - Minimal implementation.** Edit `services/fleet-api/app/schemas.py`, adding the field to `CompanySettingsRead`:
```python
class CompanySettingsRead(BaseModel):
    company_id: UUID
    gdrive_folder_id: str | None = None
    # The raw credentials blob is a secret and is never returned - only whether it's set.
    gdrive_configured: bool
    feature_flags: dict = {}
    schema_name: str | None = None
```
  Edit `services/fleet-api/app/routers/companies.py`, populating it in `_settings_read`:
```python
def _settings_read(company_id: UUID, s) -> CompanySettingsRead:
    return CompanySettingsRead(
        company_id=company_id,
        gdrive_folder_id=s.gdrive_folder_id if s else None,
        gdrive_configured=bool(s and s.gdrive_credentials_json),
        feature_flags=(s.feature_flags if s and s.feature_flags else {}),
        schema_name=(s.schema_name if s else None),
    )
```

- [x] **Step 4 - Run it, expect PASS.** `cd services/fleet-api && poetry run pytest tests/test_settings_read_schema.py -q` -> 1 passed.

- [x] **Step 5 - Commit.**
```
git add services/fleet-api/app/schemas.py services/fleet-api/app/routers/companies.py services/fleet-api/tests/test_settings_read_schema.py
git commit -m "expose schema_name in CompanySettingsRead

Surface the per-company schema_name as a read-only field on the settings
read contract. The update contract is left untouched because the value is
provisioning-owned, not user-editable."
```
