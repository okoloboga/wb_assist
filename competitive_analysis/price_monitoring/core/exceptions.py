"""
Кастомные исключения для модуля мониторинга цен.

Содержит специализированные исключения для различных типов ошибок
при работе с Google Sheets API и другими компонентами системы.
"""


class PriceMonitoringError(Exception):
    """Базовое исключение для модуля мониторинга цен."""
    pass


class GoogleSheetsError(PriceMonitoringError):
    """Базовое исключение для ошибок Google Sheets API."""
    pass


class AuthenticationError(GoogleSheetsError):
    """Ошибка аутентификации с Google API."""
    pass


class SpreadsheetNotFoundError(GoogleSheetsError):
    """Таблица не найдена."""
    pass


class SheetNotFoundError(GoogleSheetsError):
    """Лист не найден в таблице."""
    pass


class InvalidRangeError(GoogleSheetsError):
    """Некорректный диапазон ячеек."""
    pass


class QuotaExceededError(GoogleSheetsError):
    """Превышена квота запросов к API."""
    pass


class RateLimitError(GoogleSheetsError):
    """Превышен лимит частоты запросов."""
    pass


class NetworkError(GoogleSheetsError):
    """Ошибка сети при обращении к API."""
    pass


class DataValidationError(PriceMonitoringError):
    """Ошибка валидации данных."""
    pass


class ConfigurationError(PriceMonitoringError):
    """Ошибка конфигурации."""
    pass


class PriceMonitorError(PriceMonitoringError):
    """Ошибка в системе мониторинга цен."""
    pass


class ProductNotFoundError(PriceMonitorError):
    """Товар не найден в системе мониторинга."""
    pass


class InvalidPriceError(PriceMonitorError):
    """Некорректная цена товара."""
    pass


class CompetitorError(PriceMonitorError):
    """Ошибка при работе с конкурентами."""
    pass


class PriceHistoryError(PriceMonitorError):
    """Ошибка при работе с историей цен."""
    pass