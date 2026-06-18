"""Fleet API + RAG tool wrappers with caller-context forwarding."""
import json
import os

import httpx

FLEET_API_URL = os.getenv("FLEET_API_URL", "http://fleet-api:8000")
RAG_URL = os.getenv("RAG_URL", "http://rag:8000")
_INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")


def fleet_api_tool(
    path: str,
    method: str = "GET",
    body: dict | None = None,
    *,
    caller_context: dict,
) -> dict:
    """Call Fleet API; surfaces 403 as a refusal dict instead of raising."""
    headers = {
        "X-Internal-Token": _INTERNAL_TOKEN,
        "X-Caller-Context": json.dumps(caller_context),
    }
    with httpx.Client() as client:
        resp = client.request(
            method,
            f"{FLEET_API_URL}{path}",
            headers=headers,
            json=body,
        )
    if resp.status_code == 403:
        return {"error": "forbidden", "detail": "not permitted for this caller"}
    resp.raise_for_status()
    return resp.json()


def rag_tool(question: str, *, caller_context: dict) -> dict:
    """Call RAG service for semantic vehicle-profile queries."""
    with httpx.Client() as client:
        resp = client.post(
            f"{RAG_URL}/query",
            json={"question": question, "caller_context": caller_context},
        )
    resp.raise_for_status()
    return resp.json()
