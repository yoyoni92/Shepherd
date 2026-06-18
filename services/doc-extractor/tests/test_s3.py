"""S3 download path tests using moto."""
import boto3
import pytest
from moto import mock_aws

from app.bedrock import _s3_download


@mock_aws
def test_s3_download_pdf(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")
    s3.put_object(Bucket="test-bucket", Key="docs/ins.pdf", Body=b"pdfdata")
    data, media_type = _s3_download("docs/ins.pdf")
    assert data == b"pdfdata"
    assert media_type == "application/pdf"


@mock_aws
def test_s3_download_png(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")
    s3.put_object(Bucket="test-bucket", Key="docs/photo.png", Body=b"pngdata")
    data, media_type = _s3_download("docs/photo.png")
    assert data == b"pngdata"
    assert media_type == "image/png"


@mock_aws
def test_s3_download_unknown_ext_defaults_to_pdf(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")
    s3.put_object(Bucket="test-bucket", Key="docs/file.docx", Body=b"data")
    _, media_type = _s3_download("docs/file.docx")
    assert media_type == "application/pdf"
