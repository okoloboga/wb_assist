"""
Polling API для получения новых уведомлений
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.features.user.crud import UserCRUD
from app.features.notifications.notification_service import NotificationService
from app.features.notifications.schemas import PollingResponse, NotificationEvent

router = APIRouter()


@router.get("/poll", response_model=PollingResponse)
async def get_new_notifications(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    last_check: Optional[datetime] = Query(None, description="Время последней проверки"),
    db: Session = Depends(get_db)
):
    """
    Получение новых уведомлений для пользователя
    """
    try:
        # Получаем пользователя
        user_crud = UserCRUD(db)
        user = user_crud.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Если last_check не указан, берем текущее время (только новые события)
        if not last_check:
            last_check = datetime.now(timezone.utc)
        
        # Инициализируем notification service
        notification_service = NotificationService(db, None)
        
        # Получаем новые события
        events = await notification_service.get_new_events(
            user_id=user.id,
            last_check=last_check
        )
        
        return PollingResponse(
            success=True,
            events=events,
            last_check=datetime.now(timezone.utc),
            events_count=len(events)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/poll/batch", response_model=Dict[str, Any])
async def get_new_notifications_batch(
    telegram_ids: str = Query(..., description="Comma-separated telegram IDs"),
    last_check: Optional[datetime] = Query(None, description="Время последней проверки"),
    db: Session = Depends(get_db)
):
    """
    Получение новых уведомлений для нескольких пользователей (для оптимизации)
    """
    try:
        # Парсим telegram_ids
        try:
            user_telegram_ids = [int(tid.strip()) for tid in telegram_ids.split(',')]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid telegram_ids format"
            )
        
        # Если last_check не указан, берем текущее время (только новые события)
        if not last_check:
            last_check = datetime.now(timezone.utc)
        
        # Получаем пользователей
        user_crud = UserCRUD(db)
        users = []
        for telegram_id in user_telegram_ids:
            user = user_crud.get_user_by_telegram_id(telegram_id)
            if user:
                users.append(user)
        
        if not users:
            return {
                "success": True,
                "events": {},
                "last_check": datetime.now(timezone.utc),
                "total_events": 0
            }
        
        # Инициализируем notification service
        notification_service = NotificationService(db, None)
        
        # Получаем события для всех пользователей
        all_events = {}
        total_events = 0
        
        for user in users:
            events = await notification_service.get_new_events(
                user_id=user.id,
                last_check=last_check
            )
            all_events[str(user.telegram_id)] = events
            total_events += len(events)
        
        return {
            "success": True,
            "events": all_events,
            "last_check": datetime.now(timezone.utc),
            "total_events": total_events
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
