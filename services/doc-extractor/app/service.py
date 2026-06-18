"""FastAPI entry point - callable from n8n or directly."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shepherd_contracts import DocType
from app.base import ExtractionError, get_extractor
from app.reconcile import reconcile

app = FastAPI(title="doc-extractor", version="0.1.0")


class ExtractRequest(BaseModel):
    s3_key: str
    doc_type: DocType
    confidence_min: float = 0.7


class ExtractResponse(BaseModel):
    status: str
    doc_type: str
    confidence: float
    fleet_response: dict | None = None


@app.post("/extract", response_model=ExtractResponse)
def extract_and_reconcile(req: ExtractRequest) -> ExtractResponse:
    extractor = get_extractor()
    try:
        result = extractor.extract(req.s3_key, req.doc_type)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        fleet_resp = reconcile(result, req.s3_key, confidence_min=req.confidence_min)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ExtractResponse(
        status=fleet_resp.get("status", "unknown"),
        doc_type=result.doc_type.value,
        confidence=result.confidence,
        fleet_response=fleet_resp,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
