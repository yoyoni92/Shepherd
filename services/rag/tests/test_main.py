"""T7 - /query endpoint."""
import uuid

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.generate import answer as _answer_fn
from app.retrieve import query as _query_fn


PLATE = "555-55-555"
VID = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def patch_globals(ef, monkeypatch):
    import chromadb
    client = chromadb.EphemeralClient()
    col = client.get_or_create_collection("t7_main", embedding_function=ef)
    col.upsert(
        documents=[f"Vehicle: {PLATE}\nDriver: Test Driver\nOpen tickets: 0"],
        metadatas=[{"vehicle_id": VID, "plate": PLATE, "driver_id": "", "customer_id": ""}],
        ids=[VID],
    )
    mock_llm = lambda prompt: f"Vehicle {PLATE} status: operational."
    monkeypatch.setattr(main_module, "_collection", col)
    monkeypatch.setattr(main_module, "_llm", mock_llm)


@pytest.fixture
def client():
    return TestClient(app)


def test_query_returns_answer_and_citations(client):
    resp = client.post("/query", json={"question": PLATE, "caller_context": {"role": "admin"}})
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert PLATE in body["citations"]


def test_query_unknown_returns_no_record(client):
    resp = client.post(
        "/query",
        json={"question": "999-99-999 status", "caller_context": {"role": "driver", "vehicle_ids": []}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "No record found."
    assert body["citations"] == []


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
