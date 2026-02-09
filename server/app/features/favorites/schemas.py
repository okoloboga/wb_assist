"""
Схемы для валидации избранных товаров
"""
from pydantic import BaseModel
from datetime import datetime


class FavoriteBase(BaseModel):
    product_id: str


class FavoriteCreate(FavoriteBase):
    user_telegram_id: int


class FavoriteResponse(FavoriteBase):
    id: int
    user_telegram_id: int
    added_at: datetime

    class Config:
        from_attributes = True
