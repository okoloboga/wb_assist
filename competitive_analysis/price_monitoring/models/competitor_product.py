"""
Модель товара конкурента.

Выделена в отдельный модуль для сокращения размера competitor.py
и повышения читаемости.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from .enums import MarketplaceType
from ..utils.serialization import (
    competitor_product_to_dict,
    competitor_product_from_dict_data,
)


@dataclass
class CompetitorProduct:
    """
    Товар конкурента.
    
    Attributes:
        id: Уникальный ID товара конкурента
        name: Название товара
        brand: Бренд товара
        article: Артикул товара
        sku: SKU товара
        url: URL товара
        marketplace: Маркетплейс
        current_price: Текущая цена
        original_price: Первоначальная цена
        discount_percent: Процент скидки
        rating: Рейтинг товара
        reviews_count: Количество отзывов
        availability: Доступность товара
        last_updated: Время последнего обновления
        metadata: Дополнительные метаданные
    """
    
    id: str
    name: str
    brand: str
    article: str
    sku: Optional[str] = None
    url: str = ""
    marketplace: MarketplaceType = MarketplaceType.OTHER
    current_price: float = 0.0
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: int = 0
    availability: bool = True
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Автоматический расчет скидки."""
        if (self.original_price is not None and 
            self.current_price > 0 and 
            self.discount_percent is None):
            if self.original_price > self.current_price:
                self.discount_percent = ((self.original_price - self.current_price) / self.original_price) * 100
    
    @property
    def effective_price(self) -> float:
        """Эффективная цена с учетом скидки."""
        return self.current_price
    
    @property
    def price_per_review(self) -> Optional[float]:
        """Цена за отзыв (показатель популярности)."""
        if self.reviews_count > 0:
            return self.current_price / self.reviews_count
        return None
    
    def update_price(self, new_price: float, original_price: Optional[float] = None) -> None:
        """
        Обновление цены товара.
        
        Args:
            new_price: Новая цена
            original_price: Новая первоначальная цена (опционально)
        """
        self.current_price = new_price
        if original_price is not None:
            self.original_price = original_price
        
        # Пересчет скидки
        self.discount_percent = None
        self.__post_init__()
        
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь (делегировано утилите)."""
        return competitor_product_to_dict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompetitorProduct':
        """Создание объекта из словаря (нормализация через утилиту)."""
        normalized = competitor_product_from_dict_data(data)
        return cls(**normalized)


__all__ = [
    "CompetitorProduct",
]