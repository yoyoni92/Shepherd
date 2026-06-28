"""FastAPI dependencies: schema-scoped DB session, internal token guard, caller context."""
import json
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from shepherd_config import get_config
from shepherd_contracts.auth import CallerContext
from shepherd_db.models import CompanySettings
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

_engine: Engine | None = None
# company_id -> schema_name. Schema names are stable data; cache for the process lifetime.
_schema_cache: dict[str, str] = {}


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_config().database.url)
    return _engine


def _resolve_schema(engine: Engine, company_id: str | None) -> str:
    """Look up the company's schema_name (never derived). Shared schema when company-less."""
    shared = get_config().database.shared_schema
    if company_id is None:
        return shared
    if company_id in _schema_cache:
        return _schema_cache[company_id]
    with engine.connect() as conn:
        name = conn.execute(
            select(CompanySettings.schema_name).where(
                CompanySettings.company_id == company_id
            )
        ).scalar_one_or_none()
    # Treat '__pending__' (companies created before provisioning) and NULL/missing
    # the same as company-less: route to the shared schema rather than a nonexistent one.
    schema = name if (name and name != "__pending__") else shared
    _schema_cache[company_id] = schema
    return schema


def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    import os
    expected = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
    if not expected or x_internal_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_caller(
    _: Annotated[None, Depends(verify_internal_token)],
    x_caller_context: Annotated[str, Header(alias="X-Caller-Context")],
) -> CallerContext:
    try:
        return CallerContext.model_validate(json.loads(x_caller_context))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid caller context"
        ) from err


def get_caller_optional(
    x_caller_context: Annotated[str | None, Header(alias="X-Caller-Context")] = None,
) -> CallerContext | None:
    """Caller context when present (whoami / bot-enroll send none)."""
    if x_caller_context is None:
        return None
    try:
        return CallerContext.model_validate(json.loads(x_caller_context))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid caller context"
        ) from err


def get_db(
    engine: Engine = Depends(get_engine),
    caller: CallerContext | None = Depends(get_caller_optional),
) -> Generator[Session, None, None]:
    company_id = caller.company_id if caller else None
    shared = get_config().database.shared_schema
    schema = _resolve_schema(engine, company_id)
    # Fresh connection per request; schema_translate_map is a per-statement compile option,
    # so it cannot leak into another request's pooled connection.
    with engine.connect() as conn:
        conn = conn.execution_options(
            schema_translate_map={"tenant": schema, None: shared}
        )
        with Session(bind=conn) as session:
            yield session


Db = Annotated[Session, Depends(get_db)]
Caller = Annotated[CallerContext, Depends(get_caller)]
