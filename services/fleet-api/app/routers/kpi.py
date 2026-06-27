from uuid import UUID

from fastapi import APIRouter

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import KpiDailyRead

router = APIRouter(prefix="/kpi", tags=["kpi"])


def _to_read(k) -> KpiDailyRead:
    return KpiDailyRead(
        snapshot_date=k.snapshot_date,
        total_km_7d=k.total_km_7d,
        avg_km_per_driver_7d=k.avg_km_per_driver_7d,
        avg_days_between_maintenance=k.avg_days_between_maintenance,
        maintenance_due_count=k.maintenance_due_count,
        docs_expiring_count=k.docs_expiring_count,
        top_customer_id=k.top_customer_id,
        top_customer_km=k.top_customer_km,
        top_customer_vehicle_count=k.top_customer_vehicle_count,
        computed_ts=k.computed_ts,
    )


@router.get(
    "/daily",
    response_model=list[KpiDailyRead],
    summary="Latest KPI snapshots (admin only)",
    description="Return the most-recent kpi_daily rows (default 2) for dashboard tiles + trends.",
)
def list_kpi_daily(session: Db, caller: Caller, limit: int = 2) -> list[KpiDailyRead]:
    assert_permitted(caller.role, Action.READ_KPI)
    company_id = UUID(caller.company_id) if caller.company_id else None
    return [_to_read(k) for k in repo.list_kpi_daily(session, limit=limit, company_id=company_id)]
