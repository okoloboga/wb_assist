from typing import Dict, Any, List
from .db import run_sql_template

def _to_interval(period: str) -> str:
    mapping = {"7d": "7 days", "14d": "14 days", "30d": "30 days", "90d": "90 days"}
    return mapping.get(period, period if "day" in period else "7 days")

async def run_report(report_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    telegram_id = params.get("telegram_id")
    period = params.get("period", "7d")
    if report_name == "top_products":
        rows = await run_sql_template(
            name="top_products_by_revenue",
            params={
                "telegram_id": telegram_id,
                "period": _to_interval(period),
                "limit": params.get("limit", 10),
            },
        )
        items: List[Dict[str, Any]] = [
            {
                "sku_id": r.get("sku_id"),
                "name": r.get("name"),
                "revenue": float(r.get("revenue", 0) or 0),
                "qty": int(r.get("qty", 0) or 0),
            }
            for r in rows
        ]
        total_rev = sum(i["revenue"] for i in items) or 1
        for i in items:
            i["share"] = i["revenue"] / total_rev
        return {"report": report_name, "period": period, "items": items}

    # Default empty report for unknown names
    return {"report": report_name, "period": period, "items": []}
