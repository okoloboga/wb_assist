"""
Шаблон отчета по ценам для мониторинга конкурентов.

Содержит классы и методы для создания структурированных отчетов
по ценам товаров, включая форматирование, условное форматирование
и экспорт в различные форматы.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
import json
from abc import ABC, abstractmethod

# Импорты моделей
from ..models.product import Product
from ..models.price_history import PriceHistory, PriceHistoryEntry
from ..models.competitor import Competitor


class ReportFormat(Enum):
    """Формат отчета."""
    GOOGLE_SHEETS = "google_sheets"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class PriceChangeIndicator(Enum):
    """Индикаторы изменения цен."""
    INCREASE = "increase"      # Рост цены
    DECREASE = "decrease"      # Снижение цены
    STABLE = "stable"         # Стабильная цена
    CRITICAL_HIGH = "critical_high"  # Критически высокая цена
    CRITICAL_LOW = "critical_low"    # Критически низкая цена


@dataclass
class ColorScheme:
    """Цветовая схема для условного форматирования."""
    
    # Цвета для изменений цен
    price_increase: str = "#FF6B6B"      # Красный - рост цены
    price_decrease: str = "#4ECDC4"      # Зеленый - снижение цены
    price_stable: str = "#95E1D3"        # Светло-зеленый - стабильная цена
    price_critical_high: str = "#FF3838" # Ярко-красный - критически высокая
    price_critical_low: str = "#FF8C42"  # Оранжевый - критически низкая
    
    # Цвета для конкурентной позиции
    competitive_advantage: str = "#A8E6CF"  # Светло-зеленый - преимущество
    competitive_parity: str = "#FFD93D"     # Желтый - паритет
    competitive_disadvantage: str = "#FFB3BA" # Розовый - отставание
    
    # Цвета для заголовков и границ
    header_bg: str = "#2C3E50"           # Темно-синий фон заголовка
    header_text: str = "#FFFFFF"         # Белый текст заголовка
    border: str = "#BDC3C7"              # Серая граница
    
    # Цвета для фона
    even_row: str = "#F8F9FA"            # Четные строки
    odd_row: str = "#FFFFFF"             # Нечетные строки


@dataclass
class ReportColumn:
    """Колонка отчета."""
    
    name: str                    # Название колонки
    key: str                     # Ключ для получения данных
    width: int = 100            # Ширина колонки
    format_type: str = "text"   # Тип форматирования (text, number, currency, percent, date)
    alignment: str = "left"     # Выравнивание (left, center, right)
    sortable: bool = True       # Можно ли сортировать
    filterable: bool = True     # Можно ли фильтровать
    visible: bool = True        # Видимость колонки
    conditional_formatting: bool = False  # Применять ли условное форматирование


@dataclass
class ReportRow:
    """Строка отчета."""
    
    data: Dict[str, Any]        # Данные строки
    style: Dict[str, str] = field(default_factory=dict)  # Стили строки
    metadata: Dict[str, Any] = field(default_factory=dict)  # Метаданные


class PriceReportTemplate:
    """
    Шаблон отчета по ценам.
    
    Основной класс для создания отчетов по мониторингу цен,
    включающий структуру таблицы, форматирование и экспорт.
    """
    
    def __init__(self, 
                 title: str = "Отчет по мониторингу цен",
                 color_scheme: Optional[ColorScheme] = None):
        """
        Инициализация шаблона отчета.
        
        Args:
            title: Заголовок отчета
            color_scheme: Цветовая схема для форматирования
        """
        self.title = title
        self.color_scheme = color_scheme or ColorScheme()
        self.columns = self._define_default_columns()
        self.rows: List[ReportRow] = []
        self.created_at = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def _define_default_columns(self) -> List[ReportColumn]:
        """Определяет структуру колонок по умолчанию."""
        return [
            ReportColumn(
                name="ID товара",
                key="product_id",
                width=120,
                format_type="text",
                alignment="left"
            ),
            ReportColumn(
                name="Название товара",
                key="product_name",
                width=250,
                format_type="text",
                alignment="left"
            ),
            ReportColumn(
                name="Бренд",
                key="brand",
                width=120,
                format_type="text",
                alignment="left"
            ),
            ReportColumn(
                name="Артикул",
                key="article",
                width=100,
                format_type="text",
                alignment="center"
            ),
            ReportColumn(
                name="Категория",
                key="category",
                width=150,
                format_type="text",
                alignment="left"
            ),
            ReportColumn(
                name="Текущая цена",
                key="current_price",
                width=120,
                format_type="currency",
                alignment="right",
                conditional_formatting=True
            ),
            ReportColumn(
                name="Предыдущая цена",
                key="previous_price",
                width=120,
                format_type="currency",
                alignment="right"
            ),
            ReportColumn(
                name="Изменение цены",
                key="price_change",
                width=120,
                format_type="currency",
                alignment="right",
                conditional_formatting=True
            ),
            ReportColumn(
                name="Изменение (%)",
                key="price_change_percent",
                width=100,
                format_type="percent",
                alignment="right",
                conditional_formatting=True
            ),
            ReportColumn(
                name="Мин. цена конкурентов",
                key="min_competitor_price",
                width=140,
                format_type="currency",
                alignment="right"
            ),
            ReportColumn(
                name="Макс. цена конкурентов",
                key="max_competitor_price",
                width=140,
                format_type="currency",
                alignment="right"
            ),
            ReportColumn(
                name="Средняя цена конкурентов",
                key="avg_competitor_price",
                width=150,
                format_type="currency",
                alignment="right"
            ),
            ReportColumn(
                name="Позиция по цене",
                key="price_position",
                width=120,
                format_type="text",
                alignment="center",
                conditional_formatting=True
            ),
            ReportColumn(
                name="Конкурентность",
                key="competitive_status",
                width=120,
                format_type="text",
                alignment="center",
                conditional_formatting=True
            ),
            ReportColumn(
                name="Последнее обновление",
                key="last_updated",
                width=150,
                format_type="date",
                alignment="center"
            ),
            ReportColumn(
                name="Статус мониторинга",
                key="tracking_status",
                width=130,
                format_type="text",
                alignment="center"
            )
        ]
    
    def add_product_data(self, product: Product) -> None:
        """
        Добавляет данные товара в отчет.
        
        Args:
            product: Объект товара для добавления в отчет
        """
        # Получаем предыдущую цену из истории
        previous_price = None
        price_change = None
        price_change_percent = None
        
        if product.price_history and len(product.price_history.entries) > 1:
            # Берем предпоследнюю запись как предыдущую цену
            previous_price = product.price_history.entries[-2].price
            price_change = product.current_price - previous_price
            if previous_price > 0:
                price_change_percent = (price_change / previous_price) * 100
        
        # Определяем конкурентный статус
        competitive_status = self._determine_competitive_status(product)
        
        # Формируем данные строки
        row_data = {
            "product_id": product.id,
            "product_name": product.name,
            "brand": product.brand,
            "article": product.article,
            "category": product.category,
            "current_price": product.current_price,
            "previous_price": previous_price,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "min_competitor_price": product.min_competitor_price,
            "max_competitor_price": product.max_competitor_price,
            "avg_competitor_price": product.avg_competitor_price,
            "price_position": product.price_position(),
            "competitive_status": competitive_status,
            "last_updated": product.last_updated.strftime("%Y-%m-%d %H:%M"),
            "tracking_status": "Активен" if product.tracking_enabled else "Неактивен"
        }
        
        # Определяем стили для условного форматирования
        row_style = self._apply_conditional_formatting(row_data)
        
        # Создаем строку отчета
        report_row = ReportRow(
            data=row_data,
            style=row_style,
            metadata={"product_id": product.id}
        )
        
        self.rows.append(report_row)
    
    def _determine_competitive_status(self, product: Product) -> str:
        """
        Определяет конкурентный статус товара.
        
        Args:
            product: Товар для анализа
            
        Returns:
            Статус конкурентности
        """
        if not product.competitor_prices:
            return "Нет данных"
        
        avg_competitor_price = product.avg_competitor_price
        if not avg_competitor_price:
            return "Нет данных"
        
        price_diff_percent = ((product.current_price - avg_competitor_price) / avg_competitor_price) * 100
        
        if price_diff_percent <= -10:
            return "Преимущество"
        elif price_diff_percent <= 10:
            return "Паритет"
        else:
            return "Отставание"
    
    def _apply_conditional_formatting(self, row_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Применяет условное форматирование к строке.
        
        Args:
            row_data: Данные строки
            
        Returns:
            Словарь стилей для строки
        """
        style = {}
        
        # Форматирование изменения цены
        price_change_percent = row_data.get("price_change_percent")
        if price_change_percent is not None:
            if price_change_percent > 10:
                style["price_change_percent"] = f"background-color: {self.color_scheme.price_critical_high}"
            elif price_change_percent > 0:
                style["price_change_percent"] = f"background-color: {self.color_scheme.price_increase}"
            elif price_change_percent < -10:
                style["price_change_percent"] = f"background-color: {self.color_scheme.price_critical_low}"
            elif price_change_percent < 0:
                style["price_change_percent"] = f"background-color: {self.color_scheme.price_decrease}"
            else:
                style["price_change_percent"] = f"background-color: {self.color_scheme.price_stable}"
        
        # Форматирование конкурентного статуса
        competitive_status = row_data.get("competitive_status")
        if competitive_status == "Преимущество":
            style["competitive_status"] = f"background-color: {self.color_scheme.competitive_advantage}"
        elif competitive_status == "Паритет":
            style["competitive_status"] = f"background-color: {self.color_scheme.competitive_parity}"
        elif competitive_status == "Отставание":
            style["competitive_status"] = f"background-color: {self.color_scheme.competitive_disadvantage}"
        
        # Форматирование позиции по цене
        price_position = row_data.get("price_position")
        if price_position == "Самая низкая":
            style["price_position"] = f"background-color: {self.color_scheme.competitive_advantage}"
        elif price_position == "Самая высокая":
            style["price_position"] = f"background-color: {self.color_scheme.competitive_disadvantage}"
        elif price_position in ["Ниже среднего", "Выше среднего"]:
            style["price_position"] = f"background-color: {self.color_scheme.competitive_parity}"
        
        return style
    
    def add_multiple_products(self, products: List[Product]) -> None:
        """
        Добавляет несколько товаров в отчет.
        
        Args:
            products: Список товаров для добавления
        """
        for product in products:
            self.add_product_data(product)
    
    def sort_by_column(self, column_key: str, reverse: bool = False) -> None:
        """
        Сортирует строки отчета по указанной колонке.
        
        Args:
            column_key: Ключ колонки для сортировки
            reverse: Обратная сортировка
        """
        def sort_key(row: ReportRow):
            value = row.data.get(column_key)
            # Обработка None значений
            if value is None:
                return float('-inf') if not reverse else float('inf')
            return value
        
        self.rows.sort(key=sort_key, reverse=reverse)
    
    def filter_rows(self, filter_func) -> List[ReportRow]:
        """
        Фильтрует строки отчета по заданному условию.
        
        Args:
            filter_func: Функция фильтрации
            
        Returns:
            Отфильтрованные строки
        """
        return [row for row in self.rows if filter_func(row)]
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Получает сводную статистику по отчету.
        
        Returns:
            Словарь со статистикой
        """
        if not self.rows:
            return {}
        
        # Собираем числовые данные
        current_prices = [row.data.get("current_price") for row in self.rows if row.data.get("current_price") is not None]
        price_changes = [row.data.get("price_change_percent") for row in self.rows if row.data.get("price_change_percent") is not None]
        
        # Подсчитываем статусы
        competitive_statuses = [row.data.get("competitive_status") for row in self.rows]
        status_counts = {}
        for status in competitive_statuses:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        statistics = {
            "total_products": len(self.rows),
            "avg_current_price": sum(current_prices) / len(current_prices) if current_prices else 0,
            "min_current_price": min(current_prices) if current_prices else 0,
            "max_current_price": max(current_prices) if current_prices else 0,
            "avg_price_change_percent": sum(price_changes) / len(price_changes) if price_changes else 0,
            "competitive_status_distribution": status_counts,
            "products_with_advantage": status_counts.get("Преимущество", 0),
            "products_with_parity": status_counts.get("Паритет", 0),
            "products_with_disadvantage": status_counts.get("Отставание", 0),
            "report_generated_at": self.created_at.isoformat()
        }
        
        return statistics
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует отчет в словарь.
        
        Returns:
            Словарь с данными отчета
        """
        return {
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "columns": [
                {
                    "name": col.name,
                    "key": col.key,
                    "width": col.width,
                    "format_type": col.format_type,
                    "alignment": col.alignment,
                    "sortable": col.sortable,
                    "filterable": col.filterable,
                    "visible": col.visible,
                    "conditional_formatting": col.conditional_formatting
                }
                for col in self.columns
            ],
            "rows": [
                {
                    "data": row.data,
                    "style": row.style,
                    "metadata": row.metadata
                }
                for row in self.rows
            ],
            "metadata": self.metadata,
            "summary_statistics": self.get_summary_statistics()
        }
    
    def to_json(self) -> str:
        """
        Преобразует отчет в JSON.
        
        Returns:
            JSON строка с данными отчета
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def to_sheets_data(self) -> Tuple[List[str], List[List[Any]]]:
        """
        Преобразует отчет в формат для Google Sheets.
        
        Returns:
            Кортеж (заголовки, данные строк)
        """
        # Заголовки
        headers = [col.name for col in self.columns if col.visible]
        
        # Данные строк
        rows_data = []
        for row in self.rows:
            row_data = []
            for col in self.columns:
                if col.visible:
                    value = row.data.get(col.key, "")
                    # Форматирование значений
                    if col.format_type == "currency" and isinstance(value, (int, float)):
                        value = f"{value:.2f} ₽"
                    elif col.format_type == "percent" and isinstance(value, (int, float)):
                        value = f"{value:.2f}%"
                    row_data.append(value)
            rows_data.append(row_data)
        
        return headers, rows_data
    
    def get_headers(self) -> List[str]:
        """
        Получает список заголовков колонок.
        
        Returns:
            Список заголовков
        """
        return [col.name for col in self.columns if col.visible]
    
    def clear_data(self) -> None:
        """Очищает данные отчета."""
        self.rows.clear()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Добавляет метаданные к отчету.
        
        Args:
            key: Ключ метаданных
            value: Значение метаданных
        """
        self.metadata[key] = value
    
    def __str__(self) -> str:
        """Строковое представление отчета."""
        return f"PriceReportTemplate(title='{self.title}', rows={len(self.rows)})"
    
    def __repr__(self) -> str:
        """Представление отчета для отладки."""
        return f"PriceReportTemplate(title='{self.title}', columns={len(self.columns)}, rows={len(self.rows)})"


