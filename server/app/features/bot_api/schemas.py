"""
Pydantic схемы для Bot API
"""

from pydantic import BaseModel, Field, field_validator, RootModel
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    """Типы уведомлений"""
    NEW_ORDER = "new_order"
    CRITICAL_STOCKS = "critical_stocks"
    LOW_RATING_REVIEW = "low_rating_review"
    UNANSWERED_QUESTION = "unanswered_question"


class Priority(str, Enum):
    """Приоритеты уведомлений"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BotAPIResponse(BaseModel):
    """Базовая схема ответа Bot API"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    telegram_text: Optional[str] = None
    error: Optional[str] = None


class DashboardData(BaseModel):
    """Данные для dashboard"""
    cabinet_name: str
    last_sync: str
    status: str
    products: Dict[str, int]
    orders_today: Dict[str, Union[int, float]]
    stocks: Dict[str, Union[int, str]]
    reviews: Dict[str, Union[int, float]]
    recommendations: List[str]


class OrderData(BaseModel):
    """Данные заказа"""
    id: int
    date: str
    amount: float
    product_name: str
    brand: str
    warehouse_from: str
    warehouse_to: str
    commission_percent: float
    rating: float
    # Новые поля из WB API
    spp_percent: Optional[float] = None
    customer_price: Optional[float] = None
    discount_percent: Optional[float] = None
    logistics_amount: Optional[float] = None


class OrdersStatistics(BaseModel):
    """Статистика заказов"""
    today_count: int
    today_amount: float
    average_check: float
    growth_percent: float
    amount_growth_percent: float


class PaginationData(BaseModel):
    """Данные пагинации"""
    limit: int
    offset: int
    total: int
    has_more: bool


class OrdersResponse(BaseModel):
    """Ответ с заказами"""
    orders: List[OrderData]
    statistics: OrdersStatistics
    pagination: PaginationData


class StockData(RootModel[Dict[str, int]]):
    """Данные остатков"""
    root: Dict[str, int]


class CriticalProduct(BaseModel):
    """Критичный товар"""
    nm_id: int
    name: str
    brand: str
    stocks: StockData
    critical_sizes: List[str]
    zero_sizes: List[str]
    sales_per_day: float
    price: float
    commission_percent: float
    days_left: Dict[str, int]


class ZeroProduct(BaseModel):
    """Товар с нулевыми остатками"""
    nm_id: int
    name: str
    brand: str
    stocks: StockData
    sales_per_day: float
    price: float
    commission_percent: float


class StocksSummary(BaseModel):
    """Сводка по остаткам"""
    critical_count: int
    zero_count: int
    attention_needed: int
    potential_losses: float


class CriticalStocksResponse(BaseModel):
    """Ответ с критичными остатками"""
    critical_products: List[CriticalProduct]
    zero_products: List[ZeroProduct]
    summary: StocksSummary
    recommendations: List[str]


class ReviewData(BaseModel):
    """Данные отзыва"""
    id: int
    nm_id: int
    text: Optional[str] = None
    rating: Optional[int] = None
    user_name: Optional[str] = None
    color: Optional[str] = None
    pros: Optional[str] = None
    cons: Optional[str] = None
    created_date: Optional[str] = None


class QuestionData(BaseModel):
    """Данные вопроса"""
    id: str
    product_name: str
    text: str
    time_ago: str


class ReviewsStatistics(BaseModel):
    """Статистика отзывов"""
    average_rating: float
    total_reviews: int
    answered_count: int
    answered_percent: float
    attention_needed: int
    new_today: int


class ReviewsResponse(BaseModel):
    """Ответ с отзывами"""
    new_reviews: List[ReviewData]
    unanswered_questions: List[QuestionData]
    statistics: ReviewsStatistics
    recommendations: List[str]


class SalesPeriod(BaseModel):
    """Период продаж"""
    count: int
    amount: float


class SalesPeriods(BaseModel):
    """Периоды продаж"""
    today: SalesPeriod
    yesterday: SalesPeriod
    days_7: SalesPeriod = Field(alias="7_days")
    days_30: SalesPeriod = Field(alias="30_days")
    days_90: SalesPeriod = Field(alias="90_days")


