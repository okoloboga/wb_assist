"""
Валидаторы для Bot API эндпоинтов
"""

from typing import Optional
from pydantic import BaseModel, Field, validator
import re


class StocksQueryParams(BaseModel):
    """Валидация параметров для /stocks/all"""
    
    telegram_id: int = Field(..., gt=0, description="Telegram ID пользователя")
    limit: int = Field(15, ge=1, le=100, description="Количество товаров на странице")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    warehouse: Optional[str] = Field(None, max_length=500, description="Фильтр по складу")
    size: Optional[str] = Field(None, max_length=200, description="Фильтр по размеру")
    search: Optional[str] = Field(None, min_length=1, max_length=200, description="Поиск по названию или артикулу")
    
    @validator('warehouse')
    def validate_warehouse(cls, v):
        """Валидация формата складов"""
        if v is None:
            return v
        # Проверяем, что нет подозрительных символов
        if re.search(r'[<>{}[\]\\]', v):
            raise ValueError('Недопустимые символы в названии склада')
        return v
    
    @validator('size')
    def validate_size(cls, v):
        """Валидация формата размеров"""
        if v is None:
            return v
        # Проверяем, что нет подозрительных символов
        if re.search(r'[<>{}[\]\\]', v):
            raise ValueError('Недопустимые символы в размере')
        return v
    
    @validator('search')
    def validate_search(cls, v):
        """Валидация поискового запроса"""
        if v is None:
            return v
        # Удаляем лишние пробелы
        v = v.strip()
        if len(v) == 0:
            raise ValueError('Поисковый запрос не может быть пустым')
        # Проверяем, что нет SQL инъекций
        if re.search(r'(--|;|\/\*|\*\/|xp_|sp_|exec|execute|select|insert|update|delete|drop|create|alter)', v, re.IGNORECASE):
            raise ValueError('Недопустимые символы в поисковом запросе')
        return v


class AnalyticsQueryParams(BaseModel):
    """Валидация параметров для /analytics/sales"""
    
    telegram_id: int = Field(..., gt=0, description="Telegram ID пользователя")
    period: str = Field("30d", regex=r'^(7|30|60|90|180)d$', description="Период анализа")
    
    @validator('period')
    def validate_period(cls, v):
        """Валидация периода"""
        allowed_periods = ['7d', '30d', '60d', '90d', '180d']
        if v not in allowed_periods:
            raise ValueError(f'Период должен быть одним из: {", ".join(allowed_periods)}')
        return v


class OrdersQueryParams(BaseModel):
    """Валидация параметров для /orders/recent"""
    
    telegram_id: int = Field(..., gt=0, description="Telegram ID пользователя")
    limit: int = Field(10, ge=1, le=100, description="Количество заказов")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    status: Optional[str] = Field(None, regex=r'^(active|canceled)$', description="Фильтр по статусу")
    
    @validator('status')
    def validate_status(cls, v):
        """Валидация статуса заказа"""
        if v is None:
            return v
        allowed_statuses = ['active', 'canceled']
        if v not in allowed_statuses:
            raise ValueError(f'Статус должен быть одним из: {", ".join(allowed_statuses)}')
        return v


class ReviewsQueryParams(BaseModel):
    """Валидация параметров для /reviews/summary"""
    
    telegram_id: int = Field(..., gt=0, description="Telegram ID пользователя")
    limit: int = Field(10, ge=1, le=100, description="Количество отзывов")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    rating_threshold: Optional[int] = Field(None, ge=1, le=5, description="Фильтр по рейтингу")
    
    @validator('rating_threshold')
    def validate_rating(cls, v):
        """Валидация рейтинга"""
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Рейтинг должен быть от 1 до 5')
        return v


class TelegramIdParam(BaseModel):
    """Валидация telegram_id"""
    
    telegram_id: int = Field(..., gt=0, le=9999999999, description="Telegram ID пользователя")
    
    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        """Валидация формата telegram_id"""
        if v <= 0:
            raise ValueError('Telegram ID должен быть положительным числом')
        if v > 9999999999:
            raise ValueError('Некорректный формат Telegram ID')
        return v


class PaginationParams(BaseModel):
    """Базовая валидация пагинации"""
    
    limit: int = Field(15, ge=1, le=100, description="Количество элементов на странице")
    offset: int = Field(0, ge=0, le=10000, description="Смещение для пагинации")
    
    @validator('offset')
    def validate_offset(cls, v):
        """Валидация offset"""
        if v > 10000:
            raise ValueError('Максимальное смещение: 10000')
        return v
