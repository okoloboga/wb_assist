"""
Мэппинг моделей в строки и заголовки для Google Sheets.

Выделено из models.competitor для снижения связанности и упрощения
поддержки.
"""

from typing import List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    # Только для подсказок типов, избегаем циклического импорта
    from competitive_analysis.price_monitoring.models.competitor import Competitor
    from competitive_analysis.price_monitoring.models.product import Product
    from competitive_analysis.price_monitoring.models.price_history import PriceHistory


def competitor_to_sheets_rows(competitor: 'Competitor') -> List[List[Any]]:
    """
    Преобразование Competitor в строки для Google Sheets.

    Returns:
        Список строк для записи в таблицу
    """
    rows: List[List[Any]] = []
    for product in competitor.products:
        rows.append([
            competitor.id,
            competitor.name,
            competitor.type.value,
            competitor.marketplace.value,
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
            product.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    return rows


def competitor_sheets_headers() -> List[str]:
    """
    Заголовки столбцов для экспорта конкурентов в Google Sheets.
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
        'Последнее обновление',
    ]


__all__ = [
    'competitor_to_sheets_rows',
    'competitor_sheets_headers',
    'product_to_sheets_row',
    'product_sheets_headers',
    'price_history_to_sheets_rows',
    'price_history_sheets_headers',
]


def product_to_sheets_row(product: 'Product') -> List[Any]:
    """
    Преобразование Product в строку для Google Sheets.
    Совпадает с логикой Product.to_sheets_row.
    """
    import json
    return [
        product.id,
        product.name,
        product.brand,
        product.article,
        product.sku,
        product.category,
        product.current_price,
        product.target_price or '',
        product.min_price or '',
        product.max_price or '',
        product.get_min_competitor_price() or '',
        product.get_max_competitor_price() or '',
        round(product.get_average_competitor_price(), 2) if product.get_average_competitor_price() else '',
        product.price_position,
        'Да' if product.is_price_in_range() else 'Нет',
        len(product.competitor_prices),
        product.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
        'Да' if product.tracking_enabled else 'Нет',
        product.price_threshold,
        ', '.join(product.tags) if product.tags else '',
        json.dumps(product.competitor_prices) if product.competitor_prices else '[]',
    ]


def product_sheets_headers() -> List[str]:
    """
    Заголовки столбцов для экспорта товаров в Google Sheets.
    Соответствуют Product.get_sheets_headers.
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
        'Цены конкурентов',
    ]


def price_history_to_sheets_rows(history: 'PriceHistory') -> List[List[Any]]:
    """
    Преобразование PriceHistory в строки для Google Sheets.
    Совпадает с логикой PriceHistory.to_sheets_rows.
    """
    rows: List[List[Any]] = []
    for entry in sorted(history.entries, key=lambda x: x.timestamp):
        rows.append([
            entry.product_id,
            entry.price,
            entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            entry.source.value,
            entry.change_type.value if entry.change_type else '',
            round(entry.change_percent, 2) if entry.change_percent else '',
            entry.previous_price or '',
            entry.notes or ''
        ])
    return rows


def price_history_sheets_headers() -> List[str]:
    """
    Заголовки столбцов для экспорта истории цен в Google Sheets.
    Соответствуют PriceHistory.get_sheets_headers.
    """
    return [
        'ID товара',
        'Цена',
        'Дата и время',
        'Источник',
        'Тип изменения',
        'Изменение (%)',
        'Предыдущая цена',
        'Заметки'
    ]