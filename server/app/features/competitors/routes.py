"""
API роуты для работы с конкурентами
"""

import os
import logging
import re
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...features.wb_api.models import WBCabinet
from ...features.bot_api.service import BotAPIService
from .crud import CompetitorLinkCRUD, CompetitorProductCRUD, CompetitorSemanticCoreCRUD
from .tasks import scrape_competitor_task, generate_semantic_core_task
from .schemas import (
    CompetitorsListResponse,
    CompetitorProductsResponse,
    AddCompetitorRequest,
    AddCompetitorResponse,
    CompetitorLinkResponse,
    CompetitorProductResponse,
    CompetitorProductDetailResponse
)
from pydantic import BaseModel # New import

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competitors", tags=["Competitors"])


class SemanticCoreGenerateRequest(BaseModel):
    category_name: str


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
        
        # Получаем список конкурентов (все статусы)
        competitors = CompetitorLinkCRUD.get_by_cabinet(
            db,
            cabinet.id,
            status=None,  # Убираем фильтр по статусу
            offset=offset,
            limit=limit
        )
        
        # Подсчитываем общее количество
        total_count = CompetitorLinkCRUD.count_by_cabinet(db, cabinet.id, status=None)
        has_more = (offset + limit) < total_count
        
        # Формируем ответ
        competitors_data = []
        for c in competitors:
            categories = CompetitorProductCRUD.get_distinct_categories_by_competitor(db, c.id)
            competitors_data.append(
                CompetitorLinkResponse(
                    id=c.id,
                    competitor_url=c.competitor_url,
                    competitor_name=c.competitor_name,
                    status=c.status,
                    products_count=c.products_count,
                    categories=categories, # Добавляем категории
                    last_scraped_at=c.last_scraped_at,
                    created_at=c.created_at
                )
            )
        
        telegram_text = None
        if competitors_data:
            telegram_text = f"📊 Конкуренты ({total_count}):\n\n"
            for i, comp in enumerate(competitors_data, 1):
                status_icon = {
                    "completed": "✅",
                    "scraping": "🔄",
                    "pending": "⏳",
                    "error": "❌"
                }.get(comp.status, "❓")
                
                telegram_text += f"{i}. {comp.competitor_name or 'Без названия'}\n"
                if comp.categories:
                    telegram_text += f"   Категории: {', '.join(comp.categories)}\n"
                else:
                    telegram_text += f"   Товаров: {comp.products_count}\n" # Если нет категорий, показываем количество товаров
                telegram_text += "\n"
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


@router.get("/products/{product_id}", response_model=CompetitorProductDetailResponse)
async def get_competitor_product_detail(
    product_id: int,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Получить детальную информацию о товаре конкурента.
    """
    try:
        # Проверяем, что у пользователя есть активный кабинет
        bot_service = BotAPIService(db, None, None)
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кабинет WB не найден"
            )

        # Получаем товар по ID
        product = CompetitorProductCRUD.get_by_id(db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Товар конкурента не найден"
            )

        # Проверяем, что товар принадлежит кабинету пользователя
        if product.competitor_link.cabinet_id != cabinet.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен"
            )

        # Формируем ответ
        product_data = CompetitorProductResponse.from_orm(product)
        
        # Формируем текст для Telegram
        telegram_text = f"📦 **{product_data.name or 'Без названия'}**\n\n"
        
        price_text = f"{product_data.current_price:.0f}₽" if product_data.current_price else "Цена не указана"
        if product_data.original_price and product_data.current_price:
            discount = int((1 - product_data.current_price / product_data.original_price) * 100)
            price_text += f" (было {product_data.original_price:.0f}₽, 📉 -{discount}%)"
        telegram_text += f"💰 **Цена:** {price_text}\n"
        
        if product_data.rating:
            telegram_text += f"⭐ **Рейтинг:** {product_data.rating}\n"
        
        if product_data.brand:
            telegram_text += f"🏢 **Бренд:** {product_data.brand}\n"
            
        if product_data.category:
            telegram_text += f"🗂️ **Категория:** {product_data.category}\n"
            
        telegram_text += f"\n🔗 [Ссылка на товар]({product_data.product_url})\n"
        
        if product_data.description:
            telegram_text += f"\n**Описание:**\n{product_data.description[:1000]}" # Ограничиваем длину

        return CompetitorProductDetailResponse(
            status="success",
            product=product_data,
            telegram_text=telegram_text
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера"
        )


@router.get("/{competitor_id}/categories", response_model=Dict[str, Any])
async def get_competitor_categories(
    competitor_id: int,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Получить список уникальных категорий товаров для конкурента.
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
        
        competitor = CompetitorLinkCRUD.get_by_id(db, competitor_id)
        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конкурент не найден"
            )
        
        if competitor.cabinet_id != cabinet.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен"
            )
        
        categories = CompetitorProductCRUD.get_distinct_categories_by_competitor(db, competitor_id)
        
        return {
            "status": "success",
            "categories": categories
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения категорий для конкурента {competitor_id}, telegram_id {telegram_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера"
        )


@router.delete("/{competitor_id}", status_code=status.HTTP_200_OK)
async def delete_competitor(
    competitor_id: int,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Удалить конкурента.
    """
    try:
        # Проверяем доступ к конкуренту
        bot_service = BotAPIService(db, None, None)
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кабинет WB не найден"
            )

        competitor = CompetitorLinkCRUD.get_by_id(db, competitor_id)
        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конкурент не найден"
            )

        if competitor.cabinet_id != cabinet.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен"
            )

        # Удаляем конкурента
        deleted = CompetitorLinkCRUD.delete(db, competitor_id)
        if not deleted:
            # Этого не должно произойти, если проверки выше прошли
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конкурент не найден для удаления"
            )

        logger.info(f"Удален конкурент {competitor_id} из кабинета {cabinet.id}")
        
        return {
            "status": "success",
            "message": f"Конкурент '{competitor.competitor_name or competitor.competitor_url}' успешно удален."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления конкурента {competitor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера"
        )


@router.post("/{competitor_id}/semantic-core", status_code=status.HTTP_202_ACCEPTED)
async def generate_semantic_core(
    competitor_id: int,
    request: SemanticCoreGenerateRequest,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Запустить генерацию семантического ядра для конкурента по выбранной категории.
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
        
        competitor = CompetitorLinkCRUD.get_by_id(db, competitor_id)
        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конкурент не найден"
            )
        
        if competitor.cabinet_id != cabinet.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен"
            )
        
        # Создаем запись в БД для семантического ядра
        semantic_core_entry = CompetitorSemanticCoreCRUD.create(
            db,
            competitor_link_id=competitor_id,
            category_name=request.category_name,
            status="pending"
        )
        
        # Запускаем Celery задачу
        generate_semantic_core_task.apply_async(args=[semantic_core_entry.id], queue='scraping_queue')
        
        logger.info(f"Запущена генерация семантического ядра для конкурента {competitor_id}, категория '{request.category_name}'. ID задачи: {semantic_core_entry.id}")
        
        return {
            "status": "accepted",
            "message": "Генерация семантического ядра запущена. Результат будет отправлен по завершении.",
            "semantic_core_id": semantic_core_entry.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка запуска генерации семантического ядра для конкурента {competitor_id}, telegram_id {telegram_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера"
        )

