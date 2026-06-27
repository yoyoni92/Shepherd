import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from shepherd_db.security import verify_password

from app import repo
from app.deps import Db, verify_internal_token
from app.schemas import AppUserRead, LoginRequest, LoginResponse
from app.token import encode_jwt

router = APIRouter(prefix="/auth", tags=["auth"])

# Generic message - never reveal whether the email exists, the password was wrong,
# or the account is inactive.
_BAD_CREDENTIALS = "Invalid credentials"
_TOKEN_TTL = timedelta(hours=12)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Authenticate an app user and issue a portable JWT",
    description="Channel-agnostic login (X-Internal-Token only, no caller context).",
)
def login(body: LoginRequest, session: Db) -> LoginResponse:
    user = repo.get_app_user_by_email(session, body.email)
    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS
        )

    role = user.role.value if hasattr(user.role, "value") else user.role
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user.id),
        "role": role,
        "company_id": str(user.company_id) if user.company_id else None,
        "exp": int((now + _TOKEN_TTL).timestamp()),
    }
    token = encode_jwt(claims, os.environ["AUTH_JWT_SECRET"])

    # Surface the company's feature flags so the webui can gate nav without a round-trip
    # (empty for a system admin with no company).
    feature_flags = {}
    if user.company_id:
        settings = repo.get_company_settings(session, user.company_id)
        feature_flags = settings.feature_flags if settings and settings.feature_flags else {}

    return LoginResponse(
        user=AppUserRead(
            user_id=user.id,
            email=user.email,
            role=role,
            company_id=user.company_id,
            is_active=user.is_active,
            name=user.name,
            created_at=user.created_at,
        ),
        token=token,
        feature_flags=feature_flags,
    )
