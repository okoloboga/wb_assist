"""
Модель истории цен для отслеживания изменений цен товаров во времени.

Содержит информацию о ценовых изменениях, их источниках и методы
для анализа временных рядов цен.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import json
import statistics
from ..utils.sheets_mapping import (
    price_history_to_sheets_rows,
    price_history_sheets_headers,
)
from ..utils.serialization import (
    price_history_to_dict,
    price_history_from_dict_data,
    price_history_to_json,
    price_history_from_json_data,
)


class PriceChangeType(Enum):
    """Тип изменения цены."""
    INCREASE = "increase"  # Повышение цены
    DECREASE = "decrease"  # Снижение цены
    STABLE = "stable"     # Цена стабильна


class PriceSource(Enum):
    """Источник информации о цене."""
    MANUAL = "manual"           # Ручной ввод
    API = "api"                # API маркетплейса
    SCRAPING = "scraping"      # Парсинг сайта
    COMPETITOR = "competitor"   # Цена конкурента
    INTERNAL = "internal"      # Внутренняя система


@dataclass
class PriceHistoryEntry:
    """
    Запись в истории цен.
    
    Attributes:
        product_id: ID товара
        price: Цена на момент записи
        timestamp: Время записи
        source: Источник информации о цене
        change_type: Тип изменения цены
        change_percent: Процент изменения относительно предыдущей цены
        previous_price: Предыдущая цена
        notes: Дополнительные заметки
        metadata: Дополнительные метаданные
    """
    
    product_id: str
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    source: PriceSource = PriceSource.MANUAL
    change_type: Optional[PriceChangeType] = None
    change_percent: Optional[float] = None
    previous_price: Optional[float] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Автоматический расчет типа и процента изменения."""
        if self.previous_price is not None and self.change_type is None:
            if self.price > self.previous_price:
                self.change_type = PriceChangeType.INCREASE
            elif self.price < self.previous_price:
                self.change_type = PriceChangeType.DECREASE
            else:
                self.change_type = PriceChangeType.STABLE
        
        if self.previous_price is not None and self.change_percent is None:
            if self.previous_price > 0:
                self.change_percent = ((self.price - self.previous_price) / self.previous_price) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'product_id': self.product_id,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source.value,
            'change_type': self.change_type.value if self.change_type else None,
            'change_percent': self.change_percent,
            'previous_price': self.previous_price,
            'notes': self.notes,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceHistoryEntry':
        """Создание объекта из словаря."""
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        if data.get('source'):
            data['source'] = PriceSource(data['source'])
        
        if data.get('change_type'):
            data['change_type'] = PriceChangeType(data['change_type'])
        
        return cls(**data)


