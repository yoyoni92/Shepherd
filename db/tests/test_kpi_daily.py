"""refresh_kpi_daily() math (migration 0003).

Seeds a deterministic fleet, runs the function, and asserts today's kpi_daily row.
Runs against the real Postgres test container; system_config is empty so the docs
window falls back to the function's 30-day default.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import text


def _scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


def test_refresh_kpi_daily_row_math(conn):
    now = datetime.now(timezone.utc)
    # Use the DB's current_date (UTC container), not the host's local date - the
    # function keys snapshots on current_date, which can differ from a non-UTC host.
    today = _scalar(conn, "SELECT current_date")

    co = _scalar(conn, "INSERT INTO companies (name) VALUES ('Acme') RETURNING company_id")

    customer_id = _scalar(
        conn,
        "INSERT INTO customers (company_id, full_name) VALUES (:co, 'Acme') RETURNING customer_id",
        co=co,
    )
    for name, phone in [("D1", "+972500000001"), ("D2", "+972500000002")]:
        conn.execute(
            text("INSERT INTO drivers (company_id, full_name, phone_number) VALUES (:co, :n, :p)"),
            {"co": co, "n": name, "p": phone},
        )

    # vehicle1: maintenance due (current >= next), insurance expiring in 5d
    v1 = _scalar(
        conn,
        """INSERT INTO vehicles (company_id, licensing_plate, customer_id, current_km, next_maintenance_km,
                                 insurance_valid_to, license_valid_to)
           VALUES (:co, 'V-1', :c, 10000, 9000, :ins, :lic) RETURNING vehicle_id""",
        co=co, c=customer_id, ins=today + timedelta(days=5), lic=today + timedelta(days=400),
    )
    # vehicle2: not due, docs far out
    v2 = _scalar(
        conn,
        """INSERT INTO vehicles (company_id, licensing_plate, customer_id, current_km, next_maintenance_km,
                                 insurance_valid_to, license_valid_to)
           VALUES (:co, 'V-2', :c, 5000, 20000, :ins, :lic) RETURNING vehicle_id""",
        co=co, c=customer_id, ins=today + timedelta(days=400), lic=today + timedelta(days=400),
    )

    # km_updates: one reading before the 7d window (base), one inside it.
    km_rows = [
        (v1, 1000, now - timedelta(days=10)),
        (v1, 1500, now - timedelta(days=1)),   # delta 500
        (v2, 3000, now - timedelta(days=10)),
        (v2, 3200, now - timedelta(days=2)),    # delta 200
    ]
    for vid, km, ts in km_rows:
        conn.execute(
            text("""INSERT INTO km_updates (company_id, vehicle_id, km, recorded_ts, source)
                    VALUES (:co, :v, :km, :ts, 'admin_ui')"""),
            {"co": co, "v": vid, "km": km, "ts": ts},
        )

    # vehicle_care: two services 30 days apart -> avg gap 30
    for sd, km in [(today - timedelta(days=40), 800), (today - timedelta(days=10), 1200)]:
        conn.execute(
            text("""INSERT INTO vehicle_care (company_id, vehicle_id, service_date, maintenance_type, km_at_service)
                    VALUES (:co, :v, :sd, 'small', :km)"""),
            {"co": co, "v": v1, "sd": sd, "km": km},
        )

    conn.execute(text("SELECT refresh_kpi_daily()"))

    row = conn.execute(
        text("SELECT * FROM kpi_daily WHERE snapshot_date = :d"), {"d": today}
    ).mappings().one()

    assert row["total_km_7d"] == 700                       # 500 + 200
    assert float(row["avg_km_per_driver_7d"]) == 350.0     # 700 / 2 drivers
    assert float(row["avg_days_between_maintenance"]) == 30.0
    assert row["docs_expiring_count"] == 1                 # v1 insurance within 30d
    assert row["top_customer_id"] == customer_id
    assert row["top_customer_km"] == 700
    assert row["top_customer_vehicle_count"] == 2