class CompetitorComparisonTemplate(PriceReportTemplate):
    """
    Шаблон для сравнительного анализа конкурентов.
    
    Расширенная версия базового шаблона с дополнительными
    колонками для анализа конкурентов.
    """
    
    def __init__(self, 
                 title: str = "Сравнительный анализ конкурентов",
                 color_scheme: Optional[ColorScheme] = None):
        """
        Инициализация шаблона сравнительного анализа.
        
        Args:
            title: Заголовок отчета
            color_scheme: Цветовая схема
        """
        super().__init__(title, color_scheme)
        self.columns.extend(self._define_competitor_columns())
    
    def _define_competitor_columns(self) -> List[ReportColumn]:
        """Определяет дополнительные колонки для анализа конкурентов."""
        return [
            ReportColumn(
                name="Количество конкурентов",
                key="competitors_count",
                width=130,
                format_type="number",
                alignment="center"
            ),
            ReportColumn(
                name="Разброс цен конкурентов",
                key="price_range",
                width=150,
                format_type="currency",
                alignment="right"
            ),
            ReportColumn(
                name="Медианная цена",
                key="median_competitor_price",
                width=120,
                format_type="currency",
                alignment="right"
            ),
            ReportColumn(
                name="Отклонение от медианы (%)",
                key="median_deviation_percent",
                width=160,
                format_type="percent",
                alignment="right",
                conditional_formatting=True
            ),
            ReportColumn(
                name="Рекомендуемая цена",
                key="recommended_price",
                width=140,
                format_type="currency",
                alignment="right"
            ),
            ReportColumn(
                name="Потенциальная прибыль",
                key="potential_profit",
                width=140,
                format_type="currency",
                alignment="right",
                conditional_formatting=True
            )
        ]
    
    def add_product_data(self, product: Product) -> None:
        """
        Добавляет данные товара с расширенным анализом конкурентов.
        
        Args:
            product: Объект товара
        """
        # Вызываем базовый метод
        super().add_product_data(product)
        
        # Добавляем дополнительные данные для анализа конкурентов
        if self.rows:
            last_row = self.rows[-1]
            
            # Дополнительные расчеты
            competitors_count = len(product.competitor_prices)
            price_range = None
            median_price = product.median_competitor_price
            median_deviation_percent = None
            recommended_price = None
            potential_profit = None
            
            if product.min_competitor_price and product.max_competitor_price:
                price_range = product.max_competitor_price - product.min_competitor_price
            
            if median_price:
                median_deviation_percent = ((product.current_price - median_price) / median_price) * 100
                
                # Простая рекомендация: цена чуть ниже медианы
                recommended_price = median_price * 0.95
                potential_profit = recommended_price - product.current_price
            
            # Обновляем данные строки
            last_row.data.update({
                "competitors_count": competitors_count,
                "price_range": price_range,
                "median_competitor_price": median_price,
                "median_deviation_percent": median_deviation_percent,
                "recommended_price": recommended_price,
                "potential_profit": potential_profit
            })
            
            # Обновляем стили
            additional_styles = self._apply_competitor_formatting(last_row.data)
            last_row.style.update(additional_styles)
    
    def _apply_competitor_formatting(self, row_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Применяет дополнительное форматирование для анализа конкурентов.
        
        Args:
            row_data: Данные строки
            
        Returns:
            Дополнительные стили
        """
        style = {}
        
        # Форматирование отклонения от медианы
        median_deviation = row_data.get("median_deviation_percent")
        if median_deviation is not None:
            if abs(median_deviation) > 20:
                style["median_deviation_percent"] = f"background-color: {self.color_scheme.price_critical_high}"
            elif abs(median_deviation) > 10:
                style["median_deviation_percent"] = f"background-color: {self.color_scheme.price_increase}"
            else:
                style["median_deviation_percent"] = f"background-color: {self.color_scheme.price_stable}"
        
        # Форматирование потенциальной прибыли
        potential_profit = row_data.get("potential_profit")
        if potential_profit is not None:
            if potential_profit > 0:
                style["potential_profit"] = f"background-color: {self.color_scheme.competitive_advantage}"
            elif potential_profit < 0:
                style["potential_profit"] = f"background-color: {self.color_scheme.competitive_disadvantage}"
            else:
                style["potential_profit"] = f"background-color: {self.color_scheme.competitive_parity}"
        
        return style


# Фабрика для создания различных типов отчетов
class ReportTemplateFactory:
    """Фабрика для создания шаблонов отчетов."""
    
    @staticmethod
    def create_price_report(title: str = None, 
                          color_scheme: ColorScheme = None) -> PriceReportTemplate:
        """
        Создает базовый шаблон отчета по ценам.
        
        Args:
            title: Заголовок отчета
            color_scheme: Цветовая схема
            
        Returns:
            Шаблон отчета по ценам
        """
        return PriceReportTemplate(
            title=title or "Отчет по мониторингу цен",
            color_scheme=color_scheme
        )
    
    @staticmethod
    def create_competitor_comparison(title: str = None,
                                   color_scheme: ColorScheme = None) -> CompetitorComparisonTemplate:
        """
        Создает шаблон сравнительного анализа конкурентов.
        
        Args:
            title: Заголовок отчета
            color_scheme: Цветовая схема
            
        Returns:
            Шаблон сравнительного анализа
        """
        return CompetitorComparisonTemplate(
            title=title or "Сравнительный анализ конкурентов",
            color_scheme=color_scheme
        )
    
    @staticmethod
    def create_custom_report(columns: List[ReportColumn],
                           title: str = "Пользовательский отчет",
                           color_scheme: ColorScheme = None) -> PriceReportTemplate:
        """
        Создает пользовательский шаблон отчета.
        
        Args:
            columns: Список колонок
            title: Заголовок отчета
            color_scheme: Цветовая схема
            
        Returns:
            Пользовательский шаблон отчета
        """
        template = PriceReportTemplate(title=title, color_scheme=color_scheme)
        template.columns = columns
        return template