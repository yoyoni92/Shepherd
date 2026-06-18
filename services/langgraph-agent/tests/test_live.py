"""T7 - Live smoke test (gated: requires ANTHROPIC_API_KEY + running services)."""
import os

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_live_two_step_question():
    """Real agent run: 2-step question using Fleet API + RAG compose."""
    from fastapi.testclient import TestClient
    from app.main import app, _get_graph  # noqa: F401 - triggers singleton build

    with TestClient(app) as client:
        resp = client.post("/agent/run", json={
            "query": "Which vehicles are due for maintenance next month, and what is the profile of the first one?",
            "caller_context": {"role": "admin"},
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert len(body["tools_used"]) >= 1
    assert len(body["reasoning_steps"]) >= 1
