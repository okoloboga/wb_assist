"""
Модель конкурента для хранения информации о конкурентах и их товарах.

Содержит информацию о конкурентах, их товарах, ценах и методы
для анализа конкурентной позиции.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import json
import statistics


class CompetitorType(Enum):
    """Тип конкурента."""
    DIRECT = "direct"           # Прямой конкурент (тот же товар)
    INDIRECT = "indirect"       # Косвенный конкурент (аналогичный товар)
    SUBSTITUTE = "substitute"   # Товар-заменитель
    BRAND = "brand"            # Конкурент по бренду


class MarketplaceType(Enum):
    """Тип маркетплейса."""
    WILDBERRIES = "wildberries"
    OZON = "ozon"
    YANDEX_MARKET = "yandex_market"
    AVITO = "avito"
    ALIEXPRESS = "aliexpress"
    AMAZON = "amazon"
    OTHER = "other"


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
        """Преобразование в словарь."""
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'article': self.article,
            'sku': self.sku,
            'url': self.url,
            'marketplace': self.marketplace.value,
            'current_price': self.current_price,
            'original_price': self.original_price,
            'discount_percent': self.discount_percent,
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'availability': self.availability,
            'last_updated': self.last_updated.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompetitorProduct':
        """Создание объекта из словаря."""
        if isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        if data.get('marketplace'):
            data['marketplace'] = MarketplaceType(data['marketplace'])
        
        return cls(**data)


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
        """Преобразование в словарь."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'marketplace': self.marketplace.value,
            'website_url': self.website_url,
            'products': [p.to_dict() for p in self.products],
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Competitor':
        """Создание объекта из словаря."""
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        if isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        if data.get('type'):
            data['type'] = CompetitorType(data['type'])
        
        if data.get('marketplace'):
            data['marketplace'] = MarketplaceType(data['marketplace'])
        
        products = [CompetitorProduct.from_dict(p_data) 
                   for p_data in data.get('products', [])]
        data['products'] = products
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Преобразование в JSON строку."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Competitor':
        """Создание объекта из JSON строки."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_sheets_rows(self) -> List[List[Any]]:
        """
        Преобразование в строки для Google Sheets.
        
        Returns:
            Список строк для записи в таблицу
        """
        rows = []
        for product in self.products:
            rows.append([
                self.id,
                self.name,
                self.type.value,
                self.marketplace.value,
                product.id,
                product.name,
                product.brand,
                product.article,
                product.current_price,
                product.original_price or '',
                product.discount_percent or '',
                product.rating or '',
                product.reviews_count,
                'Да' if product.availability else 'Нет',
                product.url,
                product.last_updated.strftime('%Y-%m-%d %H:%M:%S')
            ])
        return rows
    
    @staticmethod
    def get_sheets_headers() -> List[str]:
        """
        Получение заголовков для Google Sheets.
        
        Returns:
            Список заголовков столбцов
        """
        return [
            'ID конкурента',
            'Название конкурента',
            'Тип конкурента',
            'Маркетплейс',
            'ID товара',
            'Название товара',
            'Бренд',
            'Артикул',
            'Текущая цена',
            'Первоначальная цена',
            'Скидка (%)',
            'Рейтинг',
            'Количество отзывов',
            'Доступность',
            'URL товара',
            'Последнее обновление'
        ]
    
    def __str__(self) -> str:
        """Строковое представление конкурента."""
        return f"Competitor(id='{self.id}', name='{self.name}', products={len(self.products)})"
    
    def __repr__(self) -> str:
        """Представление для отладки."""
        return f"Competitor(id='{self.id}', name='{self.name}', type={self.type.value}, products_count={len(self.products)})"


@dataclass
class CompetitorAnalysis:
    """
    Анализ конкурентов для конкретного товара.
    
    Attributes:
        product_id: ID анализируемого товара
        competitors: Список конкурентов
        analysis_date: Дата анализа
        market_position: Позиция на рынке
        price_recommendations: Рекомендации по ценообразованию
        metadata: Дополнительные метаданные анализа
    """
    
    product_id: str
    competitors: List[Competitor] = field(default_factory=list)
    analysis_date: datetime = field(default_factory=datetime.now)
    market_position: Optional[str] = None
    price_recommendations: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_competitor(self, competitor: Competitor) -> None:
        """Добавление конкурента в анализ."""
        self.competitors.append(competitor)
    
    def get_all_competitor_prices(self) -> List[float]:
        """Получение всех цен конкурентов."""
        prices = []
        for competitor in self.competitors:
            for product in competitor.get_available_products():
                if product.current_price > 0:
                    prices.append(product.current_price)
        return prices
    
    def calculate_market_position(self, our_price: float) -> str:
        """
        Расчет позиции на рынке относительно конкурентов.
        
        Args:
            our_price: Наша цена
            
        Returns:
            Описание позиции на рынке
        """
        competitor_prices = self.get_all_competitor_prices()
        
        if not competitor_prices:
            return "Нет данных о конкурентах"
        
        min_price = min(competitor_prices)
        max_price = max(competitor_prices)
        avg_price = statistics.mean(competitor_prices)
        
        if our_price < min_price:
            position = "Лидер по цене (самая низкая цена)"
        elif our_price > max_price:
            position = "Премиум сегмент (самая высокая цена)"
        elif our_price <= avg_price:
            position = "Ниже среднего (конкурентная цена)"
        else:
            position = "Выше среднего"
        
        self.market_position = position
        return position
    
    def generate_price_recommendations(self, our_price: float) -> Dict[str, Any]:
        """
        Генерация рекомендаций по ценообразованию.
        
        Args:
            our_price: Наша текущая цена
            
        Returns:
            Словарь с рекомендациями
        """
        competitor_prices = self.get_all_competitor_prices()
        
        if not competitor_prices:
            return {
                'status': 'no_data',
                'message': 'Недостаточно данных о конкурентах'
            }
        
        min_price = min(competitor_prices)
        max_price = max(competitor_prices)
        avg_price = statistics.mean(competitor_prices)
        median_price = statistics.median(competitor_prices)
        
        recommendations = {
            'current_price': our_price,
            'market_stats': {
                'min_competitor_price': min_price,
                'max_competitor_price': max_price,
                'avg_competitor_price': avg_price,
                'median_competitor_price': median_price,
                'competitors_count': len(competitor_prices)
            },
            'recommendations': []
        }
        
        # Рекомендации на основе позиции
        if our_price > max_price:
            recommendations['recommendations'].append({
                'type': 'price_reduction',
                'message': 'Рассмотрите снижение цены для повышения конкурентоспособности',
                'suggested_price': max_price * 0.95,
                'potential_savings': our_price - (max_price * 0.95)
            })
        elif our_price < min_price:
            recommendations['recommendations'].append({
                'type': 'price_increase',
                'message': 'Возможность повышения цены без потери конкурентоспособности',
                'suggested_price': min_price * 1.05,
                'potential_profit': (min_price * 1.05) - our_price
            })
        else:
            recommendations['recommendations'].append({
                'type': 'maintain',
                'message': 'Цена находится в конкурентном диапазоне',
                'suggested_price': our_price
            })
        
        self.price_recommendations = recommendations
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'product_id': self.product_id,
            'competitors': [c.to_dict() for c in self.competitors],
            'analysis_date': self.analysis_date.isoformat(),
            'market_position': self.market_position,
            'price_recommendations': self.price_recommendations,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompetitorAnalysis':
        """Создание объекта из словаря."""
        if isinstance(data['analysis_date'], str):
            data['analysis_date'] = datetime.fromisoformat(data['analysis_date'])
        
        competitors = [Competitor.from_dict(c_data) 
                      for c_data in data.get('competitors', [])]
        data['competitors'] = competitors
        
        return cls(**data)