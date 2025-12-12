from typing import Dict, Any, List
import logging
from .db import run_sql_template

logger = logging.getLogger(__name__)

def _to_interval(period: str) -> str:
    mapping = {"7d": "7 days", "14d": "14 days", "30d": "30 days", "90d": "90 days"}
    return mapping.get(period, period if "day" in period else "7 days")

async def run_report(report_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        telegram_id = params.get("telegram_id")
        period = params.get("period", "7d")
        
        # Проверяем наличие обязательного параметра telegram_id
        if telegram_id is None:
            error_msg = f"Missing required parameter 'telegram_id' for report '{report_name}'. Received params: {list(params.keys())}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        logger.info(f"📊 Running report: {report_name} for telegram_id={telegram_id}, period={period}")
        
        if report_name == "top_products":
            interval = _to_interval(period)
            limit = params.get("limit", 10)
            
            logger.info(f"🔍 Fetching top products: telegram_id={telegram_id}, period={interval}, limit={limit}")
            
            rows = await run_sql_template(
                name="top_products_by_revenue",
                params={
                    "telegram_id": telegram_id,
                    "period": interval,
                    "limit": limit,
                },
            )
            
            logger.info(f"✅ Received {len(rows)} rows from top_products_by_revenue query")
            
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
            
            logger.info(f"✅ Top products report: {len(items)} items, total revenue={total_rev}")
            
            return {"report": report_name, "period": period, "items": items}

        # Default empty report for unknown names
        logger.warning(f"⚠️ Unknown report name: {report_name}")
        return {"report": report_name, "period": period, "items": []}
        
    except Exception as e:
        logger.error(f"❌ Error running report {report_name} with params {params}: {e}", exc_info=True)
        raise
