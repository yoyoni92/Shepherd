"""Media upload via Fleet API (the sole storage owner). Posts bytes to POST /files,
which stores them in the acting company's Google Drive and returns the public file_url.

The caller's company is sent via X-Caller-Context so Fleet API can resolve which
tenant's Drive to store into (per-tenant Drive, no global fallback)."""

from __future__ import annotations

import json

import httpx

from app.config import settings
from app.fleet import admin_ctx


async def upload(
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    company_id: str | None = None,
) -> str:
    headers = {
        "X-Internal-Token": settings.internal_service_token,
        "X-Caller-Context": json.dumps(admin_ctx(company_id)),
    }
    async with httpx.AsyncClient(base_url=settings.fleet_api_url.rstrip("/"), timeout=60) as client:
        resp = await client.post(
            "/files",
            headers=headers,
            data={"key": key},
            files={"file": (key, data, content_type)},
        )
    resp.raise_for_status()
    return resp.json()["file_url"]
