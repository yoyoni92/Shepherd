"""emit_time_maintenance_due() - the daily time-based maintenance sweep.

Emits one open maintenance_due event per vehicle whose next_maintenance_date has
arrived (within the per-company buffer, default 30d), deduped against open events.
Runs against the real Postgres test container.
"""
from datetime import timedelta

from sqlalchemy import text


def _scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


def _company(conn):
    return _scalar(conn, "INSERT INTO companies (name) VALUES ('Acme') RETURNING company_id")


def _vehicle(conn, company_id, plate, next_date):
    return _scalar(
        conn,
        """INSERT INTO vehicles (company_id, licensing_plate, next_maintenance_date)
           VALUES (:c, :p, :d) RETURNING vehicle_id""",
        c=company_id, p=plate, d=next_date,
    )


def _open_due(conn, vehicle_id):
    return conn.execute(
        text("""SELECT payload_json FROM events
                WHERE vehicle_id = :v AND event_type = 'maintenance_due' AND status = 'open'"""),
        {"v": vehicle_id},
    ).mappings().all()


def test_time_sweep_emits_for_due_and_skips_future(conn):
    today = _scalar(conn, "SELECT current_date")
    cid = _company(conn)
    due = _vehicle(conn, cid, "DUE-1", today)                       # due today
    soon = _vehicle(conn, cid, "SOON-1", today + timedelta(days=10))  # inside 30d buffer
    future = _vehicle(conn, cid, "FUT-1", today + timedelta(days=90))  # outside buffer
    never = _vehicle(conn, cid, "NONE-1", None)                      # no time interval

    conn.execute(text("SELECT emit_time_maintenance_due()"))

    assert len(_open_due(conn, due)) == 1
    assert _open_due(conn, due)[0]["payload_json"] == {"trigger": "time"}
    assert len(_open_due(conn, soon)) == 1
    assert _open_due(conn, future) == []
    assert _open_due(conn, never) == []


def test_time_sweep_dedups_open_event(conn):
    today = _scalar(conn, "SELECT current_date")
    cid = _company(conn)
    v = _vehicle(conn, cid, "DUE-2", today)

    conn.execute(text("SELECT emit_time_maintenance_due()"))
    conn.execute(text("SELECT emit_time_maintenance_due()"))  # second run must not duplicate

    assert len(_open_due(conn, v)) == 1


def test_time_sweep_honors_company_buffer(conn):
    today = _scalar(conn, "SELECT current_date")
    cid = _company(conn)
    # 60-day buffer: a vehicle due in 45 days should now fire.
    conn.execute(
        text("""INSERT INTO system_config (company_id, config_key, config_value)
                VALUES (:c, 'maintenance_time_buffer_days', '60'::jsonb)"""),
        {"c": cid},
    )
    v = _vehicle(conn, cid, "BUF-1", today + timedelta(days=45))

    conn.execute(text("SELECT emit_time_maintenance_due()"))

    assert len(_open_due(conn, v)) == 1
