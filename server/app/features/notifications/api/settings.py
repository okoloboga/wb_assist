"""
Settings API endpoints for notification management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.user.crud import UserCRUD
from app.features.notifications.crud import NotificationSettingsCRUD
from app.features.notifications.schemas import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    APIResponse
)

router = APIRouter()


@router.get("/settings", response_model=APIResponse)
async def get_notification_settings(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Get current notification settings for the user
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


@router.post("/settings", response_model=APIResponse)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Update notification settings for the user
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
