from typing import Any, Dict, List, Optional

"""
Агрегатор Stage 3: собирает сводные данные из различных источников в единый JSON,
совместимый с секцией DATA в LLM_ANALYSIS_TEMPLATE.md.

Использование:
- aggregate(data) — если данные уже в словаре с ключами ('sales', 'ads', ...).
- build_from_sources(...) — если источники приходят разрозненно.
"""

DATA_KEYS = [
    "meta",
    "sales",
    "ads",
    "inventory",
    "reviews",
    "prices",
    "competitors",
    "top_products",
    "slow_products",
]


def aggregate(sources: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect summary data from various sources into a single structure compatible
    with DATA section in LLM_ANALYSIS_TEMPLATE.md.
    Unknown keys will be kept under "extra".
    """
    res: Dict[str, Any] = {k: sources.get(k) for k in DATA_KEYS}
    extra: Dict[str, Any] = {}
    for k, v in sources.items():
        if k not in DATA_KEYS:
            extra[k] = v

    # Compute key metrics for Stage 4
    sales: Dict[str, Any] = sources.get("sales") or {}
    dynamics: Dict[str, Any] = sales.get("dynamics") or {}
    sales_periods: Dict[str, Any] = sales.get("sales_periods") or {}
    stocks_summary: Dict[str, Any] = sales.get("stocks_summary") or {}
    top_products_list: List[Dict[str, Any]] = (
        sales.get("top_products")
        or sources.get("top_products")
        or []
    )

    day_over_day = dynamics.get("yesterday_growth_percent")
    if day_over_day is None:
        try:
            today = sales_periods.get("today") or {}
            yesterday = sales_periods.get("yesterday") or {}
            t = float(today.get("count", 0) or 0)
            y = float(yesterday.get("count", 0) or 0)
            if y > 0:
                day_over_day = ((t - y) / y) * 100.0
            elif t > 0:
                day_over_day = 100.0
            else:
                day_over_day = 0.0
        except Exception:
            day_over_day = 0.0

    week_over_week = dynamics.get("week_growth_percent")

    critical_stocks_count = stocks_summary.get("critical_count")
    if critical_stocks_count is None:
        stocks_critical = sources.get("stocks_critical")
        if isinstance(stocks_critical, list):
            critical_stocks_count = len(stocks_critical)

    top_products_count = len(top_products_list) if isinstance(top_products_list, list) else 0

    computed_metrics = {
        "day_over_day": day_over_day if isinstance(day_over_day, (int, float)) else 0.0,
        "week_over_week": week_over_week if isinstance(week_over_week, (int, float)) else 0.0,
        "top_products_count": top_products_count,
        "critical_stocks_count": int(critical_stocks_count) if isinstance(critical_stocks_count, (int, float)) else 0,
    }

    # Ensure meta exists and attach computed metrics
    meta = sources.get("meta") or {}
    meta["computed_metrics"] = computed_metrics
    res["meta"] = meta

    # Prefer to carry top_products list (from sales or sources)
    if top_products_list:
        res["top_products"] = top_products_list

    if extra:
        res["extra"] = extra
    return res


def build_from_sources(
    meta: Optional[Dict[str, Any]] = None,
    sales: Optional[Dict[str, Any]] = None,
    ads: Optional[Dict[str, Any]] = None,
    inventory: Optional[Dict[str, Any]] = None,
    reviews: Optional[Dict[str, Any]] = None,
    prices: Optional[Dict[str, Any]] = None,
    competitors: Optional[Dict[str, Any]] = None,
    top_products: Optional[List[Dict[str, Any]]] = None,
    slow_products: Optional[List[Dict[str, Any]]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Build DATA dict explicitly from typed args.
    Unknown kwargs go to "extra".
    """
    data: Dict[str, Any] = {
        "meta": meta,
        "sales": sales,
        "ads": ads,
        "inventory": inventory,
        "reviews": reviews,
        "prices": prices,
        "competitors": competitors,
        "top_products": top_products or [],
        "slow_products": slow_products or [],
    }
    if extra:
        data["extra"] = extra
    return data