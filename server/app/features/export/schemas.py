"""
Pydantic схемы для экспорта данных в Google Sheets
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ExportStatus(str, Enum):
    """Статусы экспорта"""
    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMIT = "rate_limit"


class ExportDataType(str, Enum):
    """Типы данных для экспорта"""
    ORDERS = "orders"
    STOCKS = "stocks"
    REVIEWS = "reviews"


class ExportTokenCreate(BaseModel):
    """Схема для создания токена экспорта"""
    cabinet_id: int = Field(..., description="ID кабинета WB")
    user_id: int = Field(..., description="ID пользователя Telegram")


class ExportTokenResponse(BaseModel):
    """Схема ответа с токеном экспорта"""
    token: str = Field(..., description="Токен экспорта")
    cabinet_id: int = Field(..., description="ID кабинета WB")
    created_at: datetime = Field(..., description="Время создания токена")
    is_active: bool = Field(..., description="Активен ли токен")
    rate_limit_remaining: int = Field(..., description="Оставшиеся запросы в час")
    rate_limit_reset: Optional[datetime] = Field(None, description="Время сброса лимита")

    class Config:
        from_attributes = True


class ExportDataResponse(BaseModel):
    """Схема ответа с данными для экспорта"""
    data: List[Dict[str, Any]] = Field(..., description="Данные для экспорта")
    total_rows: int = Field(..., description="Общее количество строк")
    last_updated: Optional[datetime] = Field(None, description="Время последнего обновления данных")
    cabinet_id: int = Field(..., description="ID кабинета WB")
    data_type: ExportDataType = Field(..., description="Тип экспортируемых данных")


class ExportLogResponse(BaseModel):
    """Схема ответа с логом экспорта"""
    id: int = Field(..., description="ID лога")
    timestamp: datetime = Field(..., description="Время запроса")
    status: ExportStatus = Field(..., description="Статус запроса")
    data_type: ExportDataType = Field(..., description="Тип данных")
    rows_count: Optional[int] = Field(None, description="Количество экспортированных строк")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    response_time_ms: Optional[int] = Field(None, description="Время ответа в миллисекундах")

    class Config:
        from_attributes = True


class ExportStatsResponse(BaseModel):
    """Схема ответа со статистикой экспорта"""
    total_requests: int = Field(..., description="Общее количество запросов")
    successful_requests: int = Field(..., description="Успешные запросы")
    failed_requests: int = Field(..., description="Неудачные запросы")
    rate_limited_requests: int = Field(..., description="Запросы с превышением лимита")
    success_rate: float = Field(..., description="Процент успешных запросов")
    avg_response_time_ms: float = Field(..., description="Среднее время ответа в мс")
    last_24h_requests: int = Field(..., description="Запросы за последние 24 часа")
    most_requested_data_type: str = Field(..., description="Самый запрашиваемый тип данных")


class GoogleSheetsTemplateResponse(BaseModel):
    """Схема ответа с информацией о шаблоне Google Sheets"""
    template_id: str = Field(..., description="ID шаблона Google Sheets")
    template_url: str = Field(..., description="Ссылка на шаблон")
    created_at: datetime = Field(..., description="Время создания шаблона")
    sheets_count: int = Field(..., description="Количество листов в шаблоне")
    is_ready: bool = Field(..., description="Готов ли шаблон к использованию")


class ExportErrorResponse(BaseModel):
    """Схема ответа с ошибкой экспорта"""
    error: str = Field(..., description="Тип ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали ошибки")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время ошибки")


class CabinetValidationResponse(BaseModel):
    """Схема ответа для валидации кабинета"""
    is_valid: bool = Field(..., description="Валиден ли кабинет")
    cabinet_id: int = Field(..., description="ID кабинета")
    cabinet_name: Optional[str] = Field(None, description="Название кабинета")
    has_data: bool = Field(..., description="Есть ли данные для экспорта")
    last_sync: Optional[datetime] = Field(None, description="Время последней синхронизации")
    data_counts: Dict[str, int] = Field(default_factory=dict, description="Количество записей по типам данных")
