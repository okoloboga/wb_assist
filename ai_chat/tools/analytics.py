from typing import Any, Dict, List, Optional

from .db import run_sql_template

def _to_interval(period: str) -> str:
    mapping = {"7d": "7 days", "14d": "14 days", "30d": "30 days", "90d": "90 days", "180d": "180 days"}
    return mapping.get(period, period if "day" in period else "30 days")

def _granularity_sql(granularity: str) -> str:
    return "week" if granularity == "week" else "day"

async def get_dashboard(telegram_id: int, period: str = "7d") -> Dict[str, Any]:
    interval = _to_interval(period)
    rows = await run_sql_template(
        name="timeseries_sales",
        params={"telegram_id": telegram_id, "period": interval, "granularity": "day"},
    )
    revenue = sum(r.get("revenue", 0) or 0 for r in rows)
    orders = sum(r.get("qty", 0) or 0 for r in rows)
    aov = (revenue / orders) if orders else 0
    return {
        "period": period,
        "orders": int(orders),
        "revenue": float(revenue),
        "aov": float(aov),
        "stocks_total": None,
        "avg_rating": None,
        "neg_reviews": None,
        "notes": [],
    }

async def get_sales_timeseries(telegram_id: int, period: str = "30d", granularity: str = "day") -> Dict[str, Any]:
    interval = _to_interval(period)
    gran = _granularity_sql(granularity)
    rows = await run_sql_template(
        name="timeseries_sales",
        params={"telegram_id": telegram_id, "period": interval, "granularity": gran},
    )
    series = [{"date": str(r.get("d")), "qty": int(r.get("qty", 0) or 0), "revenue": float(r.get("revenue", 0) or 0)} for r in rows]
    # Simple WoW approximation: last 7 vs prev 7 if enough points
    wow = 0.0
    if len(series) >= 14 and gran == "day":
        last7 = sum(p["revenue"] for p in series[-7:])
        prev7 = sum(p["revenue"] for p in series[-14:-7])
        if prev7:
            wow = (last7 - prev7) / prev7
    return {"granularity": granularity, "series": series, "wow": wow}

async def compute_kpis(kpi_list: List[str], scope: Dict[str, Any], period: str) -> Dict[str, Any]:
    # For now only level=all is supported via sales timeseries aggregation.
    interval = _to_interval(period)
    rows = await run_sql_template(
        name="timeseries_sales",
        params={"telegram_id": scope.get("telegram_id"), "period": interval, "granularity": "day"},
    )
    revenue = sum(r.get("revenue", 0) or 0 for r in rows)
    orders = sum(r.get("qty", 0) or 0 for r in rows)
    aov = (revenue / orders) if orders else 0
    kpis: Dict[str, Any] = {}
    for k in kpi_list:
        if k == "revenue":
            kpis[k] = float(revenue)
        elif k == "orders":
            kpis[k] = int(orders)
        elif k == "aov":
            kpis[k] = float(aov)
        else:
            kpis[k] = 0
    return {"period": period, "scope": scope, "kpis": kpis}

async def forecast_sales(telegram_id: int, sku_id: Optional[int] = None, horizon: int = 14, method: str = "auto", include_ci: bool = True) -> Dict[str, Any]:
    # Placeholder: forecasting to be implemented in later stage
    return {"horizon": horizon, "level": "sku" if sku_id else "all", "sku_id": sku_id, "forecast": [], "method": method}
