"""S3 media upload (accident attachments + scanned documents). boto3 is sync -> to_thread."""

from __future__ import annotations

import asyncio

import boto3

from app.config import settings


def _upload_sync(bucket: str, key: str, data: bytes, content_type: str) -> str:
    s3 = boto3.client("s3", region_name=settings.aws_default_region)
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return f"https://{bucket}.s3.{settings.aws_default_region}.amazonaws.com/{key}"


async def upload(
    key: str, data: bytes, content_type: str = "application/octet-stream", bucket: str | None = None
) -> str:
    bucket = bucket or settings.s3_bucket_accidents
    return await asyncio.to_thread(_upload_sync, bucket, key, data, content_type)
