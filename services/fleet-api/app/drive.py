"""Per-company Google Drive storage for uploaded media (accident attachments + scanned documents).

Each company supplies its own service-account credentials + target Shared Drive folder
(stored in ``company_settings``); there is no global fallback. Files land in that folder,
are shared "anyone with the link can view", and the public webViewLink is returned for
storage. The Drive client is sync; fleet-api routers are sync def, so FastAPI runs them in
a threadpool and no asyncio wrapping is needed here.

``_build_service`` is the single indirection point where the Google client is constructed,
so tests can monkeypatch it and avoid any real network call.
"""

from __future__ import annotations

import json
from io import BytesIO

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _build_service(credentials_json: str):
    """Build a Drive v3 client from a service-account JSON blob.

    Single indirection point: tests monkeypatch this so no real Google call happens.
    """
    info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def validate_credentials(credentials_json: str, folder_id: str) -> tuple[bool, str]:
    """Check the credentials authenticate and the target folder is reachable.

    Returns ``(True, "ok")`` on success, or ``(False, <human message>)`` mapping a JSON
    parse error / bad service-account key / inaccessible folder to a specific message.
    """
    try:
        service = _build_service(credentials_json)
    except json.JSONDecodeError:
        return (False, "Credentials are not valid JSON.")
    except (ValueError, KeyError) as exc:
        return (False, f"Invalid service-account credentials: {exc}")
    except Exception as exc:  # noqa: BLE001 - any client-build failure is a config error
        return (False, f"Could not initialize the Drive client: {exc}")

    try:
        service.files().get(
            fileId=folder_id, fields="id,name", supportsAllDrives=True
        ).execute()
    except Exception as exc:  # noqa: BLE001 - auth/permission/missing folder all surface here
        return (False, f"Drive folder not accessible: {exc}")
    return (True, "ok")


def upload(
    key: str,
    data: bytes,
    content_type: str,
    *,
    credentials_json: str,
    folder_id: str,
) -> str:
    """Upload bytes to the company's Shared Drive folder and return a public link.

    ``key`` is used verbatim as the Drive file name so artifacts stay identifiable
    (e.g. ``accidents/{chat}/{cat}.jpg``). Credentials + folder come from the caller's
    company settings - there is no env fallback.
    """
    service = _build_service(credentials_json)
    media = MediaIoBaseUpload(BytesIO(data), mimetype=content_type, resumable=False)
    created = (
        service.files()
        .create(
            body={"name": key, "parents": [folder_id]},
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
