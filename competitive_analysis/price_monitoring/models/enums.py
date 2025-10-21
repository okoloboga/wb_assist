"""
Перечисления для моделей конкурентов и маркетплейсов.
"""

from enum import Enum


class CompetitorType(Enum):
    """Тип конкурента."""
    DIRECT = "direct"           # Прямой конкурент (тот же товар)
    INDIRECT = "indirect"       # Косвенный конкурент (аналогичный товар)
    SUBSTITUTE = "substitute"   # Товар-заменитель
    BRAND = "brand"             # Конкурент по бренду


class MarketplaceType(Enum):
    """Тип маркетплейса."""
    WILDBERRIES = "wildberries"
    OZON = "ozon"
    YANDEX_MARKET = "yandex_market"
    AVITO = "avito"
    ALIEXPRESS = "aliexpress"
    AMAZON = "amazon"
    OTHER = "other"


__all__ = [
    "CompetitorType",
    "MarketplaceType",
]