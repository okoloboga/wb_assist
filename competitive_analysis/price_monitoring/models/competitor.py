"""
Модель конкурента: фасад и логика управления товарами.

Файл облегчён: типы и модели вынесены в отдельные модули
(`enums.py`, `competitor_product.py`, `analysis.py`). Этот модуль
оставляет только класс Competitor и реэкспорт ключевых сущностей
для обратной совместимости импорта `models.competitor`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import statistics

# Импорт вынесенных сущностей
from .enums import CompetitorType, MarketplaceType
from .competitor_product import CompetitorProduct
from .analysis import CompetitorAnalysis
from ..utils.sheets_mapping import (
    competitor_to_sheets_rows,
    competitor_sheets_headers,
)
from ..utils.serialization import (
    competitor_to_dict,
    competitor_from_dict_data,
    competitor_to_json,
    competitor_from_json_data,
    competitor_product_from_dict_data,
)


@dataclass
class Competitor:
    """
    Конкурент.
    
    Attributes:
        id: Уникальный ID конкурента
        name: Название конкурента/магазина
        type: Тип конкурента
        marketplace: Основной маркетплейс
        website_url: URL сайта конкурента
        products: Список товаров конкурента
        is_active: Активен ли мониторинг конкурента
        priority: Приоритет конкурента (1-10)
        created_at: Время создания записи
        updated_at: Время последнего обновления
        metadata: Дополнительные метаданные
    """
    
    id: str
    name: str
    type: CompetitorType = CompetitorType.DIRECT
    marketplace: MarketplaceType = MarketplaceType.OTHER
    website_url: Optional[str] = None
    products: List[CompetitorProduct] = field(default_factory=list)
    is_active: bool = True
    priority: int = 5  # 1-10, где 10 - наивысший приоритет
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_product(self, product: CompetitorProduct) -> None:
        """
        Добавление товара конкурента.
        
        Args:
            product: Товар конкурента
        """
        # Проверка на дублирование
        existing_ids = {p.id for p in self.products}
        if product.id not in existing_ids:
            self.products.append(product)
            self.updated_at = datetime.now()
    
    def remove_product(self, product_id: str) -> bool:
        """
        Удаление товара конкурента.
        
        Args:
            product_id: ID товара для удаления
            
        Returns:
            True если товар был удален, False если не найден
        """
        initial_count = len(self.products)
        self.products = [p for p in self.products if p.id != product_id]
        
        if len(self.products) < initial_count:
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_product(self, product_id: str) -> Optional[CompetitorProduct]:
        """
        Получение товара по ID.
        
        Args:
            product_id: ID товара
            
        Returns:
            Товар или None если не найден
        """
        for product in self.products:
            if product.id == product_id:
                return product
        return None
    
    def get_products_by_brand(self, brand: str) -> List[CompetitorProduct]:
        """
        Получение товаров по бренду.
        
        Args:
            brand: Название бренда
            
        Returns:
            Список товаров указанного бренда
        """
        return [p for p in self.products if p.brand.lower() == brand.lower()]
    
    def get_available_products(self) -> List[CompetitorProduct]:
        """
        Получение доступных товаров.
        
        Returns:
            Список доступных товаров
        """
        return [p for p in self.products if p.availability]
    
    def get_price_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики цен товаров конкурента.
        
        Returns:
            Словарь со статистикой
        """
        available_products = self.get_available_products()
        
        if not available_products:
            return {
                'products_count': 0,
                'available_count': 0,
                'min_price': None,
                'max_price': None,
                'avg_price': None,
                'median_price': None,
                'total_reviews': 0,
                'avg_rating': None
            }
        
        prices = [p.current_price for p in available_products if p.current_price > 0]
        ratings = [p.rating for p in available_products if p.rating is not None]
        total_reviews = sum(p.reviews_count for p in available_products)
        
        return {
            'products_count': len(self.products),
            'available_count': len(available_products),
            'min_price': min(prices) if prices else None,
            'max_price': max(prices) if prices else None,
            'avg_price': statistics.mean(prices) if prices else None,
            'median_price': statistics.median(prices) if prices else None,
            'total_reviews': total_reviews,
            'avg_rating': statistics.mean(ratings) if ratings else None
        }
    
    def get_products_in_price_range(self, 
                                   min_price: float, 
                                   max_price: float) -> List[CompetitorProduct]:
        """
        Получение товаров в ценовом диапазоне.
        
        Args:
            min_price: Минимальная цена
            max_price: Максимальная цена
            
        Returns:
            Список товаров в указанном диапазоне
        """
        return [
            p for p in self.get_available_products()
            if min_price <= p.current_price <= max_price
        ]
    
    def get_top_rated_products(self, limit: int = 10) -> List[CompetitorProduct]:
        """
        Получение товаров с наивысшим рейтингом.
        
        Args:
            limit: Максимальное количество товаров
            
        Returns:
            Список товаров, отсортированных по рейтингу
        """
        products_with_rating = [
            p for p in self.get_available_products()
            if p.rating is not None
        ]
        
        return sorted(
            products_with_rating,
            key=lambda x: (x.rating, x.reviews_count),
            reverse=True
        )[:limit]
    
    def get_most_reviewed_products(self, limit: int = 10) -> List[CompetitorProduct]:
        """
        Получение товаров с наибольшим количеством отзывов.
        
        Args:
            limit: Максимальное количество товаров
            
        Returns:
            Список товаров, отсортированных по количеству отзывов
        """
        return sorted(
            self.get_available_products(),
            key=lambda x: x.reviews_count,
            reverse=True
        )[:limit]
    
    def update_products_prices(self, price_updates: Dict[str, float]) -> int:
        """
        Массовое обновление цен товаров.
        
        Args:
            price_updates: Словарь {product_id: new_price}
            
        Returns:
            Количество обновленных товаров
        """
        updated_count = 0
        
        for product in self.products:
            if product.id in price_updates:
                product.update_price(price_updates[product.id])
                updated_count += 1
        
        if updated_count > 0:
            self.updated_at = datetime.now()
        
        return updated_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь (делегировано утилите)."""
        return competitor_to_dict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Competitor':
        """Создание объекта из словаря (нормализация через утилиту)."""
        normalized = competitor_from_dict_data(data)
        products = [CompetitorProduct.from_dict(competitor_product_from_dict_data(p_data))
                    for p_data in normalized.get('products', [])]
        normalized['products'] = products
        return cls(**normalized)
    
    def to_json(self) -> str:
        """Преобразование в JSON строку (делегировано утилите)."""
        return competitor_to_json(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Competitor':
        """Создание объекта из JSON строки (нормализация через утилиту)."""
        normalized = competitor_from_json_data(json_str)
        return cls.from_dict(normalized)
    
    def to_sheets_rows(self) -> List[List[Any]]:
        """
        Преобразование в строки для Google Sheets.
        
        Returns:
            Список строк для записи в таблицу
        """
        return competitor_to_sheets_rows(self)
    
    @staticmethod
    def get_sheets_headers() -> List[str]:
        """
        Получение заголовков для Google Sheets.
        
        Returns:
            Список заголовков столбцов
        """
        return competitor_sheets_headers()
    
    def __str__(self) -> str:
        """Строковое представление конкурента."""
        return f"Competitor(id='{self.id}', name='{self.name}', products={len(self.products)})"
    
    def __repr__(self) -> str:
        """Представление для отладки."""
        return f"Competitor(id='{self.id}', name='{self.name}', type={self.type.value}, products_count={len(self.products)})"

# Реэкспорт ключевых сущностей для обратной совместимости
__all__ = [
    "Competitor",
    "CompetitorProduct",
    "CompetitorAnalysis",
    "CompetitorType",
    "MarketplaceType",
]