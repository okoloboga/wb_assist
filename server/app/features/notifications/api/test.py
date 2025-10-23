"""
Test API endpoints for notification testing
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.user.crud import UserCRUD
from app.features.notifications.notification_service import NotificationService
from app.features.notifications.schemas import (
    TestNotificationData,
    TestNotificationResponse
)

router = APIRouter()


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    test_data: TestNotificationData,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Send a test notification to the user
    """
    try:
        # Получаем пользователя по telegram_id
        user_crud = UserCRUD(db)
        user = user_crud.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Инициализируем notification service
        notification_service = NotificationService()
        
        # Отправляем тестовое уведомление через webhook
        result = await notification_service.send_test_notification(
            db, user.id, test_data.notification_type, test_data.test_data
        )
        
        return TestNotificationResponse(
            success=result.get("success", False),
            message=result.get("message", "Test notification processed"),
            notification_sent=result.get("notification_sent", False),
            webhook_url=user.bot_webhook_url,
            error=result.get("error")
        )
        
    except HTTPException as e:
        return TestNotificationResponse(
            success=False,
            message=e.detail,
            notification_sent=False,
            error=e.detail
        )
    except Exception as e:
        return TestNotificationResponse(
            success=False,
            message=f"Internal server error: {str(e)}",
            notification_sent=False,
            error=str(e)
        )


@router.post("/trigger-sync-events")
async def trigger_sync_events(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Trigger sync events processing for testing
    """
    try:
        from app.features.user.crud import UserCRUD
        from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
        from app.features.wb_api.models import WBCabinet
        from app.features.notifications.notification_service import NotificationService
        from datetime import datetime, timedelta
        
        # Получаем пользователя
        user_crud = UserCRUD(db)
        user = user_crud.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Получаем кабинет пользователя
        cabinet_crud = CabinetUserCRUD()
        cabinet_ids = cabinet_crud.get_user_cabinets(db, user.id)
        if not cabinet_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cabinet not found"
            )
        
        # Берем первый кабинет пользователя
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_ids[0]).first()
        if not cabinet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cabinet not found"
            )
        
        # Симулируем синхронизацию
        previous_sync_at = cabinet.last_sync_at or (datetime.utcnow() - timedelta(hours=1))
        current_sync_at = datetime.utcnow()
        
        # Обновляем last_sync_at
        cabinet.last_sync_at = current_sync_at
        db.commit()
        
        # Запускаем обработку уведомлений
        notification_service = NotificationService(db)
        
        # Получаем данные для обработки уведомлений
        # Для тестирования используем пустые списки, так как основная логика уже исправлена
        result = await notification_service.process_sync_events(
            user.id, cabinet.id, [], [], [], [], [], []
        )
        
        return {
            "success": True,
            "message": "Sync events processed",
            "result": result,
            "previous_sync_at": previous_sync_at.isoformat(),
            "current_sync_at": current_sync_at.isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "result": None
        }