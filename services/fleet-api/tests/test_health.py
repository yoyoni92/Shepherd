"""T1 - Health endpoint + app boot + Swagger served."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_docs_served(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_redoc_served(client):
    r = client.get("/redoc")
    assert r.status_code == 200
