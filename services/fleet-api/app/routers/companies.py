from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import drive, repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import (
    CompanyCreate,
    CompanyRead,
    CompanySettingsRead,
    CompanySettingsUpdate,
    CompanyUpdate,
)

router = APIRouter(prefix="/companies", tags=["companies"])


def _to_read(c) -> CompanyRead:
    return CompanyRead(
        company_id=c.company_id,
        name=c.name,
        is_active=c.is_active,
        created_at=c.created_at,
    )


def _settings_read(company_id: UUID, s) -> CompanySettingsRead:
    return CompanySettingsRead(
        company_id=company_id,
        gdrive_folder_id=s.gdrive_folder_id if s else None,
        gdrive_configured=bool(s and s.gdrive_credentials_json),
        feature_flags=(s.feature_flags if s and s.feature_flags else {}),
    )


@router.get(
    "",
    response_model=list[CompanyRead],
    summary="List companies (system-admin only)",
)
def list_companies(session: Db, caller: Caller) -> list[CompanyRead]:
    assert_permitted(caller.role, Action.MANAGE_COMPANIES)
    return [_to_read(c) for c in repo.list_companies(session)]


@router.post(
    "",
    response_model=CompanyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create company (system-admin only)",
)
def create_company(body: CompanyCreate, session: Db, caller: Caller) -> CompanyRead:
    assert_permitted(caller.role, Action.MANAGE_COMPANIES)
    return _to_read(repo.create_company(session, body.model_dump()))


@router.patch(
    "/{company_id}",
    response_model=CompanyRead,
    summary="Update company (system-admin only)",
    description="Partial update - only provided fields are written.",
)
def update_company(
    company_id: UUID, body: CompanyUpdate, session: Db, caller: Caller
) -> CompanyRead:
    assert_permitted(caller.role, Action.MANAGE_COMPANIES)
    company = repo.update_company(session, company_id, body.model_dump(exclude_unset=True))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return _to_read(company)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete company (system-admin only)",
)
def delete_company(company_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_COMPANIES)
    if not repo.delete_company(session, company_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")


# --- Per-company settings (Drive + feature flags) ---


@router.get(
    "/{company_id}/settings",
    response_model=CompanySettingsRead,
    summary="Read a company's settings (system-admin only)",
    description="Returns Drive config (credentials redacted to gdrive_configured) + feature flags.",
)
def get_company_settings(company_id: UUID, session: Db, caller: Caller) -> CompanySettingsRead:
    assert_permitted(caller.role, Action.MANAGE_COMPANIES)
    if repo.get_company(session, company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return _settings_read(company_id, repo.get_company_settings(session, company_id))


@router.patch(
    "/{company_id}/settings",
    response_model=CompanySettingsRead,
    summary="Update a company's settings (system-admin only)",
    description=(
        "Validate-then-persist: when Drive credentials and/or folder are set, the "
        "service account + folder are checked against Google first; on failure the "
        "call returns 400 with a specific message and nothing is stored. feature_flags "
        "are merged into the existing flags (other flags are preserved)."
    ),
)
def update_company_settings(
    company_id: UUID, body: CompanySettingsUpdate, session: Db, caller: Caller
) -> CompanySettingsRead:
    assert_permitted(caller.role, Action.MANAGE_COMPANIES)
    if repo.get_company(session, company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    existing = repo.get_company_settings(session, company_id)

    # Effective Drive config after applying this patch (fall back to what's stored).
    new_folder = (
        body.gdrive_folder_id
        if body.gdrive_folder_id is not None
        else (existing.gdrive_folder_id if existing else None)
    )
    new_creds = (
        body.gdrive_credentials_json
        if body.gdrive_credentials_json is not None
        else (existing.gdrive_credentials_json if existing else None)
    )

    # Validate whenever the Drive config is being touched; a partial config can't be validated.
    if body.gdrive_credentials_json is not None or body.gdrive_folder_id is not None:
        if not (new_creds and new_folder):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both a Drive folder id and credentials are required.",
            )
        ok, message = drive.validate_credentials(new_creds, new_folder)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    kwargs: dict = {}
    if body.gdrive_folder_id is not None:
        kwargs["gdrive_folder_id"] = body.gdrive_folder_id
    if body.gdrive_credentials_json is not None:
        kwargs["gdrive_credentials_json"] = body.gdrive_credentials_json
    if body.feature_flags is not None:
        merged = dict(existing.feature_flags) if existing and existing.feature_flags else {}
        merged.update(body.feature_flags)
        kwargs["feature_flags"] = merged

    s = repo.upsert_company_settings(session, company_id, **kwargs)
    return _settings_read(company_id, s)
