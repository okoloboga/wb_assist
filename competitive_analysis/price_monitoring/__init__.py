"""
Модуль мониторинга цен конкурентов и анализа рекламных ставок.

Этот модуль предоставляет функциональность для:
- Мониторинга цен конкурентов на маркетплейсах
- Анализа рекламных ставок по ключевым словам
- Интеграции с Google Sheets для отчетности
- Системы уведомлений об изменениях цен

Основные компоненты:
- GoogleSheetsClient: клиент для работы с Google Sheets API
- Product: модель товара с ценами конкурентов
- PriceMonitor: основная логика мониторинга цен
- CompetitorAnalyzer: анализ конкурентов
"""

__version__ = "1.0.0"
__author__ = "WB Assistant Team"

from .core.google_sheets_client import GoogleSheetsClient
from .models.product import Product

__all__ = [
    "GoogleSheetsClient",
    "Product",
]