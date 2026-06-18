"""Deterministic pre-checks: auth and language - no LLM calls."""
from langdetect import DetectorFactory, LangDetectException, detect
from sqlalchemy.orm import Session

from shepherd_db.models import ChannelStatusEnum, Driver, DriverStatusEnum, ChannelIdentity

DetectorFactory.seed = 0  # reproducible detection


def auth(phone: str, db: Session) -> dict:
    """Return {pass, reason, role?} based on channel_identities + drivers lookup."""
    identity = db.query(ChannelIdentity).filter_by(phone_number=phone).first()
    if not identity:
        return {"pass": False, "reason": "not registered"}
    if identity.status == ChannelStatusEnum.revoked:
        return {"pass": False, "reason": "blocked"}
    driver = db.query(Driver).filter_by(phone_number=phone).first()
    role = "driver" if driver and driver.status == DriverStatusEnum.active else "user"
    return {"pass": True, "reason": "ok", "role": role}


def language(text: str, allowed: list[str]) -> dict:
    """Return {pass, reason} based on detected language vs allowed set."""
    try:
        lang = detect(text)
    except LangDetectException:
        return {"pass": False, "reason": "language detection failed"}
    if lang in allowed:
        return {"pass": True, "reason": lang}
    return {"pass": False, "reason": f"language {lang!r} not allowed"}
