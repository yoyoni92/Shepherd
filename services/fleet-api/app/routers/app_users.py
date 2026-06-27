from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import AppUserCreate, AppUserRead, AppUserUpdate

router = APIRouter(prefix="/app-users", tags=["app-users"])


def _to_read(u) -> AppUserRead:
    # NEVER expose password_hash.
    return AppUserRead(
        user_id=u.id,
        email=u.email,
        role=u.role.value if hasattr(u.role, "value") else u.role,
        company_id=u.company_id,
        is_active=u.is_active,
        name=u.name,
        created_at=u.created_at,
    )


@router.get(
    "",
    response_model=list[AppUserRead],
    summary="List app users (system-admin only)",
)
def list_app_users(session: Db, caller: Caller) -> list[AppUserRead]:
    assert_permitted(caller.role, Action.MANAGE_APP_USERS)
    return [_to_read(u) for u in repo.list_app_users(session)]


@router.post(
    "",
    response_model=AppUserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create app user (system-admin only)",
)
def create_app_user(body: AppUserCreate, session: Db, caller: Caller) -> AppUserRead:
    assert_permitted(caller.role, Action.MANAGE_APP_USERS)
    if body.role not in ("admin", "company_admin"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if body.role == "company_admin" and body.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="company_admin requires company_id",
        )
    if body.role == "admin" and body.company_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin must not have a company_id",
        )
    if repo.get_app_user_by_email(session, body.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    return _to_read(repo.create_app_user(session, body.model_dump()))


@router.patch(
    "/{user_id}",
    response_model=AppUserRead,
    summary="Update app user (system-admin only)",
    description="Partial update - reset password, toggle is_active, rename.",
)
def update_app_user(user_id: UUID, body: AppUserUpdate, session: Db, caller: Caller) -> AppUserRead:
    assert_permitted(caller.role, Action.MANAGE_APP_USERS)
    user = repo.update_app_user(session, user_id, body.model_dump(exclude_unset=True))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App user not found")
    return _to_read(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete app user (system-admin only)",
)
def delete_app_user(user_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_APP_USERS)
    if not repo.delete_app_user(session, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App user not found")
