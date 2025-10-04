"""
Bot API routes для интеграции с Telegram ботом
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.wb_api.cache_manager import WBCacheManager
from app.features.wb_api.sync_service import WBSyncService
from .service import BotAPIService
from .schemas import (
    DashboardResponse, OrdersResponse, CriticalStocksAPIResponse, 
    ReviewsSummaryAPIResponse, AnalyticsSalesAPIResponse, SyncResponse, SyncStatusResponse,
    OrderDetailResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bot", tags=["Bot API"])


def get_bot_service(db: Session = Depends(get_db)) -> BotAPIService:
    """Получение экземпляра BotAPIService"""
    cache_manager = WBCacheManager(db)
    sync_service = WBSyncService(db, cache_manager)
    return BotAPIService(db, cache_manager, sync_service)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение общей сводки по кабинету WB"""
    try:
        # Получаем кабинет пользователя
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        # Получаем данные dashboard
        result = await bot_service.get_dashboard_data(cabinet)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return DashboardResponse(
            status="success",
            dashboard=result["data"],
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения dashboard для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/orders/recent", response_model=OrdersResponse)
async def get_recent_orders(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    limit: int = Query(10, ge=1, le=100, description="Количество заказов"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение последних заказов пользователя"""
    try:
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        result = await bot_service.get_recent_orders(cabinet, limit, offset)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return OrdersResponse(
            status="success",
            orders=result["data"].get("orders"),
            pagination=result["data"].get("pagination"),
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения заказов для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/stocks/critical", response_model=CriticalStocksAPIResponse)
async def get_critical_stocks(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    limit: int = Query(20, ge=1, le=100, description="Количество товаров"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение критичных остатков"""
    try:
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        result = await bot_service.get_critical_stocks(cabinet, limit, offset)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return CriticalStocksAPIResponse(
            status="success",
            stocks=result["data"],
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения критичных остатков для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/reviews/summary", response_model=ReviewsSummaryAPIResponse)
async def get_reviews_summary(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    limit: int = Query(10, ge=1, le=100, description="Количество отзывов"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение новых и проблемных отзывов"""
    try:
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        result = await bot_service.get_reviews_summary(cabinet, limit, offset)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return ReviewsSummaryAPIResponse(
            status="success",
            reviews=result["data"],
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения отзывов для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/analytics/sales", response_model=AnalyticsSalesAPIResponse)
async def get_analytics_sales(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    period: str = Query("7d", description="Период анализа (7d, 30d, 90d)"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение статистики продаж и аналитики"""
    try:
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        result = await bot_service.get_analytics_sales(cabinet, period)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return AnalyticsSalesAPIResponse(
            status="success",
            analytics=result["data"],
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения аналитики для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.post("/sync/start", response_model=SyncResponse)
async def start_sync(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Запуск ручной синхронизации данных"""
    try:
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        result = await bot_service.start_sync(cabinet)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return SyncResponse(
            status="success",
            message=result["message"],
            sync_id=result["data"].get("sync_id") if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка запуска синхронизации для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение статуса синхронизации"""
    try:
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        result = await bot_service.get_sync_status(cabinet)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return SyncStatusResponse(
            status="success",
            sync_status=result["data"],
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статуса синхронизации для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: int,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение детальной информации о заказе"""
    try:
        cabinet = await bot_service.get_user_cabinet(telegram_id)
        if not cabinet:
            raise HTTPException(status_code=404, detail="Кабинет WB не найден")
        
        result = await bot_service.get_order_detail(cabinet, order_id)
        
        if not result["success"]:
            if "не найден" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=500, detail=result["error"])
        
        return OrderDetailResponse(
            status="success",
            order=result["data"],
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения деталей заказа {order_id} для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")