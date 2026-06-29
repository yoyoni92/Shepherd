"""Flow 5.3 - Fleet summary (admin, single-shot) from the latest KPI snapshot."""

from __future__ import annotations

from app import fmt, texts
from app.context import Ctx
from app.tg import send


async def fleet_summary(ctx: Ctx, route: str | None) -> None:
    resp = await ctx.fleet.get("/kpi/daily", params={"limit": 1})
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        await send(ctx, f"{texts.FLEET_SUMMARY_TITLE}\n\nאין נתונים זמינים.")
        return
    k = rows[0]

    def _v(key: str) -> object:
        v = k.get(key)
        return "-" if v is None else v

    lines = [
        texts.FLEET_SUMMARY_TITLE,
        "",
        fmt.kv('ק"מ ב-7 ימים', _v("total_km_7d")),
        fmt.kv('ממוצע ק"מ לנהג', _v("avg_km_per_driver_7d")),
        fmt.kv("מסמכים שעומדים לפוג", _v("docs_expiring_count")),
    ]
    await send(ctx, "\n".join(lines))
