"""Media upload via Fleet API (the sole storage owner). Posts bytes to POST /files,
which stores them in Google Drive and returns the public file_url."""

from __future__ import annotations

import httpx

from app.config import settings


async def upload(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    async with httpx.AsyncClient(base_url=settings.fleet_api_url.rstrip("/"), timeout=60) as client:
        resp = await client.post(
            "/files",
            headers={"X-Internal-Token": settings.internal_service_token},
            data={"key": key},
            files={"file": (key, data, content_type)},
        )
    resp.raise_for_status()
    return resp.json()["file_url"]
