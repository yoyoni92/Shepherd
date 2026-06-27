from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app import drive, repo
from app.deps import Caller, Db

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "",
    summary="Upload a file to the caller's company Google Drive (internal callers only)",
    description=(
        "Stores the uploaded bytes in the calling company's Shared Drive folder, shares "
        "them 'anyone with the link can view', and returns the public file_url. The "
        "company is resolved from X-Caller-Context; its Drive must be configured first "
        "(POST is rejected with 400 otherwise). Called by the Telegram bot and the web UI."
    ),
)
async def upload_file(
    session: Db,
    caller: Caller,
    file: UploadFile = File(...),
    key: str = Form(...),
) -> dict:
    if not caller.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Caller has no company"
        )
    settings = repo.get_company_settings(session, UUID(caller.company_id))
    if settings is None or not settings.gdrive_credentials_json or not settings.gdrive_folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Drive not configured for this company",
        )
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    url = drive.upload(
        key,
        data,
        content_type,
        credentials_json=settings.gdrive_credentials_json,
        folder_id=settings.gdrive_folder_id,
    )
    return {"file_url": url}
