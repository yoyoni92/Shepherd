"""FastAPI dependencies: DB session, internal token guard, caller context."""
import json
import os
from typing import Annotated, Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from shepherd_contracts.auth import CallerContext

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = os.environ["DATABASE_URL"]
        _engine = create_engine(url)
    return _engine


def get_db(engine: Engine = Depends(get_engine)) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    expected = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
    if not expected or x_internal_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_caller(
    _: Annotated[None, Depends(verify_internal_token)],
    x_caller_context: Annotated[str, Header(alias="X-Caller-Context")],
) -> CallerContext:
    try:
        return CallerContext.model_validate(json.loads(x_caller_context))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid caller context")


Db = Annotated[Session, Depends(get_db)]
Caller = Annotated[CallerContext, Depends(get_caller)]
