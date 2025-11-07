"""
FastAPI эндпоинты для digest feature
"""
import logging
from datetime import datetime, date, time as dt_time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet
from app.features.wb_api.models_cabinet_users import CabinetUser

from .schemas import ChannelReportCreate, ChannelReportUpdate, ChannelReportResponse
from .crud import ChannelReportCRUD
from .service import DigestService
from .formatter import DigestFormatter

router = APIRouter(prefix="/channels", tags=["channels"])
logger = logging.getLogger(__name__)


def parse_time(time_str: str) -> dt_time:
    """Парсинг времени из строки HH:MM"""
    try:
        hour, minute = map(int, time_str.split(":"))
        return dt_time(hour=hour, minute=minute)
    except:
        raise ValueError(f"Invalid time format: {time_str}")


@router.post("/", response_model=ChannelReportResponse)
async def create_channel_report(
    data: ChannelReportCreate,
    telegram_id: int = Query(None),
    db: Session = Depends(get_db)
):
    """Создать настройку канала"""
    try:
        # Если передан telegram_id, находим user_id
        if telegram_id:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user_id = user.id
        else:
            # Иначе используем user_id из data
            user = db.query(User).filter(User.id == data.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user_id = data.user_id
        
        # Проверяем кабинет
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == data.cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Проверяем доступ пользователя к кабинету
        cabinet_user = db.query(CabinetUser).filter(
            CabinetUser.cabinet_id == data.cabinet_id,
            CabinetUser.user_id == user_id
        ).first()
        if not cabinet_user:
            raise HTTPException(status_code=403, detail="User does not have access to this cabinet")
        
        # Парсим время
        report_time = parse_time(data.report_time)
        
        # Проверяем, существует ли уже канал с таким chat_id и cabinet_id
        existing_channel = ChannelReportCRUD.get_by_chat_and_cabinet(
            db=db,
            chat_id=data.chat_id,
            cabinet_id=data.cabinet_id
        )
        
        if existing_channel:
            # Обновляем существующий канал
            channel = ChannelReportCRUD.update(
                db=db,
                channel_id=existing_channel.id,
                chat_title=data.chat_title,
                chat_type=data.chat_type,
                report_time=report_time,
                timezone=data.timezone,
                is_active=True  # Активируем при обновлении
            )
        else:
            # Создаем новый канал
            channel = ChannelReportCRUD.create(
                db=db,
                user_id=user_id,
                cabinet_id=data.cabinet_id,
                chat_id=data.chat_id,
                chat_title=data.chat_title,
                chat_type=data.chat_type,
                report_time=report_time,
                timezone=data.timezone
            )
        
        # Форматируем ответ - преобразуем time в строку перед созданием ответа
        response_data = ChannelReportResponse(
            id=channel.id,
            user_id=channel.user_id,
            cabinet_id=channel.cabinet_id,
            chat_id=channel.chat_id,
            chat_title=channel.chat_title,
            chat_type=channel.chat_type,
            report_time=channel.report_time.strftime("%H:%M"),  # Преобразуем time в строку
            timezone=channel.timezone,
            is_active=channel.is_active,
            last_sent_at=channel.last_sent_at,
            created_at=channel.created_at
        )
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating channel report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=dict)
async def get_user_channels(
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Получить список каналов пользователя"""
    try:
        # Получаем пользователя по telegram_id
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return {"success": True, "channels": [], "total": 0}
        
        # Получаем каналы
        channels = ChannelReportCRUD.get_by_user(db, user.id)
        
        # Форматируем ответ
        channels_data = []
        for channel in channels:
            channels_data.append({
                "id": channel.id,
                "cabinet_id": channel.cabinet_id,
                "chat_title": channel.chat_title,
                "report_time": channel.report_time.strftime("%H:%M"),
                "is_active": channel.is_active,
                "last_sent_at": channel.last_sent_at.isoformat() if channel.last_sent_at else None
            })
        
        return {
            "success": True,
            "channels": channels_data,
            "total": len(channels_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting user channels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{channel_id}", response_model=ChannelReportResponse)
async def get_channel_detail(
    channel_id: int,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Получить детальную информацию о канале"""
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Получаем канал
        channel = ChannelReportCRUD.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Проверяем владельца
        if channel.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Форматируем ответ
        response_data = ChannelReportResponse(
            id=channel.id,
            user_id=channel.user_id,
            cabinet_id=channel.cabinet_id,
            chat_id=channel.chat_id,
            chat_title=channel.chat_title,
            chat_type=channel.chat_type,
            report_time=channel.report_time.strftime("%H:%M"),
            timezone=channel.timezone,
            is_active=channel.is_active,
            last_sent_at=channel.last_sent_at,
            created_at=channel.created_at
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{channel_id}", response_model=ChannelReportResponse)
async def update_channel_report(
    channel_id: int,
    data: ChannelReportUpdate,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Обновить настройки канала"""
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Получаем канал
        channel = ChannelReportCRUD.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Проверяем владельца
        if channel.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Обновляем
        update_data = {}
        if data.report_time:
            update_data["report_time"] = parse_time(data.report_time)
        if data.is_active is not None:
            update_data["is_active"] = data.is_active
        
        updated_channel = ChannelReportCRUD.update(db, channel_id, **update_data)
        if not updated_channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Форматируем ответ - преобразуем time в строку перед созданием ответа
        response_data = ChannelReportResponse(
            id=updated_channel.id,
            user_id=updated_channel.user_id,
            cabinet_id=updated_channel.cabinet_id,
            chat_id=updated_channel.chat_id,
            chat_title=updated_channel.chat_title,
            chat_type=updated_channel.chat_type,
            report_time=updated_channel.report_time.strftime("%H:%M"),  # Преобразуем time в строку
            timezone=updated_channel.timezone,
            is_active=updated_channel.is_active,
            last_sent_at=updated_channel.last_sent_at,
            created_at=updated_channel.created_at
        )
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating channel report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{channel_id}")
async def delete_channel_report(
    channel_id: int,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Удалить канал"""
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Получаем канал
        channel = ChannelReportCRUD.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Проверяем владельца
        if channel.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Удаляем
        success = ChannelReportCRUD.delete(db, channel_id)
        
        if success:
            return {"success": True, "message": "Channel deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete channel")
        
    except Exception as e:
        logger.error(f"Error deleting channel report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/digest/daily")
async def get_daily_digest(
    cabinet_id: int = Query(...),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Получить ежедневную сводку"""
    try:
        # Парсим дату если указана
        target_date = None
        if date:
            target_date = datetime.fromisoformat(date).date()
        
        # Получаем данные
        service = DigestService(db)
        data = service.get_daily_digest(cabinet_id, target_date)
        
        # Форматируем текст (по умолчанию МСК)
        telegram_text = DigestFormatter.format_daily_digest(data, "Europe/Moscow")
        
        return {
            "success": True,
            "data": data,
            "telegram_text": telegram_text
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting daily digest: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

