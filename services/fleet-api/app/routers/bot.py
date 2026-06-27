from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app import repo
from app.auth import Action, assert_company, assert_permitted
from app.deps import Caller, Db, verify_internal_token
from app.schemas import (
    BotAuthorizationCreate,
    BotAuthorizationRead,
    BotEnrollRequest,
    BotEnrollResponse,
    BotUserRead,
    BotWhoamiResponse,
    UserRolePatch,
)

router = APIRouter(tags=["bot"])


@router.get(
    "/whoami",
    response_model=BotWhoamiResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Resolve telegram chat_id to a bot user",
)
def whoami(chat_id: int, session: Db) -> BotWhoamiResponse:
    # System-admin path wins: the operator is an app_user linked by telegram_chat_id,
    # not a tenant bot user. Returns a company-less admin context.
    operator = repo.get_app_user_by_telegram_chat_id(session, chat_id)
    if operator is not None and operator.is_system_admin:
        playground = repo.get_internal_company(session)
        return BotWhoamiResponse(
            role="admin",
            company_id=None,
            is_system_admin=True,
            user_id=operator.id,
            playground_company_id=playground.company_id if playground else None,
        )
    user = repo.get_bot_user_by_chat_id(session, chat_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown")
    # A temporary role that has lapsed, or a driver who's been deactivated, loses
    # access immediately (defence-in-depth ahead of the pg_cron sweep).
    if user.expires_at is not None and user.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown")
    if user.driver is not None and user.driver.status.value != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown")
    attendance_enabled = (
        repo.company_feature_enabled(session, user.company_id, "attendance")
        if user.company_id
        else False
    )
    return BotWhoamiResponse(
        role=user.role.value,
        driver_id=user.driver_id,
        driver_name=user.driver.full_name if user.driver else None,
        user_id=user.id,
        company_id=user.company_id,
        attendance_enabled=attendance_enabled,
    )


@router.post(
    "/bot-enroll",
    response_model=BotEnrollResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Enroll a telegram user by matching their phone to a driver/authorization",
)
def enroll(body: BotEnrollRequest, session: Db) -> BotEnrollResponse:
    # System-admin precedence: a phone matching an is_system_admin app_user links the
    # operator's telegram_chat_id (no tenant bot user is created).
    operator = repo.get_system_app_user_by_phone(session, body.phone_number)
    if operator is not None:
        repo.link_app_user_telegram(session, operator, body.telegram_chat_id)
        return BotEnrollResponse(
            role="admin", user_id=operator.id, is_system_admin=True
        )
    user = repo.enroll_bot_user(session, body.telegram_chat_id, body.phone_number)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_authorized")
    return BotEnrollResponse(
        role=user.role.value,
        driver_id=user.driver_id,
        driver_name=user.driver.full_name if user.driver else None,
        user_id=user.id,
        expires_at=user.expires_at,
    )


def _authz_read(a) -> BotAuthorizationRead:
    return BotAuthorizationRead(
        id=a.id,
        phone_number=a.phone_number,
        role=a.role.value if hasattr(a.role, "value") else a.role,
        driver_id=a.driver_id,
        driver_name=a.driver.full_name if a.driver else None,
        expires_at=a.expires_at,
        created_at=a.created_at,
    )


@router.post(
    "/bot-authorizations",
    response_model=BotAuthorizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Authorize a phone for bot access (admin only)",
)
def create_authorization(body: BotAuthorizationCreate, session: Db, caller: Caller) -> BotAuthorizationRead:
    assert_permitted(caller.role, Action.MANAGE_BOT_INVITES)
    if body.role not in ("admin", "driver"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if body.driver_id is not None and repo.get_driver(session, body.driver_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    company_id = UUID(caller.company_id) if caller.company_id else None
    auth = repo.create_bot_authorization(
        session, body.phone_number, body.role, body.driver_id, body.expires_at,
        company_id=company_id,
    )
    return _authz_read(auth)


@router.get(
    "/bot-authorizations",
    response_model=list[BotAuthorizationRead],
    summary="List active bot authorizations (admin only)",
)
def list_authorizations(session: Db, caller: Caller) -> list[BotAuthorizationRead]:
    assert_permitted(caller.role, Action.MANAGE_BOT_INVITES)
    company_id = UUID(caller.company_id) if caller.company_id else None
    return [_authz_read(a) for a in repo.list_bot_authorizations(session, company_id=company_id)]


@router.delete(
    "/bot-authorizations/{auth_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a bot authorization (admin only)",
)
def delete_authorization(auth_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_BOT_INVITES)
    auth = repo.get_bot_authorization(session, auth_id)
    if auth is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authorization not found")
    assert_company(auth, caller)
    repo.delete_bot_authorization(session, auth_id)


def _user_read(u) -> BotUserRead:
    return BotUserRead(
        user_id=u.id,
        telegram_chat_id=u.telegram_chat_id,
        role=u.role.value,
        phone_number=u.phone_number or (u.driver.phone_number if u.driver else None),
        driver_id=u.driver_id,
        driver_name=u.driver.full_name if u.driver else None,
        expires_at=u.expires_at,
        created_at=u.created_at,
    )


@router.get(
    "/users",
    response_model=list[BotUserRead],
    summary="List bot users (admin only)",
)
def list_users(session: Db, caller: Caller, role: str | None = None) -> list[BotUserRead]:
    assert_permitted(caller.role, Action.MANAGE_BOT_USERS)
    if role is not None and role not in ("admin", "driver"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    company_id = UUID(caller.company_id) if caller.company_id else None
    return [_user_read(u) for u in repo.list_bot_users(session, role, company_id=company_id)]


@router.patch(
    "/users/{user_id}/role",
    response_model=BotUserRead,
    summary="Update a bot user's role (admin only)",
)
def update_user_role(user_id: UUID, body: UserRolePatch, session: Db, caller: Caller) -> BotUserRead:
    assert_permitted(caller.role, Action.MANAGE_BOT_USERS)
    existing = repo.get_bot_user(session, user_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    assert_company(existing, caller)
    user = repo.update_bot_user_role(session, user_id, body.role)
    return _user_read(user)
