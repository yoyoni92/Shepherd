"""Gemini vision document extractor (fallback provider)."""
from __future__ import annotations

import json
import os

import boto3
from google import genai
from google.genai import types as genai_types

from shepherd_contracts import DocType, DocumentExtractor, ExtractionResult
from app.base import ExtractionError
from app.prompt import build_prompt, FIELD_KEYS


def _s3_download(s3_key: str) -> bytes:
    bucket = os.environ.get("S3_BUCKET", "shepherd-fleet")
    s3 = boto3.client("s3")
    return s3.get_object(Bucket=bucket, Key=s3_key)["Body"].read()


class GeminiExtractor(DocumentExtractor):
    def __init__(self, model=None) -> None:
        self._model = model  # injected in tests; None triggers lazy init

    def _get_model(self):
        if self._model is None:
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY env var is required")
            client = genai.Client(api_key=api_key)
            self._model = client.models
        return self._model

    def extract(self, s3_key: str, doc_type: DocType) -> ExtractionResult:
        raw_bytes = _s3_download(s3_key)
        ext = s3_key.rsplit(".", 1)[-1].lower()
        mime = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }.get(ext, "application/pdf")

        prompt = build_prompt(doc_type)
        response = self._get_model().generate_content(
            model="gemini-2.0-flash",
            contents=[
                genai_types.Part.from_bytes(data=raw_bytes, mime_type=mime),
                prompt,
            ],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        text = response.text

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ExtractionError("Model returned non-JSON output", reason="parse_error") from exc

        if "fields" not in parsed or "confidence" not in parsed:
            raise ExtractionError("Missing required keys in model output", reason="schema_error")

        fields = {k: parsed["fields"].get(k) for k in FIELD_KEYS.get(doc_type, [])}
        return ExtractionResult(
            doc_type=doc_type,
            fields=fields,
            confidence=float(parsed["confidence"]),
            raw=parsed.get("raw"),
        )