@dataclass
class PriceHistory:
    """
    История цен товара.
    
    Attributes:
        product_id: ID товара
        entries: Список записей истории цен
        created_at: Время создания истории
        updated_at: Время последнего обновления
    """
    
    product_id: str
    entries: List[PriceHistoryEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_price_entry(self, 
                       price: float, 
                       source: PriceSource = PriceSource.MANUAL,
                       notes: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> PriceHistoryEntry:
        """
        Добавление новой записи о цене.
        
        Args:
            price: Новая цена
            source: Источник информации
            notes: Дополнительные заметки
            metadata: Дополнительные метаданные
            
        Returns:
            Созданная запись
        """
        previous_price = self.get_latest_price()
        
        entry = PriceHistoryEntry(
            product_id=self.product_id,
            price=price,
            source=source,
            previous_price=previous_price,
            notes=notes,
            metadata=metadata or {}
        )
        
        self.entries.append(entry)
        self.updated_at = datetime.now()
        
        return entry
    
    def get_latest_price(self) -> Optional[float]:
        """Получение последней цены."""
        if not self.entries:
            return None
        return max(self.entries, key=lambda x: x.timestamp).price
    
    def get_price_at_date(self, target_date: datetime) -> Optional[float]:
        """
        Получение цены на определенную дату.
        
        Args:
            target_date: Целевая дата
            
        Returns:
            Цена на указанную дату или None
        """
        # Найти ближайшую запись до указанной даты
        valid_entries = [e for e in self.entries if e.timestamp <= target_date]
        if not valid_entries:
            return None
        
        return max(valid_entries, key=lambda x: x.timestamp).price
    
    def get_price_range(self, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> List[PriceHistoryEntry]:
        """
        Получение записей за определенный период.
        
        Args:
            start_date: Начальная дата (по умолчанию - все записи)
            end_date: Конечная дата (по умолчанию - текущая дата)
            
        Returns:
            Список записей за период
        """
        if start_date is None:
            start_date = datetime.min
        if end_date is None:
            end_date = datetime.now()
        
        return [
            entry for entry in self.entries
            if start_date <= entry.timestamp <= end_date
        ]
    
    def get_price_statistics(self, 
                           days: int = 30) -> Dict[str, Any]:
        """
        Получение статистики цен за последние N дней.
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь со статистикой
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        entries = self.get_price_range(start_date, end_date)
        
        if not entries:
            return {
                'period_days': days,
                'entries_count': 0,
                'min_price': None,
                'max_price': None,
                'avg_price': None,
                'median_price': None,
                'price_volatility': None,
                'total_change_percent': None
            }
        
        prices = [entry.price for entry in entries]
        
        # Сортировка по времени для расчета изменения
        sorted_entries = sorted(entries, key=lambda x: x.timestamp)
        first_price = sorted_entries[0].price
        last_price = sorted_entries[-1].price
        
        total_change_percent = None
        if first_price > 0:
            total_change_percent = ((last_price - first_price) / first_price) * 100
        
        # Волатильность как стандартное отклонение
        price_volatility = None
        if len(prices) > 1:
            price_volatility = statistics.stdev(prices)
        
        return {
            'period_days': days,
            'entries_count': len(entries),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': statistics.mean(prices),
            'median_price': statistics.median(prices),
            'price_volatility': price_volatility,
            'total_change_percent': total_change_percent,
            'first_price': first_price,
            'last_price': last_price
        }
    
    def get_price_trend(self, days: int = 7) -> str:
        """
        Определение тренда цены за последние N дней.
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Строка с описанием тренда
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        entries = self.get_price_range(start_date, end_date)
        
        if len(entries) < 2:
            return "Недостаточно данных"
        
        # Сортировка по времени
        sorted_entries = sorted(entries, key=lambda x: x.timestamp)
        first_price = sorted_entries[0].price
        last_price = sorted_entries[-1].price
        
        change_percent = ((last_price - first_price) / first_price) * 100
        
        if abs(change_percent) < 1:
            return "Стабильная"
        elif change_percent > 5:
            return "Растущая"
        elif change_percent > 1:
            return "Слабо растущая"
        elif change_percent < -5:
            return "Падающая"
        else:
            return "Слабо падающая"
    
    def detect_price_anomalies(self, 
                              threshold_percent: float = 20.0) -> List[PriceHistoryEntry]:
        """
        Обнаружение аномальных изменений цен.
        
        Args:
            threshold_percent: Порог изменения в процентах для определения аномалии
            
        Returns:
            Список записей с аномальными изменениями
        """
        anomalies = []
        
        for entry in self.entries:
            if (entry.change_percent is not None and 
                abs(entry.change_percent) >= threshold_percent):
                anomalies.append(entry)
        
        return anomalies
    
    def get_price_changes_by_source(self) -> Dict[str, List[PriceHistoryEntry]]:
        """
        Группировка изменений цен по источникам.
        
        Returns:
            Словарь с группировкой по источникам
        """
        changes_by_source = {}
        
        for entry in self.entries:
            source_key = entry.source.value
            if source_key not in changes_by_source:
                changes_by_source[source_key] = []
            changes_by_source[source_key].append(entry)
        
        return changes_by_source
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь (делегировано утилите)."""
        return price_history_to_dict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceHistory':
        """Создание объекта из словаря (нормализация через утилиту)."""
        normalized = price_history_from_dict_data(data)
        entries = [PriceHistoryEntry.from_dict(entry_data)
                   for entry_data in normalized.get('entries', [])]
        normalized['entries'] = entries
        return cls(**normalized)
    
    def to_json(self) -> str:
        """Преобразование в JSON строку (делегировано утилите)."""
        return price_history_to_json(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PriceHistory':
        """Создание объекта из JSON строки (нормализация через утилиту)."""
        normalized = price_history_from_json_data(json_str)
        return cls.from_dict(normalized)
    
    def to_sheets_rows(self) -> List[List[Any]]:
        """
        Преобразование в строки для Google Sheets.
        
        Returns:
            Список строк для записи в таблицу
        """
        return price_history_to_sheets_rows(self)
    
    @staticmethod
    def get_sheets_headers() -> List[str]:
        """
        Получение заголовков для Google Sheets.
        
        Returns:
            Список заголовков столбцов
        """
        return price_history_sheets_headers()
    
    def __str__(self) -> str:
        """Строковое представление истории цен."""
        latest_price = self.get_latest_price()
        return f"PriceHistory(product_id='{self.product_id}', entries={len(self.entries)}, latest_price={latest_price})"
    
    def __repr__(self) -> str:
        """Представление для отладки."""
        return f"PriceHistory(product_id='{self.product_id}', entries_count={len(self.entries)})"