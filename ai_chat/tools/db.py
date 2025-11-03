from typing import Dict, Any, List, Tuple
from .db_pool import POOL

SQL_TEMPLATES: Dict[str, str] = {
    "timeseries_sales": (
        """
        SELECT date_trunc($3, sale_date)::date AS d, SUM(qty) AS qty, SUM(revenue) AS revenue
        FROM sales
        WHERE telegram_id = $1 AND sale_date >= CURRENT_DATE - $2::interval
        GROUP BY d
        ORDER BY d
        """
    ),
    "top_products_by_revenue": (
        """
        SELECT sku_id, name, SUM(revenue) AS revenue, SUM(qty) AS qty
        FROM sales
        WHERE telegram_id = $1 AND sale_date >= CURRENT_DATE - $2::interval
        GROUP BY sku_id, name
        ORDER BY revenue DESC
        LIMIT $3
        """
    ),
    "orders_summary": (
        """
        SELECT COUNT(*) AS orders, SUM(revenue) AS revenue
        FROM orders
        WHERE telegram_id = $1 AND created_at >= $2 AND created_at < $3
        """
    ),
    "stock_levels": (
        """
        SELECT sku_id, name, stock
        FROM stocks
        WHERE telegram_id = $1
        """
    ),
    "neg_reviews_agg": (
        """
        SELECT reason, COUNT(*) AS cnt
        FROM reviews
        WHERE telegram_id = $1 AND created_at >= CURRENT_DATE - $2::interval AND rating <= 3
        GROUP BY reason
        ORDER BY cnt DESC
        """
    ),
}

def _map_params(name: str, params: Dict[str, Any]) -> Tuple:
    if name == "timeseries_sales":
        return (
            params["telegram_id"],
            params.get("period", "30 days"),
            params.get("granularity", "day"),
        )
    if name == "top_products_by_revenue":
        return (
            params["telegram_id"],
            params.get("period", "7 days"),
            params.get("limit", 10),
        )
    if name == "orders_summary":
        return (
            params["telegram_id"],
            params["from"],
            params["to"],
        )
    if name == "stock_levels":
        return (params["telegram_id"],)
    if name == "neg_reviews_agg":
        return (
            params["telegram_id"],
            params.get("period", "30 days"),
        )
    raise ValueError("Unknown template or missing params")

async def run_sql_template(name: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    if name not in SQL_TEMPLATES:
        raise ValueError("Template not allowed")
    if POOL is None:
        raise RuntimeError("DB pool is not initialized or database is not Postgres")
    query = SQL_TEMPLATES[name]
    args = _map_params(name, params)
    async with POOL.acquire() as conn:  # type: ignore
        rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]
