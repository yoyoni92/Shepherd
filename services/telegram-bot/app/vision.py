"""Gemini vision extraction for the admin document-scan flow (cheapest vision model).

Direct call from the bot (the doc-extractor service is retired). Returns a flat dict of
fields; the doc_scan flow maps it onto Fleet API's reconcile/patch endpoints.
"""

from __future__ import annotations

import asyncio
import json

from google import genai
from google.genai import types

from app.config import settings

_MODEL = "gemini-2.0-flash"
_client: genai.Client | None = None

# doc_type -> extraction prompt. Each asks for strict JSON with the named fields.
_PROMPTS = {
    "vehicle_license": (
        "This is an Israeli vehicle annual licensing document (רישיון רכב). "
        'Return ONLY JSON: {"plate_number": string|null, "valid_to": "YYYY-MM-DD"|null}.'
    ),
    "insurance": (
        "This is an Israeli vehicle insurance certificate (תעודת ביטוח). "
        'Return ONLY JSON: {"plate_number": string|null, "valid_to": "YYYY-MM-DD"|null}.'
    ),
    "driver_license": (
        "This is an Israeli driver license (רישיון נהיגה). "
        'Return ONLY JSON: {"license_number": string|null, "valid_to": "YYYY-MM-DD"|null}.'
    ),
}


def _parse(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") : text.rfind("}") + 1]
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return {}


def _get() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _extract_sync(doc_type: str, image: bytes, mime: str) -> dict:
    resp = _get().models.generate_content(
        model=_MODEL,
        contents=[_PROMPTS[doc_type], types.Part.from_bytes(data=image, mime_type=mime)],
    )
    return _parse(resp.text)


async def extract(doc_type: str, image: bytes, mime: str = "image/jpeg") -> dict:
    return await asyncio.to_thread(_extract_sync, doc_type, image, mime)
