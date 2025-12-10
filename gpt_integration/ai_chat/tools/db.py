from typing import Dict, Any, List, Tuple
import re
from .db_pool import get_asyncpg_pool

SQL_TEMPLATES: Dict[str, str] = {
    "timeseries_sales": (
        """
        SELECT 
            date_trunc($3, ws.sale_date)::date AS d, 
            COUNT(*) AS qty, 
            SUM(ws.amount) AS revenue
        FROM wb_sales ws
        JOIN cabinet_users cu ON ws.cabinet_id = cu.cabinet_id
        JOIN users u ON cu.user_id = u.id
        WHERE u.telegram_id = $1 
          AND ws.sale_date >= CURRENT_DATE - make_interval(days => $2)
          AND ws.type = 'buyout'
          AND (ws.is_cancel IS NULL OR ws.is_cancel = false)
        GROUP BY d
        ORDER BY d
        """
    ),
    "top_products_by_revenue": (
        """
        SELECT 
            ws.nm_id AS sku_id, 
            ws.product_name AS name, 
            SUM(ws.amount) AS revenue, 
            COUNT(*) AS qty
        FROM wb_sales ws
        JOIN cabinet_users cu ON ws.cabinet_id = cu.cabinet_id
        JOIN users u ON cu.user_id = u.id
        WHERE u.telegram_id = $1 
          AND ws.sale_date >= CURRENT_DATE - make_interval(days => $2)
          AND ws.type = 'buyout'
          AND (ws.is_cancel IS NULL OR ws.is_cancel = false)
        GROUP BY ws.nm_id, ws.product_name
        ORDER BY revenue DESC
        LIMIT $3
        """
    ),
    "orders_summary": (
        """
        SELECT 
            COUNT(*) AS orders, 
            SUM(wo.total_price) AS revenue
        FROM wb_orders wo
        JOIN cabinet_users cu ON wo.cabinet_id = cu.cabinet_id
        JOIN users u ON cu.user_id = u.id
        WHERE u.telegram_id = $1 
          AND wo.order_date >= $2 
          AND wo.order_date < $3
        """
    ),
    "stock_levels": (
        """
        SELECT 
            ws.nm_id AS sku_id, 
            ws.name, 
            ws.quantity AS stock
        FROM wb_stocks ws
        JOIN cabinet_users cu ON ws.cabinet_id = cu.cabinet_id
        JOIN users u ON cu.user_id = u.id
        WHERE u.telegram_id = $1
        """
    ),
    "neg_reviews_agg": (
        """
        SELECT 
            wr.text AS reason, 
            COUNT(*) AS cnt
        FROM wb_reviews wr
        JOIN cabinet_users cu ON wr.cabinet_id = cu.cabinet_id
        JOIN users u ON cu.user_id = u.id
        WHERE u.telegram_id = $1 
          AND wr.created_at >= CURRENT_DATE - make_interval(days => $2) 
          AND wr.rating <= 3
        GROUP BY wr.text
        ORDER BY cnt DESC
        """
    ),
}

def _parse_interval(period: str) -> int:
    """Преобразует строку периода в количество дней (int)"""
    if isinstance(period, int):
        return period
    # Извлекаем число из строки типа "7 days", "30 days" и т.д.
    match = re.search(r'(\d+)', str(period))
    if match:
        return int(match.group(1))
    return 30  # По умолчанию 30 дней

def _map_params(name: str, params: Dict[str, Any]) -> Tuple:
    if name == "timeseries_sales":
        period_str = params.get("period", "30 days")
        days = _parse_interval(period_str)
        return (
            params["telegram_id"],
            days,  # Передаем число дней вместо строки
            params.get("granularity", "day"),
        )
    if name == "top_products_by_revenue":
        period_str = params.get("period", "7 days")
        days = _parse_interval(period_str)
        return (
            params["telegram_id"],
            days,  # Передаем число дней вместо строки
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
        period_str = params.get("period", "30 days")
        days = _parse_interval(period_str)
        return (
            params["telegram_id"],
            days,  # Передаем число дней вместо строки
        )
    raise ValueError("Unknown template or missing params")

async def run_sql_template(name: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    if name not in SQL_TEMPLATES:
        raise ValueError("Template not allowed")
    
    # Получить пул подключений (автоматически инициализируется, если нужно)
    pool = await get_asyncpg_pool()
    
    query = SQL_TEMPLATES[name]
    args = _map_params(name, params)
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]
