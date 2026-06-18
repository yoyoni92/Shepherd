"""FastAPI app: POST /analyse - fetch image from S3, run inference."""

import functools
import io
import os
import sys

import boto3
import botocore.exceptions
import PIL.Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Ensure service root is on path so infer/model imports work
_svc_root = os.path.dirname(os.path.dirname(__file__))
if _svc_root not in sys.path:
    sys.path.insert(0, _svc_root)


class AnalyseRequest(BaseModel):
    s3_key: str


class AnalyseResponse(BaseModel):
    doc_type: str
    confidence: float


@functools.lru_cache(maxsize=1)
def _get_model():
    from model import build_model
    from train import load_model

    checkpoint = os.path.join(_svc_root, "artifacts", "model.pth")
    if os.path.exists(checkpoint):
        return load_model(checkpoint)
    model = build_model()
    model.eval()
    return model


app = FastAPI()


@app.post("/analyse", response_model=AnalyseResponse)
def analyse(request: AnalyseRequest):
    from infer import infer

    bucket = os.environ.get("S3_BUCKET", "shepherd-docs")
    threshold = float(os.environ.get("IMAGE_CONFIDENCE_MIN", "0.6"))

    s3 = boto3.client("s3")
    try:
        obj = s3.get_object(Bucket=bucket, Key=request.s3_key)
        body = obj["Body"].read()
    except botocore.exceptions.ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchKey", "404"):
            raise HTTPException(status_code=400, detail=f"S3 key not found: {request.s3_key}")
        raise HTTPException(status_code=400, detail=str(exc))

    image = PIL.Image.open(io.BytesIO(body)).convert("RGB")
    result = infer(image, _get_model(), threshold)
    return AnalyseResponse(**result)
