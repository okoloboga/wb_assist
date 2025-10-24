"""
Bot API routes для интеграции с Telegram ботом
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.wb_api.cache_manager import WBCacheManager
from app.features.wb_api.sync_service import WBSyncService
from app.features.user.crud import UserCRUD
from app.features.notifications.crud import NotificationSettingsCRUD
from app.features.notifications.schemas import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    APIResponse
)
from .service import BotAPIService
from .schemas import (
    DashboardResponse, OrdersResponse, CriticalStocksAPIResponse, 
    ReviewsSummaryAPIResponse, AnalyticsSalesAPIResponse, SyncResponse, SyncStatusResponse,
    OrderDetailResponse, CabinetStatusResponse, CabinetConnectResponse, CabinetConnectRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bot API"])


def get_bot_service(db: Session = Depends(get_db)) -> BotAPIService:
    """Получение экземпляра BotAPIService"""
    cache_manager = WBCacheManager(db)
    sync_service = WBSyncService(db)
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
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_dashboard(user)
        
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
    status: Optional[str] = Query(None, description="Фильтр по статусу заказа (active/canceled)"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение последних заказов пользователя"""
    try:
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_recent_orders(user, limit, offset, status)
        
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
        
        # Получаем пользователя
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_critical_stocks(user, limit, offset)
        
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
        
        # Получаем пользователя
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_reviews_summary(user, limit, offset)
        
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
        
        # Получаем пользователя
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_analytics_sales(user, period)
        
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
        
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.start_sync(user)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return SyncResponse(
            status="success",
            message=result.get("telegram_text", "Синхронизация запущена"),
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
        
        result = await bot_service.get_sync_status()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return SyncStatusResponse(
            status="success",
            message=result.get("telegram_text", "Статус синхронизации получен"),
            sync_status=None,  # Пока не реализовано
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статуса синхронизации для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/orders/statistics")
async def get_orders_statistics(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение полной статистики по заказам"""
    try:
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_orders_statistics(user)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "data": result["data"],
            "telegram_text": result["telegram_text"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статистики заказов для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: int,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение детальной информации о заказе"""
    try:
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_order_detail(user, order_id)
        
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


# ===== WB КАБИНЕТЫ ENDPOINTS =====

@router.get("/cabinets/status", response_model=CabinetStatusResponse)
async def get_cabinet_status(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Получение статуса подключенных WB кабинетов"""
    try:
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        result = await bot_service.get_cabinet_status(user)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return CabinetStatusResponse(
            status="success",
            cabinets=result["data"]["cabinets"],
            total_cabinets=result["data"]["total_cabinets"],
            active_cabinets=result["data"]["active_cabinets"],
            last_check=result["data"]["last_check"],
            telegram_text=result["telegram_text"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статуса кабинетов для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.post("/cabinets/connect", response_model=CabinetConnectResponse)
async def connect_cabinet(
    request: CabinetConnectRequest,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    bot_service: BotAPIService = Depends(get_bot_service)
):
    """Подключение нового WB кабинета через API ключ"""
    try:
        logger.info(f"🔗 CONNECT_CABINET: Пользователь {telegram_id} пытается подключить кабинет с API ключом")
        logger.info(f"🔗 CONNECT_CABINET: API ключ: {request.api_key[:20]}...")
        
        user = await bot_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
        
        logger.info(f"🔗 CONNECT_CABINET: Пользователь найден/создан: {user['id']}")
        
        result = await bot_service.connect_cabinet(user, request.api_key)
        
        if not result["success"]:
            if "already connected" in result["error"].lower():
                raise HTTPException(status_code=409, detail=result["error"])
            elif "invalid" in result["error"].lower():
                raise HTTPException(status_code=400, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        # Обрабатываем структуру с data или без
        data = result.get("data", result)
        
        return CabinetConnectResponse(
            status="success",
            cabinet_id=data.get("cabinet_id"),
            cabinet_name=data.get("cabinet_name"),
            connected_at=data.get("connected_at"),
            api_key_status=data.get("api_key_status"),
            permissions=data.get("permissions"),
            validation=data.get("validation"),
            telegram_text=result.get("telegram_text")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка подключения кабинета для telegram_id {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


# ===== НАСТРОЙКИ УВЕДОМЛЕНИЙ ENDPOINTS =====

@router.get("/notifications/settings", response_model=APIResponse)
async def get_notification_settings(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """Get current notification settings for the user"""
    try:
        # Получаем пользователя по telegram_id
        user_crud = UserCRUD(db)
        user = user_crud.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Получаем настройки (должны существовать, так как создаются автоматически)
        settings_crud = NotificationSettingsCRUD()
        settings = settings_crud.get_user_settings(db, user.id)
        
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Notification settings should exist for user"
            )
        
        settings_data = NotificationSettingsResponse.model_validate(settings)
        
        return APIResponse(
            success=True,
            message="Settings retrieved successfully",
            data=settings_data.model_dump()
        )
        
    except HTTPException as e:
        return APIResponse(
            success=False,
            message=e.detail,
            error=e.detail
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Internal server error: {str(e)}",
            error=str(e)
        )


@router.post("/notifications/settings", response_model=APIResponse)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """Update notification settings for the user"""
    try:
        # Получаем пользователя по telegram_id
        user_crud = UserCRUD(db)
        user = user_crud.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Получаем настройки (должны существовать, так как создаются автоматически)
        settings_crud = NotificationSettingsCRUD()
        existing_settings = settings_crud.get_user_settings(db, user.id)
        if not existing_settings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Notification settings should exist for user"
            )
        
        # Обновляем настройки
        updated_settings = settings_crud.update_settings(
            db, 
            user.id, 
            settings_update.model_dump(exclude_unset=True)
        )
        
        settings_data = NotificationSettingsResponse.model_validate(updated_settings)
        
        return APIResponse(
            success=True,
            message="Settings updated successfully",
            data=settings_data.model_dump()
        )
        
    except HTTPException as e:
        return APIResponse(
            success=False,
            message=e.detail,
            error=e.detail
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Internal server error: {str(e)}",
            error=str(e)
        )