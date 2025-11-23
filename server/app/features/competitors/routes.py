"""
API роуты для работы с конкурентами
"""

import os
import logging
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...features.wb_api.models import WBCabinet
from ...features.bot_api.service import BotAPIService
from .crud import CompetitorLinkCRUD, CompetitorProductCRUD
from .tasks import scrape_competitor_task
from .schemas import (
    CompetitorsListResponse,
    CompetitorProductsResponse,
    AddCompetitorRequest,
    AddCompetitorResponse,
    CompetitorLinkResponse,
    CompetitorProductResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competitors", tags=["Competitors"])


def validate_competitor_url(url: str) -> bool:
    """
    Валидация URL конкурента.
    Принимаются ссылки на бренды или селлеров Wildberries.
    """
    pattern = r'https?://(www\.)?wildberries\.ru/(brands|seller)/[\w\-]+'
    return bool(re.match(pattern, url))


@router.post("/add", response_model=AddCompetitorResponse)
async def add_competitor(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    request: AddCompetitorRequest = None,
    competitor_url: Optional[str] = Query(None, description="URL конкурента (устаревший параметр)"),
    db: Session = Depends(get_db)
):
    """
    Добавить ссылку конкурента.
    
    Валидирует URL, проверяет лимиты и дублирование,
    сохраняет в БД и запускает Celery задачу скрапинга.
    """
    try:
        # Поддержка старого формата (competitor_url в query) и нового (в body)
        url = request.competitor_url if request else competitor_url
        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL конкурента обязателен"
            )
        
        # Валидация URL
        if not validate_competitor_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат URL. Ожидается ссылка на бренд или селлера Wildberries"
            )
        
        # Получаем кабинет пользователя
        bot_service = BotAPIService(db, None, None)
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кабинет WB не найден"
            )
        
        # Проверка дублирования
        if CompetitorLinkCRUD.check_duplicate(db, cabinet.id, url):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Этот конкурент уже добавлен в кабинет"
            )
        
        # Проверка лимита
        if not CompetitorLinkCRUD.check_limit(db, cabinet.id):
            max_links = int(os.getenv("COMPETITOR_MAX_LINKS_PER_CABINET", "10"))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Достигнут лимит конкурентов ({max_links}). Удалите существующих перед добавлением новых."
            )
        
        # Создаем запись конкурента
        competitor = CompetitorLinkCRUD.create(db, cabinet.id, url)
        
        # Запускаем Celery задачу скрапинга
        scrape_competitor_task.delay(competitor.id)
        
        logger.info(f"Добавлен конкурент {competitor.id} для кабинета {cabinet.id}, запущен скрапинг")
        
        return AddCompetitorResponse(
            status="success",
            message="Конкурент добавлен. Скрапинг запустится автоматически.\n\nРезультаты появятся после завершения.",
            competitor_id=competitor.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка добавления конкурента для telegram_id {telegram_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера"
        )


@router.get("", response_model=CompetitorsListResponse)
async def get_competitors(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    limit: int = Query(10, ge=1, le=50, description="Количество конкурентов"),
    db: Session = Depends(get_db)
):
    """
    Получить список конкурентов кабинета с пагинацией.
    Возвращает только завершенные скрапингом конкуренты (status='completed').
    """
    try:
        # Получаем кабинет пользователя
        bot_service = BotAPIService(db, None, None)
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кабинет WB не найден"
            )
        
        # Получаем список конкурентов (только завершенные)
        competitors = CompetitorLinkCRUD.get_by_cabinet(
            db,
            cabinet.id,
            status='completed',
            offset=offset,
            limit=limit
        )
        
        # Подсчитываем общее количество
        total_count = CompetitorLinkCRUD.count_by_cabinet(db, cabinet.id, status='completed')
        has_more = (offset + limit) < total_count
        
        # Формируем ответ
        competitors_data = [
            CompetitorLinkResponse(
                id=c.id,
                competitor_url=c.competitor_url,
                competitor_name=c.competitor_name,
                status=c.status,
                products_count=c.products_count,
                last_scraped_at=c.last_scraped_at,
                created_at=c.created_at
            )
            for c in competitors
        ]
        
        telegram_text = None
        if competitors_data:
            telegram_text = f"📊 Конкуренты ({total_count}):\n\n"
            for i, comp in enumerate(competitors_data, 1):
                telegram_text += f"{i}. {comp.competitor_name or 'Без названия'}\n"
                telegram_text += f"   Товаров: {comp.products_count}\n\n"
        else:
            telegram_text = "📊 Конкуренты не найдены.\n\nОтправьте ссылку на бренд или селлера для добавления."
        
        return CompetitorsListResponse(
            status="success",
            competitors=competitors_data,
            pagination={
                "offset": offset,
                "limit": limit,
                "total": total_count,
                "has_more": has_more
            },
            telegram_text=telegram_text
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения конкурентов для telegram_id {telegram_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера"
        )


@router.get("/{competitor_id}/products", response_model=CompetitorProductsResponse)
async def get_competitor_products(
    competitor_id: int,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    limit: int = Query(10, ge=1, le=50, description="Количество товаров"),
    db: Session = Depends(get_db)
):
    """
    Получить товары конкурента с пагинацией.
    """
    try:
        # Проверяем доступ к конкуренту (принадлежит кабинету пользователя)
        bot_service = BotAPIService(db, None, None)
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кабинет WB не найден"
            )
        
        # Получаем конкурента
        competitor = CompetitorLinkCRUD.get_by_id(db, competitor_id)
        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конкурент не найден"
            )
        
        # Проверяем, что конкурент принадлежит кабинету пользователя
        if competitor.cabinet_id != cabinet.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен"
            )
        
        # Получаем товары
        products = CompetitorProductCRUD.get_by_competitor(
            db,
            competitor_id,
            offset=offset,
            limit=limit
        )
        
        # Подсчитываем общее количество
        total_count = CompetitorProductCRUD.count_by_competitor(db, competitor_id)
        has_more = (offset + limit) < total_count
        
        # Формируем ответ
        products_data = [
            CompetitorProductResponse(
                id=p.id,
                nm_id=p.nm_id,
                product_url=p.product_url,
                name=p.name,
                current_price=float(p.current_price) if p.current_price else None,
                original_price=float(p.original_price) if p.original_price else None,
                brand=p.brand,
                category=p.category,
                rating=float(p.rating) if p.rating else None,
                description=p.description,
                scraped_at=p.scraped_at
            )
            for p in products
        ]
        
        competitor_name = competitor.competitor_name or "Неизвестный"
        telegram_text = f"🛍️ Товары конкурента: {competitor_name}\n\n"
        
        if products_data:
            for i, prod in enumerate(products_data, 1):
                price_text = f"{prod.current_price:.0f}₽" if prod.current_price else "Цена не указана"
                if prod.original_price and prod.current_price:
                    discount = int((1 - prod.current_price / prod.original_price) * 100)
                    price_text += f" (было {prod.original_price:.0f}₽, -{discount}%)"
                
                telegram_text += f"{i}. {prod.name or 'Без названия'}\n"
                telegram_text += f"   {price_text}\n"
                if prod.rating:
                    telegram_text += f"   ⭐ {prod.rating}\n"
                telegram_text += "\n"
        else:
            telegram_text += "Товары не найдены."
        
        return CompetitorProductsResponse(
            status="success",
            products=products_data,
            pagination={
                "offset": offset,
                "limit": limit,
                "total": total_count,
                "has_more": has_more
            },
            telegram_text=telegram_text
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения товаров конкурента {competitor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера"
        )

