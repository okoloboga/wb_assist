"""
API endpoints для работы с каталогом товаров
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional

from app.features.catalog.schemas import Product, Category
from app.services.sheets_service import sheets_service
import logging

logger = logging.getLogger(__name__)
logger.info("'app.services.sheets_service.sheets_service' imported and instantiated.")

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/categories", response_model=List[Category])
async def get_categories():
    """Получить список категорий"""
    categories = sheets_service.get_categories()
    return categories


@router.get("/products", response_model=List[Product])
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category ID")
):
    """Получить список товаров"""
    if category:
        products = sheets_service.get_products_by_category(category)
    else:
        # Возвращаем все товары
        all_products = []
        categories = sheets_service.get_categories()
        for cat in categories:
            products = sheets_service.get_products_by_category(cat['category_id'])
            all_products.extend(products)
        return all_products

    return products


@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """Получить информацию о товаре"""
    product = sheets_service.get_product_by_id(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.post("/refresh-cache")
async def refresh_cache():
    """Очистить кеш Google Sheets"""
    sheets_service.clear_cache()
    return {"status": "ok", "message": "Cache cleared"}