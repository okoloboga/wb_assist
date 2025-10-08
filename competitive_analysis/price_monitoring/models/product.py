"""
Модель товара для мониторинга цен конкурентов.

Содержит информацию о товаре, его ценах и ценах конкурентов,
а также методы для анализа позиции по цене.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING
import json

# Избегаем циклических импортов
if TYPE_CHECKING:
    from .price_history import PriceHistory
    from .competitor import Competitor, CompetitorAnalysis


@dataclass
class Product:
    """
    Модель товара для мониторинга цен.
    
    Attributes:
        id: Уникальный идентификатор товара
        name: Название товара
        brand: Бренд товара
        article: Артикул товара
        category: Категория товара
        current_price: Текущая цена товара
        competitor_prices: Список цен конкурентов
        last_updated: Время последнего обновления
        tracking_enabled: Включен ли мониторинг
        price_threshold: Порог изменения цены для уведомления (в процентах)
        marketplace_url: URL товара на маркетплейсе
        competitor_urls: Список URL конкурентов
        tags: Дополнительные теги для группировки
        price_history: История изменения цен
        competitors: Список связанных конкурентов
        competitor_analysis: Анализ конкурентов
    """
    
    id: str
    name: str
    brand: str
    article: str  # Артикул товара
    sku: str  # SKU товара (Stock Keeping Unit)
    category: str
    current_price: float
    target_price: Optional[float] = None  # Целевая цена для товара
    min_price: Optional[float] = None  # Минимальная допустимая цена
    max_price: Optional[float] = None  # Максимальная допустимая цена
    competitor_prices: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    tracking_enabled: bool = True
    price_threshold: float = 5.0  # Процент изменения для уведомления
    marketplace_url: Optional[str] = None
    competitor_urls: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Связи с другими моделями
    price_history: Optional['PriceHistory'] = None
    competitors: List['Competitor'] = field(default_factory=list)
    competitor_analysis: Optional['CompetitorAnalysis'] = None
    
    def __post_init__(self):
        """Постобработка после инициализации."""
        if isinstance(self.last_updated, str):
            self.last_updated = datetime.fromisoformat(self.last_updated)
        
        # Валидация данных при инициализации
        self.validate()
    
    def validate(self) -> None:
        """
        Валидация данных товара.
        
        Raises:
            ValueError: При некорректных данных
        """
        if not self.id or not self.id.strip():
            raise ValueError("ID товара не может быть пустым")
        
        if not self.name or not self.name.strip():
            raise ValueError("Название товара не может быть пустым")
        
        if not self.sku or not self.sku.strip():
            raise ValueError("SKU товара не может быть пустым")
        
        if self.current_price < 0:
            raise ValueError("Текущая цена не может быть отрицательной")
        
        if self.target_price is not None and self.target_price < 0:
            raise ValueError("Целевая цена не может быть отрицательной")
        
        if self.min_price is not None and self.min_price < 0:
            raise ValueError("Минимальная цена не может быть отрицательной")
        
        if self.max_price is not None and self.max_price < 0:
            raise ValueError("Максимальная цена не может быть отрицательной")
        
        if (self.min_price is not None and self.max_price is not None and 
            self.min_price > self.max_price):
            raise ValueError("Минимальная цена не может быть больше максильной")
        
        if self.price_threshold < 0:
            raise ValueError("Порог уведомлений не может быть отрицательным")
        
        # Валидация цен конкурентов
        for price in self.competitor_prices:
            if price < 0:
                raise ValueError("Цены конкурентов не могут быть отрицательными")
    
    def update_price(self, new_price: float) -> None:
        """
        Обновление текущей цены товара.
        
        Args:
            new_price: Новая цена товара
            
        Raises:
            ValueError: При некорректной цене
        """
        if new_price < 0:
            raise ValueError("Цена не может быть отрицательной")
        
        self.current_price = new_price
        self.last_updated = datetime.now()
    
    def is_price_in_range(self) -> bool:
        """
        Проверка, находится ли текущая цена в допустимом диапазоне.
        
        Returns:
            True если цена в допустимом диапазоне или диапазон не задан
        """
        if self.min_price is not None and self.current_price < self.min_price:
            return False
        
        if self.max_price is not None and self.current_price > self.max_price:
            return False
        
        return True
    
    def get_min_competitor_price(self) -> Optional[float]:
        """
        Минимальная цена среди конкурентов.
        
        Returns:
            Минимальная цена или None если нет данных о конкурентах
        """
        return min(self.competitor_prices) if self.competitor_prices else None
    
    def get_max_competitor_price(self) -> Optional[float]:
        """
        Максимальная цена среди конкурентов.
        
        Returns:
            Максимальная цена или None если нет данных о конкурентах
        """
        return max(self.competitor_prices) if self.competitor_prices else None
    
    def get_average_competitor_price(self) -> Optional[float]:
        """
        Средняя цена среди конкурентов.
        
        Returns:
            Средняя цена или None если нет данных о конкурентах
        """
        if not self.competitor_prices:
            return None
        return sum(self.competitor_prices) / len(self.competitor_prices)
    
    def get_median_competitor_price(self) -> Optional[float]:
        """
        Медианная цена среди конкурентов.
        
        Returns:
            Медианная цена или None если нет данных о конкурентах
        """
        if not self.competitor_prices:
            return None
        
        sorted_prices = sorted(self.competitor_prices)
        n = len(sorted_prices)
        
        if n % 2 == 0:
            return (sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2
        else:
            return sorted_prices[n//2]
    
    def get_price_position(self) -> str:
        """
        Позиция по цене относительно конкурентов.
        
        Returns:
            Строковое описание позиции по цене
        """
        if not self.competitor_prices:
            return "unknown"
        
        min_price = self.get_min_competitor_price()
        max_price = self.get_max_competitor_price()
        avg_price = self.get_average_competitor_price()
        
        if self.current_price <= min_price:
            return "lowest"
        elif self.current_price >= max_price:
            return "highest"
        elif self.current_price < avg_price:
            return "below_average"
        elif self.current_price > avg_price:
            return "above_average"
        else:
            return "average"
    
    def is_price_competitive(self, threshold_percent: float = 10.0) -> bool:
        """
        Проверка конкурентоспособности цены.
        
        Args:
            threshold_percent: Допустимое отклонение от средней цены в процентах
            
        Returns:
            True если цена конкурентоспособна
        """
        if not self.competitor_prices:
            return True  # Нет данных для сравнения
        
        min_price = self.get_min_competitor_price()
        max_price = self.get_max_competitor_price()
        
        if min_price is None or max_price is None:
            return True
        
        # Если цена ниже минимальной цены конкурентов, она всегда конкурентоспособна
        if self.current_price <= min_price:
            return True
        
        # Если цена выше максимальной цены конкурентов более чем на 5%, она не конкурентоспособна
        if self.current_price > max_price:
            max_diff_percent = ((self.current_price - max_price) / max_price) * 100
            return max_diff_percent <= 5.0  # Строгий лимит для цен выше максимальной
        
        # Если цена в диапазоне конкурентов, проверяем отклонение от средней
        avg_price = self.get_average_competitor_price()
        if avg_price:
            price_diff_percent = abs((self.current_price - avg_price) / avg_price * 100)
            return price_diff_percent <= threshold_percent
        
        return True
    
    @property
    def pricing_recommendations(self) -> Dict[str, Any]:
        """
        Получение рекомендаций по ценообразованию.
        
        Returns:
            Словарь с рекомендациями
        """
        return self.get_price_recommendations()

    @property
    def min_competitor_price(self) -> Optional[float]:
        """
        Минимальная цена среди конкурентов.
        
        Returns:
            Минимальная цена или None если нет данных о конкурентах
        """
        return self.get_min_competitor_price()
    
    @property
    def max_competitor_price(self) -> Optional[float]:
        """
        Максимальная цена среди конкурентов.
        
        Returns:
            Максимальная цена или None если нет данных о конкурентах
        """
        return self.get_max_competitor_price()
    
    @property
    def avg_competitor_price(self) -> Optional[float]:
        """
        Средняя цена среди конкурентов.
        
        Returns:
            Средняя цена или None если нет данных о конкурентах
        """
        return self.get_average_competitor_price()
    
    @property
    def median_competitor_price(self) -> Optional[float]:
        """
        Медианная цена среди конкурентов.
        
        Returns:
            Медианная цена или None если нет данных о конкурентах
        """
        return self.get_median_competitor_price()
    
    @property
    def price_position(self) -> str:
        """
        Позиция по цене относительно конкурентов.
        
        Returns:
            Строковое описание позиции по цене
        """
        if not self.competitor_prices:
            return "unknown"
        
        min_price = self.get_min_competitor_price()
        max_price = self.get_max_competitor_price()
        avg_price = self.get_average_competitor_price()
        
        if self.current_price <= min_price:
            return "lowest"
        elif self.current_price >= max_price:
            return "highest"
        elif self.current_price < avg_price:
            return "below_average"
        elif self.current_price > avg_price:
            return "above_average"
        else:
            return "average"
    
    def price_difference_percent(self, competitor_price: float) -> float:
        """
        Разница в цене с конкурентом в процентах.
        
        Args:
            competitor_price: Цена конкурента
            
        Returns:
            Разница в процентах (положительная если наша цена выше)
        """
        if competitor_price == 0:
            return 0.0
        
        return ((self.current_price - competitor_price) / competitor_price) * 100
    
    def avg_price_difference_percent(self) -> Optional[float]:
        """
        Средняя разница в цене с конкурентами в процентах.
        
        Returns:
            Средняя разница в процентах или None если нет данных
        """
        avg_price = self.avg_competitor_price
        if avg_price is None:
            return None
        
        return self.price_difference_percent(avg_price)
    
    def get_price_recommendations(self) -> Dict[str, Any]:
        """
        Получение рекомендаций по ценообразованию.
        
        Returns:
            Словарь с рекомендациями
        """
        if not self.competitor_prices:
            return {
                "action": "no_data",
                "recommended_price": self.current_price,
                "reason": "Нет данных о ценах конкурентов"
            }
        
        min_price = self.get_min_competitor_price()
        max_price = self.get_max_competitor_price()
        avg_price = self.get_average_competitor_price()
        median_price = self.get_median_competitor_price()
        
        recommendations = {
            "current_position": self.price_position,
            "competitor_stats": {
                "min": min_price,
                "max": max_price,
                "avg": round(avg_price, 2),
                "median": round(median_price, 2),
                "count": len(self.competitor_prices)
            },
            "price_difference": {
                "vs_min": self.price_difference_percent(min_price),
                "vs_max": self.price_difference_percent(max_price),
                "vs_avg": self.avg_price_difference_percent(),
                "vs_median": self.price_difference_percent(median_price)
            }
        }
        
        # Рекомендации по оптимизации
        if self.current_price > max_price:
            recommendations["action"] = "decrease"
            recommendations["recommended_price"] = round(avg_price * 0.95, 2)
            recommendations["reason"] = "Рассмотрите снижение цены для повышения конкурентоспособности"
        elif self.current_price < min_price:
            recommendations["action"] = "increase"
            recommendations["recommended_price"] = round(min_price * 0.98, 2)
            recommendations["reason"] = "Возможность повышения цены без потери конкурентоспособности"
        else:
            recommendations["action"] = "maintain"
            recommendations["recommended_price"] = self.current_price
            recommendations["reason"] = "Цена находится в конкурентном диапазоне"
        
        recommendations["recommendation"] = recommendations["reason"]
        recommendations["suggested_price"] = recommendations["recommended_price"]
        
        return recommendations
    
    def update_competitor_prices(self, new_prices: List[float]) -> None:
        """
        Обновление цен конкурентов.
        
        Args:
            new_prices: Новый список цен конкурентов
        """
        self.competitor_prices = [price for price in new_prices if price > 0]
        self.last_updated = datetime.now()
    
    def add_competitor_price(self, price: float, url: Optional[str] = None) -> None:
        """
        Добавление цены конкурента.
        
        Args:
            price: Цена конкурента
            url: URL товара конкурента (опционально)
        """
        if price > 0:
            self.competitor_prices.append(price)
            if url and url not in self.competitor_urls:
                self.competitor_urls.append(url)
            self.last_updated = datetime.now()
    
    def remove_competitor_price(self, price: float) -> bool:
        """
        Удаление цены конкурента.
        
        Args:
            price: Цена для удаления
            
        Returns:
            True если цена была удалена
        """
        if price in self.competitor_prices:
            self.competitor_prices.remove(price)
            self.last_updated = datetime.now()
            return True
        return False
    
    def add_competitor(self, competitor: 'Competitor') -> None:
        """
        Добавление конкурента к товару.
        
        Args:
            competitor: Объект конкурента
        """
        if competitor not in self.competitors:
            self.competitors.append(competitor)
            self.last_updated = datetime.now()
    
    def remove_competitor(self, competitor_id: str) -> bool:
        """
        Удаление конкурента по ID.
        
        Args:
            competitor_id: ID конкурента
            
        Returns:
            True если конкурент был удален
        """
        initial_count = len(self.competitors)
        self.competitors = [c for c in self.competitors if c.id != competitor_id]
        
        if len(self.competitors) < initial_count:
            self.last_updated = datetime.now()
            return True
        return False
    
    def get_competitor(self, competitor_id: str) -> Optional['Competitor']:
        """
        Получение конкурента по ID.
        
        Args:
            competitor_id: ID конкурента
            
        Returns:
            Объект конкурента или None
        """
        for competitor in self.competitors:
            if competitor.id == competitor_id:
                return competitor
        return None
    
    def set_price_history(self, price_history: 'PriceHistory') -> None:
        """
        Установка истории цен для товара.
        
        Args:
            price_history: Объект истории цен
        """
        self.price_history = price_history
        self.last_updated = datetime.now()
    
    def add_price_to_history(self, price: float, source: str = "manual", 
                           change_type: str = "update", notes: str = "") -> None:
        """
        Добавление записи в историю цен.
        
        Args:
            price: Цена
            source: Источник данных
            change_type: Тип изменения
            notes: Заметки
        """
        if self.price_history is None:
            # Создаем историю цен если её нет
            from .price_history import PriceHistory
            self.price_history = PriceHistory(product_id=self.id)
        
        self.price_history.add_entry(
            price=price,
            source=source,
            change_type=change_type,
            notes=notes
        )
        self.last_updated = datetime.now()
    
    def set_competitor_analysis(self, analysis: 'CompetitorAnalysis') -> None:
        """
        Установка анализа конкурентов.
        
        Args:
            analysis: Объект анализа конкурентов
        """
        self.competitor_analysis = analysis
        self.last_updated = datetime.now()
    
    def get_all_competitor_prices_from_objects(self) -> List[float]:
        """
        Получение всех цен конкурентов из связанных объектов.
        
        Returns:
            Список цен всех товаров конкурентов
        """
        prices = []
        for competitor in self.competitors:
            for product in competitor.get_available_products():
                if product.current_price > 0:
                    prices.append(product.current_price)
        return prices
    
    def sync_competitor_prices(self) -> None:
        """
        Синхронизация цен конкурентов из связанных объектов.
        Обновляет список competitor_prices на основе данных из объектов конкурентов.
        """
        new_prices = self.get_all_competitor_prices_from_objects()
        if new_prices != self.competitor_prices:
            self.competitor_prices = new_prices
            self.last_updated = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование в словарь для сериализации.
        
        Returns:
            Словарь с данными товара
        """
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'article': self.article,
            'sku': self.sku,
            'category': self.category,
            'current_price': self.current_price,
            'target_price': self.target_price,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'competitor_prices': self.competitor_prices,
            'last_updated': self.last_updated.isoformat(),
            'tracking_enabled': self.tracking_enabled,
            'price_threshold': self.price_threshold,
            'marketplace_url': self.marketplace_url,
            'competitor_urls': self.competitor_urls,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """
        Создание объекта из словаря.
        
        Args:
            data: Словарь с данными товара
            
        Returns:
            Объект Product
        """
        # Обработка даты
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        # Добавляем sku если его нет
        if 'sku' not in data:
            data['sku'] = data.get('article', '')
        
        return cls(**data)
    
    def to_json(self) -> str:
        """
        Преобразование в JSON строку.
        
        Returns:
            JSON строка
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Product':
        """
        Создание объекта из JSON строки.
        
        Args:
            json_str: JSON строка
            
        Returns:
            Объект Product
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_sheets_row(self) -> List[Any]:
        """
        Преобразование в строку для Google Sheets.
        
        Returns:
            Список значений для записи в таблицу
        """
        import json
        return [
            self.id,
            self.name,
            self.brand,
            self.article,
            self.sku,
            self.category,
            self.current_price,
            self.target_price or '',
            self.min_price or '',
            self.max_price or '',
            self.get_min_competitor_price() or '',
            self.get_max_competitor_price() or '',
            round(self.get_average_competitor_price(), 2) if self.get_average_competitor_price() else '',
            self.price_position,
            'Да' if self.is_price_in_range() else 'Нет',
            len(self.competitor_prices),
            self.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
            'Да' if self.tracking_enabled else 'Нет',
            self.price_threshold,
            ', '.join(self.tags) if self.tags else '',
            json.dumps(self.competitor_prices) if self.competitor_prices else '[]'
        ]
    
    @staticmethod
    def get_sheets_headers() -> List[str]:
        """
        Получение заголовков для Google Sheets.
        
        Returns:
            Список заголовков столбцов
        """
        return [
            'ID',
            'Название',
            'Бренд',
            'Артикул',
            'SKU',
            'Категория',
            'Текущая цена',
            'Целевая цена',
            'Мин. цена',
            'Макс. цена',
            'Мин. цена конкурентов',
            'Макс. цена конкурентов',
            'Средняя цена конкурентов',
            'Позиция по цене',
            'Цена в диапазоне',
            'Количество конкурентов',
            'Последнее обновление',
            'Отслеживание включено',
            'Порог цены',
            'Теги',
            'Цены конкурентов'
        ]
    
    def __str__(self) -> str:
        """Строковое представление товара."""
        return f"{self.brand} {self.name} ({self.article}) - {self.current_price}₽"
    
    def __repr__(self) -> str:
        """Представление для отладки."""
        return f"Product(id='{self.id}', name='{self.name}', price={self.current_price})"
    
    def __eq__(self, other) -> bool:
        """Сравнение товаров по ID."""
        if not isinstance(other, Product):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Хеширование товара по ID."""
        return hash(self.id)