class SalesDynamics(BaseModel):
    """Динамика продаж"""
    yesterday_growth_percent: float
    week_growth_percent: float
    average_check: float
    conversion_percent: float


class TopProduct(BaseModel):
    """Топ товар"""
    nm_id: int
    name: str
    sales_count: int
    sales_amount: float
    rating: float
    stocks: StockData


class StocksSummaryAnalytics(BaseModel):
    """Сводка по остаткам для аналитики"""
    critical_count: int
    zero_count: int
    attention_needed: int
    total_products: int


class AnalyticsResponse(BaseModel):
    """Ответ с аналитикой"""
    sales_periods: SalesPeriods
    dynamics: SalesDynamics
    top_products: List[TopProduct]
    stocks_summary: StocksSummaryAnalytics
    recommendations: List[str]


class SyncUpdates(BaseModel):
    """Обновления синхронизации"""
    orders: Dict[str, int]
    stocks: Dict[str, int]
    reviews: Dict[str, int]
    products: Dict[str, int]
    analytics: Dict[str, Union[bool, int]]


class SyncStatistics(BaseModel):
    """Статистика синхронизации"""
    successful_today: int
    errors_today: int
    average_duration: float
    last_error: Optional[str]


class SyncStatusData(BaseModel):
    """Данные статуса синхронизации"""
    last_sync: str
    status: str
    duration_seconds: int
    cabinets_processed: int
    updates: SyncUpdates
    next_sync: str
    sync_mode: str
    interval_seconds: int
    statistics: SyncStatistics


class SyncStartData(BaseModel):
    """Данные запуска синхронизации"""
    sync_id: str
    status: str
    message: str


# Webhook схемы
class WebhookPayload(BaseModel):
    """Payload для webhook"""
    type: NotificationType
    telegram_id: int
    data: Dict[str, Any]
    telegram_text: str
    timestamp: datetime = Field(default_factory=datetime.now)


class NewOrderNotification(BaseModel):
    """Уведомление о новом заказе"""
    order_id: int
    date: str
    amount: float
    product_name: str
    brand: str
    warehouse_from: str
    warehouse_to: str
    today_stats: Dict[str, Union[int, float]]
    stocks: StockData


class CriticalStocksNotification(BaseModel):
    """Уведомление о критичных остатках"""
    products: List[CriticalProduct]


