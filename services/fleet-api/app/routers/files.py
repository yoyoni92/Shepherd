from fastapi import APIRouter, Depends, File, Form, UploadFile

from app import drive
from app.deps import verify_internal_token

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "",
    summary="Upload a file to Google Drive (internal callers only)",
    description=(
        "Stores the uploaded bytes in the Shared Drive folder, shares them "
        "'anyone with the link can view', and returns the public file_url. "
        "Called by the Telegram bot and the web UI in place of direct object storage."
    ),
    dependencies=[Depends(verify_internal_token)],
)
async def upload_file(file: UploadFile = File(...), key: str = Form(...)) -> dict:
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    url = drive.upload(key, data, content_type)
    return {"file_url": url}
