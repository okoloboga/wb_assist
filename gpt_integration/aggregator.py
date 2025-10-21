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