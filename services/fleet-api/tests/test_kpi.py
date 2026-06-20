"""GET /kpi/daily — admin reads the latest kpi_daily snapshots; drivers are forbidden.

The 0003 migration backfills today's row, so the endpoint always has at least one snapshot.
"""
from tests.conftest import admin_headers, driver_headers


def test_kpi_daily_admin_reads_snapshots(client):
    resp = client.get("/kpi/daily?limit=2", headers=admin_headers())
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list) and len(rows) >= 1
    assert len(rows) <= 2
    assert "snapshot_date" in rows[0]
    assert "total_km_7d" in rows[0]
    assert "top_customer_vehicle_count" in rows[0]


def test_kpi_daily_forbidden_for_driver(client):
    resp = client.get("/kpi/daily", headers=driver_headers("00000000-0000-0000-0000-000000000000"))
    assert resp.status_code == 403
