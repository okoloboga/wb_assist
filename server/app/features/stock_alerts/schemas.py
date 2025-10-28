"""
Pydantic схемы для системы динамических уведомлений по остаткам
"""

from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class DailySalesAnalyticsBase(BaseModel):
    """Базовая схема для аналитики продаж"""
    cabinet_id: int
    nm_id: int
    warehouse_name: str
    size: str
    date: date
    orders_count: int = 0
    quantity_ordered: int = 0


class DailySalesAnalyticsCreate(DailySalesAnalyticsBase):
    """Схема для создания записи аналитики"""
    pass


class DailySalesAnalyticsResponse(DailySalesAnalyticsBase):
    """Схема ответа с аналитикой продаж"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StockAlertHistoryBase(BaseModel):
    """Базовая схема для истории уведомлений"""
    cabinet_id: int
    user_id: int
    nm_id: int
    warehouse_name: str
    size: str
    alert_type: str = 'dynamic_stock'
    orders_last_24h: int
    current_stock: int
    days_remaining: float


class StockAlertHistoryCreate(StockAlertHistoryBase):
    """Схема для создания записи истории"""
    pass


class StockAlertHistoryResponse(StockAlertHistoryBase):
    """Схема ответа с историей уведомлений"""
    id: int
    notification_sent_at: datetime
    
    class Config:
        from_attributes = True


class StockPositionRisk(BaseModel):
    """Схема для позиции остатков с риском"""
    nm_id: int
    name: Optional[str] = None
    brand: Optional[str] = None
    warehouse_name: str
    size: str
    current_stock: int
    orders_last_24h: int
    days_remaining: float
    risk_level: str = Field(..., description="high/medium/low")


class RiskAnalysisResponse(BaseModel):
    """Схема ответа риск-анализа"""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_positions": 150,
                    "at_risk_positions": 5,
                    "positions": [
                        {
                            "nm_id": 12345,
                            "name": "Платье черное",
                            "brand": "BRAND",
                            "warehouse_name": "Москва",
                            "size": "L",
                            "current_stock": 7,
                            "orders_last_24h": 10,
                            "days_remaining": 0.7,
                            "risk_level": "high"
                        }
                    ]
                }
            }
        }


class SalesAnalyticsResponse(BaseModel):
    """Схема ответа аналитики продаж"""
    success: bool
    data: List[DailySalesAnalyticsResponse] = Field(default_factory=list)


class AlertHistoryResponse(BaseModel):
    """Схема ответа истории уведомлений"""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total": 25,
                    "alerts": [
                        {
                            "nm_id": 12345,
                            "warehouse_name": "Москва",
                            "size": "L",
                            "orders_last_24h": 10,
                            "current_stock": 7,
                            "days_remaining": 0.7,
                            "notification_sent_at": "2025-10-27T15:30:00+03:00"
                        }
                    ]
                }
            }
        }

