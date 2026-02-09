"""
Pydantic схемы для каталога товаров
"""
from pydantic import BaseModel
from typing import Optional


# Product schemas (from Google Sheets)
class Product(BaseModel):
    product_id: str
    category: str
    name: str
    description: str
    wb_link: str
    ozon_url: Optional[str] = None
    shop_url: Optional[str] = None
    available_sizes: str
    collage_url: str
    photo_1_url: str
    photo_2_url: str
    photo_3_url: str
    photo_4_url: str
    photo_5_url: str
    photo_6_url: str


class Category(BaseModel):
    category_id: str
    category_name: str
    display_order: int
    emoji: str


# Favorite schemas
class FavoriteCreate(BaseModel):
    user_id: int
    product_id: str


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    product_id: str
    added_at: str

    class Config:
        from_attributes = True