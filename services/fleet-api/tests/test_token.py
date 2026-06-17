"""T10 - Internal-token guard: missing/wrong token -> 401; client-asserted role ignored.
/health is public (load-balancer probe). All other endpoints require X-Internal-Token.
"""
from tests.conftest import TEST_TOKEN
from shepherd_contracts.auth import CallerContext, Role


def test_missing_token_rejected(raw_client):
    r = raw_client.get(
        "/config",
        headers={"X-Caller-Context": CallerContext(role=Role.admin).model_dump_json()},
    )
    assert r.status_code == 401


def test_wrong_token_rejected(raw_client):
    r = raw_client.get(
        "/config",
        headers={
            "X-Internal-Token": "wrong-token",
            "X-Caller-Context": CallerContext(role=Role.admin).model_dump_json(),
        },
    )
    assert r.status_code == 401


def test_correct_token_accepted(raw_client):
    r = raw_client.get(
        "/config",
        headers={
            "X-Internal-Token": TEST_TOKEN,
            "X-Caller-Context": CallerContext(role=Role.admin).model_dump_json(),
        },
    )
    assert r.status_code == 200


def test_health_is_public(raw_client):
    """Health endpoint is accessible without a token (for load balancer probes)."""
    r = raw_client.get("/health")
    assert r.status_code == 200


def test_no_caller_context_rejected(raw_client):
    """Missing X-Caller-Context header on a protected endpoint returns 422."""
    r = raw_client.get("/config", headers={"X-Internal-Token": TEST_TOKEN})
    assert r.status_code == 422


def test_invalid_caller_context_rejected(raw_client):
    r = raw_client.get(
        "/config",
        headers={
            "X-Internal-Token": TEST_TOKEN,
            "X-Caller-Context": "not-valid-json",
        },
    )
    assert r.status_code == 400
