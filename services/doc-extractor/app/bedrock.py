"""Bedrock (Claude vision) document extractor."""
from __future__ import annotations

import base64
import json
import os

import boto3

from shepherd_contracts import DocType, DocumentExtractor, ExtractionResult
from app.base import ExtractionError
from app.prompt import build_prompt, FIELD_KEYS


def _model_id() -> str:
    mid = os.environ.get("BEDROCK_MODEL_ID", "")
    if not mid:
        raise RuntimeError("BEDROCK_MODEL_ID env var is required")
    return mid


def _s3_download(s3_key: str) -> tuple[bytes, str]:
    """Return (raw_bytes, media_type). Infers media type from key extension."""
    bucket = os.environ.get("S3_BUCKET", "shepherd-fleet")
    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name=region)
    obj = s3.get_object(Bucket=bucket, Key=s3_key)
    data = obj["Body"].read()
    ext = s3_key.rsplit(".", 1)[-1].lower()
    media_type = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get(ext, "application/pdf")
    return data, media_type


def _build_content(raw: bytes, media_type: str, prompt: str) -> list[dict]:
    b64 = base64.standard_b64encode(raw).decode()
    if media_type == "application/pdf":
        doc_block: dict = {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        }
    else:
        doc_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        }
    return [doc_block, {"type": "text", "text": prompt}]


class BedrockExtractor(DocumentExtractor):
    def __init__(self, client=None) -> None:
        self._client = client  # injected in tests; lazy-init otherwise

    def _bedrock(self):
        if self._client is None:
            region = os.environ.get("BEDROCK_REGION", "us-east-1")
            self._client = boto3.client("bedrock-runtime", region_name=region)
        return self._client

    def extract(self, s3_key: str, doc_type: DocType) -> ExtractionResult:
        raw_bytes, media_type = _s3_download(s3_key)
        prompt = build_prompt(doc_type)
        content = _build_content(raw_bytes, media_type, prompt)

        response = self._bedrock().invoke_model(
            modelId=_model_id(),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": content}],
            }),
            contentType="application/json",
            accept="application/json",
        )
        body = json.loads(response["body"].read())
        text = body["content"][0]["text"]

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
