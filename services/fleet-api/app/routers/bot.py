import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db, verify_internal_token
from app.schemas import (
    BotInviteClaimRequest,
    BotInviteClaimResponse,
    BotInviteCreate,
    BotInviteRead,
    BotInviteResponse,
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
    user = repo.get_bot_user_by_chat_id(session, chat_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown")
    return BotWhoamiResponse(
        role=user.role.value,
        driver_id=user.driver_id,
        driver_name=user.driver.full_name if user.driver else None,
        user_id=user.id,
    )


@router.post(
    "/bot-invite",
    response_model=BotInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue an invite token for a driver (admin only)",
)
def create_invite(body: BotInviteCreate, session: Db, caller: Caller) -> BotInviteResponse:
    assert_permitted(caller.role, Action.MANAGE_BOT_INVITES)
    if body.role not in ("admin", "driver"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    # Driver invites must name a driver; admin invites may be standalone (no driver).
    if body.role == "driver" and body.driver_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="driver_id required for a driver invite")
    if body.driver_id is not None and repo.get_driver(session, body.driver_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    token_str = str(uuid.uuid4())
    invite = repo.create_bot_invite(session, body.driver_id, token_str, body.role, body.phone_number)
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "ShepherdBot")
    return BotInviteResponse(
        token=invite.token,
        deep_link=f"https://t.me/{bot_username}?start={invite.token}",
        expires_at=invite.expires_at,
    )


@router.post(
    "/bot-invite/claim",
    response_model=BotInviteClaimResponse,
    dependencies=[Depends(verify_internal_token)],
    summary="Claim an invite token and link a telegram user",
)
def claim_invite(body: BotInviteClaimRequest, session: Db) -> BotInviteClaimResponse:
    result = repo.claim_bot_invite(session, body.token, body.telegram_chat_id, body.phone_number)
    if result == "phone_mismatch":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="phone_mismatch")
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return BotInviteClaimResponse(driver_id=result.driver_id, role=result.role.value, user_id=result.id)


@router.get(
    "/bot-invite",
    response_model=list[BotInviteRead],
    summary="List pending bot invites (admin only)",
)
def list_invites(session: Db, caller: Caller) -> list[BotInviteRead]:
    assert_permitted(caller.role, Action.MANAGE_BOT_INVITES)
    return [
        BotInviteRead(
            token=inv.token,
            driver_id=inv.driver_id,
            driver_name=inv.driver.full_name if inv.driver else None,
            role=inv.role.value if hasattr(inv.role, "value") else inv.role,
            phone_number=inv.phone_number,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in repo.list_pending_bot_invites(session)
    ]


@router.delete(
    "/bot-invite/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a pending invite (admin only)",
)
def revoke_invite(token: str, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_BOT_INVITES)
    result = repo.revoke_bot_invite(session, token)
    if result == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    if result == "already_used":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already used")


@router.get(
    "/users",
    response_model=list[BotUserRead],
    summary="List bot users (admin only)",
)
def list_users(session: Db, caller: Caller, role: str | None = None) -> list[BotUserRead]:
    assert_permitted(caller.role, Action.MANAGE_BOT_USERS)
    if role is not None and role not in ("admin", "driver"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    return [
        BotUserRead(
            user_id=u.id,
            telegram_chat_id=u.telegram_chat_id,
            role=u.role.value,
            driver_id=u.driver_id,
            driver_name=u.driver.full_name if u.driver else None,
            created_at=u.created_at,
        )
        for u in repo.list_bot_users(session, role)
    ]


@router.patch(
    "/users/{user_id}/role",
    response_model=BotUserRead,
    summary="Update a bot user's role (admin only)",
)
def update_user_role(user_id: UUID, body: UserRolePatch, session: Db, caller: Caller) -> BotUserRead:
    assert_permitted(caller.role, Action.MANAGE_BOT_USERS)
    user = repo.update_bot_user_role(session, user_id, body.role)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return BotUserRead(
        user_id=user.id,
        telegram_chat_id=user.telegram_chat_id,
        role=user.role.value,
        driver_id=user.driver_id,
        driver_name=user.driver.full_name if user.driver else None,
        created_at=user.created_at,
    )
