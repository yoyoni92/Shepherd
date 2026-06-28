"""Central config loader: read config.toml, build a typed Config."""
from __future__ import annotations

import functools
import os
import re
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


_VAR = re.compile(r"\$\{([^}]+)\}")


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


def _walk(node):
    if isinstance(node, str):
        return _interpolate(node)
    if isinstance(node, dict):
        return {k: _walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v) for v in node]
    return node


def _config_path() -> Path:
    return Path(os.environ.get("SHEPHERD_CONFIG", "config.toml"))


@functools.lru_cache
def get_config() -> Config:
    with _config_path().open("rb") as fh:
        raw = tomllib.load(fh)
    return Config.model_validate(_walk(raw))