class WebhookResponse(BaseModel):
    """Ответ webhook"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class NotificationResult(BaseModel):
    """Результат отправки уведомления"""
    success: bool
    attempts: int
    status: str
    error: Optional[str] = None
    notification_id: Optional[str] = None


class QueueStats(BaseModel):
    """Статистика очереди"""
    queue_size: int
    total_processed: int
    total_successful: int
    total_failed: int
    success_rate: float


# Валидаторы
class BotAPISchemas:
    """Валидаторы для Bot API"""
    
    @staticmethod
    def validate_telegram_id(telegram_id: int) -> int:
        """Валидация telegram_id"""
        if telegram_id <= 0:
            raise ValueError("Telegram ID должен быть положительным числом")
        return telegram_id
    
    @staticmethod
    def validate_limit(limit: int) -> int:
        """Валидация лимита"""
        if limit <= 0:
            raise ValueError("Лимит должен быть положительным числом")
        if limit > 100:
            raise ValueError("Лимит не может превышать 100")
        return limit
    
    @staticmethod
    def validate_offset(offset: int) -> int:
        """Валидация смещения"""
        if offset < 0:
            raise ValueError("Смещение не может быть отрицательным")
        return offset
    
    @staticmethod
    def validate_period(period: str) -> str:
        """Валидация периода"""
        allowed_periods = ["7d", "30d", "90d"]
        if period not in allowed_periods:
            raise ValueError(f"Период должен быть одним из: {', '.join(allowed_periods)}")
        return period


# Схемы для запросов
class DashboardRequest(BaseModel):
    """Запрос dashboard"""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v):
        return BotAPISchemas.validate_telegram_id(v)


class OrdersRequest(BaseModel):
    """Запрос заказов"""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    limit: int = Field(10, ge=1, le=100, description="Количество заказов")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v):
        return BotAPISchemas.validate_telegram_id(v)


class CriticalStocksRequest(BaseModel):
    """Запрос критичных остатков"""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    limit: int = Field(20, ge=1, le=100, description="Количество товаров")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v):
        return BotAPISchemas.validate_telegram_id(v)


class ReviewsRequest(BaseModel):
    """Запрос отзывов"""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    limit: int = Field(10, ge=1, le=100, description="Количество отзывов")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v):
        return BotAPISchemas.validate_telegram_id(v)


class AnalyticsRequest(BaseModel):
    """Запрос аналитики"""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    period: str = Field("7d", description="Период анализа")
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v):
        return BotAPISchemas.validate_telegram_id(v)
    
    @field_validator('period')
    @classmethod
    def validate_period(cls, v):
        return BotAPISchemas.validate_period(v)


class SyncRequest(BaseModel):
    """Запрос синхронизации"""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v):
        return BotAPISchemas.validate_telegram_id(v)


# ===== СХЕМЫ ОТВЕТОВ ДЛЯ API ENDPOINTS =====

class DashboardResponse(BaseModel):
    """Ответ dashboard endpoint"""
    status: str
    message: Optional[str] = None
    dashboard: Optional[DashboardData] = None
    telegram_text: Optional[str] = None


class OrdersResponse(BaseModel):
    """Ответ orders/recent endpoint"""
    status: str
    message: Optional[str] = None
    orders: Optional[List[OrderData]] = None
    pagination: Optional[PaginationData] = None
    telegram_text: Optional[str] = None


class OrderDetailResponse(BaseModel):
    """Ответ orders/{order_id} endpoint"""
    status: str
    message: Optional[str] = None
    order: Optional[OrderData] = None
    telegram_text: Optional[str] = None


class CriticalStocksAPIResponse(BaseModel):
    """Ответ stocks/critical endpoint"""
    status: str
    message: Optional[str] = None
    stocks: Optional[CriticalStocksResponse] = None
    telegram_text: Optional[str] = None


class ReviewsSummaryAPIResponse(BaseModel):
    """Ответ reviews/summary endpoint"""
    status: str
    message: Optional[str] = None
    reviews: Optional[ReviewsResponse] = None
    telegram_text: Optional[str] = None


class AnalyticsSalesAPIResponse(BaseModel):
    """Ответ analytics/sales endpoint"""
    status: str
    message: Optional[str] = None
    analytics: Optional[AnalyticsResponse] = None
    telegram_text: Optional[str] = None


class SyncResponse(BaseModel):
    """Ответ sync/start endpoint"""
    status: str
    message: str
    sync_id: Optional[str] = None


class SyncStatusResponse(BaseModel):
    """Ответ sync/status endpoint"""
    status: str
    message: Optional[str] = None
    sync_status: Optional[SyncStatusData] = None
    telegram_text: Optional[str] = None


# ===== СХЕМЫ ДЛЯ WB КАБИНЕТОВ =====

class CabinetConnectRequest(BaseModel):
    """Запрос подключения кабинета"""
    api_key: str = Field(..., description="WB API ключ пользователя")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("API ключ должен содержать минимум 10 символов")
        return v.strip()


class CabinetStatusResponse(BaseModel):
    """Ответ cabinets/status endpoint"""
    status: str
    cabinets: Optional[List[Dict[str, Any]]] = None
    total_cabinets: int = 0
    active_cabinets: int = 0
    last_check: Optional[str] = None
    telegram_text: Optional[str] = None


class CabinetConnectResponse(BaseModel):
    """Ответ cabinets/connect endpoint"""
    status: str
    cabinet_id: Optional[str] = None
    cabinet_name: Optional[str] = None
    connected_at: Optional[str] = None
    api_key_status: Optional[str] = None
    permissions: Optional[List[str]] = None
    validation: Optional[Dict[str, Any]] = None
    telegram_text: Optional[str] = None