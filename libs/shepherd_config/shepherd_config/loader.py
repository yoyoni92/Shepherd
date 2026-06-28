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
