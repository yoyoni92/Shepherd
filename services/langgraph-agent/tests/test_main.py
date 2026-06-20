"""T6 - /agent/run endpoint with ownership enforcement end-to-end."""
from contextlib import contextmanager

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app, _get_graph
from app.graph import build_graph
from app.tools import fleet_api_tool, rag_tool

from tests.conftest import (
    ADMIN_CTX,
    DRIVER_CTX,
    make_scripted_planner,
    make_scripted_synthesiser,
)


@contextmanager
def _inject_graph(planner, synthesiser=None):
    """Override the singleton graph with a scripted one for the test."""
    import app.main as main_mod
    main_mod._graph = build_graph(
        planner,
        synthesiser or make_scripted_synthesiser(),
        {"fleet_api": fleet_api_tool, "rag": rag_tool},
    )
    try:
        yield
    finally:
        main_mod._graph = None


@respx.mock
def test_run_returns_typed_response():
    planner = make_scripted_planner({
        "fleet list": [{"tool": "fleet_api", "path": "/vehicles", "method": "GET"}],
    })
    with _inject_graph(planner):
        respx.get("http://fleet-api:8000/vehicles").mock(
            return_value=httpx.Response(200, json=[])
        )
        with TestClient(app) as client:
            resp = client.post("/agent/run", json={
                "query": "fleet list",
                "caller_context": ADMIN_CTX,
            })
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert "tools_used" in body
    assert "reasoning_steps" in body
    assert isinstance(body["tools_used"], list)
    assert isinstance(body["reasoning_steps"], list)


@respx.mock
def test_ownership_enforced_via_fleet_api_403():
    """Driver querying another driver's vehicle gets a 403 surfaced as refusal in the answer."""
    planner = make_scripted_planner({
        "vehicle": [{"tool": "fleet_api", "path": "/vehicles/OTHER-PLATE", "method": "GET"}],
    })

    def refusal_synthesiser(query, tool_results):
        assert any(r.get("result", {}).get("error") == "forbidden" for r in tool_results)
        return {"answer": "You are not permitted to access this vehicle.", "tools_used": [], "reasoning_steps": []}

    with _inject_graph(planner, refusal_synthesiser):
        respx.get("http://fleet-api:8000/vehicles/OTHER-PLATE").mock(
            return_value=httpx.Response(403)
        )
        with TestClient(app) as client:
            resp = client.post("/agent/run", json={
                "query": "vehicle OTHER-PLATE details",
                "caller_context": DRIVER_CTX,
            })
    assert resp.status_code == 200
    assert "not permitted" in resp.json()["answer"].lower()


@respx.mock
def test_rag_citations_flow_through_to_response():
    """RAG returns citations on /query; the agent must surface them (gap D1)."""
    planner = make_scripted_planner({
        "policy": [{"tool": "rag", "question": "what is the tyre policy?"}],
    })
    with _inject_graph(planner):
        respx.post("http://rag:8000/query").mock(
            return_value=httpx.Response(200, json={
                "answer": "Rotate every 10000km.",
                "citations": ["vehicle-profile-12-345-67", "maintenance-guide"],
            })
        )
        with TestClient(app) as client:
            resp = client.post("/agent/run", json={
                "query": "tyre policy?",
                "caller_context": ADMIN_CTX,
            })
    assert resp.status_code == 200
    body = resp.json()
    assert "citations" in body
    assert body["citations"] == ["vehicle-profile-12-345-67", "maintenance-guide"]


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@respx.mock
def test_clarify_response_returns_no_tools():
    planner = make_scripted_planner({})  # everything is ambiguous
    with _inject_graph(planner):
        with TestClient(app) as client:
            resp = client.post("/agent/run", json={
                "query": "huh?",
                "caller_context": ADMIN_CTX,
            })
    assert resp.status_code == 200
    body = resp.json()
    assert body["tools_used"] == []
    assert body["answer"]  # clarification message is non-empty
