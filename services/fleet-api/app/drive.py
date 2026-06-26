"""Google Drive storage for uploaded media (accident attachments + scanned documents).

Files land in a Shared Drive folder the service account is a member of, are shared
"anyone with the link can view", and the public webViewLink is returned for storage.
The Drive client is sync; fleet-api routers are sync def, so FastAPI runs them in a
threadpool and no asyncio wrapping is needed here.
"""

from __future__ import annotations

import os
from io import BytesIO

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

_SCOPES = ["https://www.googleapis.com/auth/drive"]
_service = None


def _drive():
    global _service
    if _service is None:
        creds = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=_SCOPES
        )
        _service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _service


def upload(key: str, data: bytes, content_type: str) -> str:
    """Upload bytes to the configured Shared Drive folder and return a public link.

    ``key`` is used verbatim as the Drive file name so artifacts stay identifiable
    (e.g. ``accidents/{chat}/{cat}.jpg``).
    """
    service = _drive()
    media = MediaIoBaseUpload(BytesIO(data), mimetype=content_type, resumable=False)
    created = (
        service.files()
        .create(
            body={"name": key, "parents": [os.environ["GDRIVE_FOLDER_ID"]]},
            media_body=media,
            supportsAllDrives=True,
            fields="id,webViewLink",
        )
        .execute()
    )
    service.permissions().create(
        fileId=created["id"],
        body={"type": "anyone", "role": "reader"},
        supportsAllDrives=True,
    ).execute()
    return created["webViewLink"]
