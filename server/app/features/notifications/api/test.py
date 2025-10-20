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
        
        # Webhook удален - используется только polling
        # Инициализируем notification service
        notification_service = NotificationService(db, None)  # Redis не нужен для теста
        
        # Тестовые уведомления теперь отправляются через polling
        result = {"success": True, "message": "Test notification queued for polling"}
        
        return TestNotificationResponse(
            success=result.get("success", False),
            message=result.get("message", "Test notification processed"),
            notification_sent=result.get("notification_sent", False),
            webhook_url=bot_webhook_url,
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