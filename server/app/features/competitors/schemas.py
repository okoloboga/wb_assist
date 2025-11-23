"""
Pydantic схемы для API конкурентов
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class CompetitorLinkResponse(BaseModel):
    """Схема ответа для ссылки конкурента"""
    id: int
    competitor_url: str
    competitor_name: Optional[str] = None
    status: str
    products_count: int
    last_scraped_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CompetitorProductResponse(BaseModel):
    """Схема ответа для товара конкурента"""
    id: int
    nm_id: str
    product_url: str
    name: Optional[str] = None
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    description: Optional[str] = None
    scraped_at: datetime

    class Config:
        from_attributes = True


class CompetitorsListResponse(BaseModel):
    """Схема ответа для списка конкурентов"""
    status: str
    competitors: List[CompetitorLinkResponse]
    pagination: Dict[str, Any]
    telegram_text: Optional[str] = None


class CompetitorProductsResponse(BaseModel):
    """Схема ответа для списка товаров конкурента"""
    status: str
    products: List[CompetitorProductResponse]
    pagination: Dict[str, Any]
    telegram_text: Optional[str] = None


class AddCompetitorRequest(BaseModel):
    """Схема запроса на добавление конкурента"""
    competitor_url: str = Field(..., description="URL страницы бренда или селлера")


class AddCompetitorResponse(BaseModel):
    """Схема ответа на добавление конкурента"""
    status: str
    message: str
    competitor_id: Optional[int] = None

