"""Guardrails service FastAPI endpoints."""
import os

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.deterministic import auth, language
from app.guardrails_ai import GuardrailsAIProvider

app = FastAPI(title="Shepherd Guardrails", version="0.1.0")

# ponytail: lazy engine - avoids crashing on import when DATABASE_URL is absent
_SessionLocal = None


def get_db():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=create_engine(os.environ["DATABASE_URL"]))
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ponytail: lazy singleton - hub imports are heavy
_provider = None


def _get_provider() -> GuardrailsAIProvider:
    global _provider
    if _provider is None:
        _provider = GuardrailsAIProvider()
    return _provider


def _get_allowed_languages(db: Session) -> list[str]:
    from shepherd_db.models import SystemConfig

    row = db.query(SystemConfig).filter_by(config_key="allowed_languages").first()
    return row.config_value if row else ["he", "en"]


class InputRequest(BaseModel):
    phone: str
    text: str
    context: dict = {}


class OutputRequest(BaseModel):
    text: str
    sources: list[str] = []


@app.post("/check/input")
def check_input(req: InputRequest, db: Session = Depends(get_db)):
    auth_result = auth(req.phone, db)
    if not auth_result["pass"]:
        return {"pass": False, "reason": auth_result["reason"]}

    allowed = _get_allowed_languages(db)
    lang_result = language(req.text, allowed)
    if not lang_result["pass"]:
        return {"pass": False, "reason": lang_result["reason"]}

    return _get_provider().check_input(req.text, req.context)


@app.post("/check/output")
def check_output(req: OutputRequest):
    return _get_provider().check_output(req.text, req.sources)
