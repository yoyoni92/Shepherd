from __future__ import annotations

import os

import boto3
import httpx

from shepherd_contracts import IngestionPayload

_S3_BUCKET = os.getenv("S3_BUCKET", "shepherd-docs")
_N8N_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/ingest")


def put_s3(key: str, body: bytes, content_type: str) -> None:
    boto3.client("s3").put_object(
        Bucket=_S3_BUCKET, Key=key, Body=body, ContentType=content_type
    )


async def forward(payload: IngestionPayload) -> None:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            _N8N_URL,
            content=payload.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
