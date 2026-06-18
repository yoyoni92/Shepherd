"""T1 - Tools are typed + permission-aware."""
import json

import httpx
import pytest
import respx

from app.tools import fleet_api_tool, rag_tool

ADMIN_CTX = {"role": "admin"}
DRIVER_CTX = {"role": "driver", "driver_id": "driver-123"}


@respx.mock
def test_fleet_api_forwards_caller_context():
    route = respx.get("http://fleet-api:8000/vehicles").mock(
        return_value=httpx.Response(200, json=[])
    )
    fleet_api_tool("/vehicles", caller_context=ADMIN_CTX)
    assert route.called
    sent_ctx = json.loads(route.calls.last.request.headers["X-Caller-Context"])
    assert sent_ctx == ADMIN_CTX


@respx.mock
def test_fleet_api_forwards_internal_token(monkeypatch):
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "tok-test")
    import importlib
    import app.tools as tools_mod
    importlib.reload(tools_mod)

    route = respx.get("http://fleet-api:8000/vehicles").mock(
        return_value=httpx.Response(200, json=[])
    )
    tools_mod.fleet_api_tool("/vehicles", caller_context=ADMIN_CTX)
    assert route.calls.last.request.headers["X-Internal-Token"] == "tok-test"


@respx.mock
def test_fleet_api_403_surfaces_as_refusal():
    respx.get("http://fleet-api:8000/vehicles/ABC-123").mock(
        return_value=httpx.Response(403)
    )
    result = fleet_api_tool("/vehicles/ABC-123", caller_context=DRIVER_CTX)
    assert result["error"] == "forbidden"
    assert "detail" in result


@respx.mock
def test_fleet_api_raises_on_5xx():
    respx.get("http://fleet-api:8000/vehicles").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(httpx.HTTPStatusError):
        fleet_api_tool("/vehicles", caller_context=ADMIN_CTX)


@respx.mock
def test_rag_tool_calls_query_endpoint():
    route = respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(200, json={"answer": "ok", "citations": []})
    )
    result = rag_tool(question="status of plate X", caller_context=ADMIN_CTX)
    assert result["answer"] == "ok"
    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert body["caller_context"] == ADMIN_CTX


@respx.mock
def test_rag_tool_forwards_caller_context_to_rag():
    route = respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(200, json={"answer": "found", "citations": ["123"]})
    )
    rag_tool(question="insurance?", caller_context=DRIVER_CTX)
    body = json.loads(route.calls.last.request.content)
    assert body["caller_context"] == DRIVER_CTX
