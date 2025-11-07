"""
CRUD операции для digest feature
"""
import logging
from datetime import datetime, date, time as dt_time
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import ChannelReport, DigestHistory

logger = logging.getLogger(__name__)


class ChannelReportCRUD:
    """CRUD для настроек каналов"""
    
    @staticmethod
    def get_by_id(db: Session, channel_id: int) -> Optional[ChannelReport]:
        """Получить канал по ID"""
        return db.query(ChannelReport).filter(ChannelReport.id == channel_id).first()
    
    @staticmethod
    def get_by_chat_and_cabinet(db: Session, chat_id: int, cabinet_id: int) -> Optional[ChannelReport]:
        """Получить канал по chat_id и cabinet_id"""
        return db.query(ChannelReport).filter(
            ChannelReport.chat_id == chat_id,
            ChannelReport.cabinet_id == cabinet_id
        ).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> List[ChannelReport]:
        """Получить все каналы пользователя"""
        return db.query(ChannelReport).filter(ChannelReport.user_id == user_id).all()
    
    @staticmethod
    def get_all_active(db: Session) -> List[ChannelReport]:
        """Получить все активные каналы"""
        return db.query(ChannelReport).filter(ChannelReport.is_active == True).all()
    
    @staticmethod
    def get_active_by_time(db: Session, report_time: dt_time) -> List[ChannelReport]:
        """Получить все активные каналы для заданного времени"""
        return db.query(ChannelReport).filter(
            and_(
                ChannelReport.is_active == True,
                ChannelReport.report_time == report_time
            )
        ).all()
    
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        cabinet_id: int,
        chat_id: int,
        chat_title: str,
        chat_type: str,
        report_time: dt_time,
        timezone: str = "Europe/Moscow"
    ) -> ChannelReport:
        """Создать настройку канала"""
        channel = ChannelReport(
            user_id=user_id,
            cabinet_id=cabinet_id,
            chat_id=chat_id,
            chat_title=chat_title,
            chat_type=chat_type,
            report_time=report_time,
            timezone=timezone,
            is_active=True
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel
    
    @staticmethod
    def update(db: Session, channel_id: int, **kwargs) -> Optional[ChannelReport]:
        """Обновить настройки канала"""
        channel = ChannelReportCRUD.get_by_id(db, channel_id)
        if not channel:
            return None
        
        for key, value in kwargs.items():
            if hasattr(channel, key) and value is not None:
                setattr(channel, key, value)
        
        db.commit()
        db.refresh(channel)
        return channel
    
    @staticmethod
    def delete(db: Session, channel_id: int) -> bool:
        """Удалить канал"""
        channel = ChannelReportCRUD.get_by_id(db, channel_id)
        if not channel:
            return False
        
        db.delete(channel)
        db.commit()
        return True
    
    @staticmethod
    def update_last_sent(db: Session, channel_id: int, sent_at: datetime) -> bool:
        """Обновить время последней отправки"""
        channel = ChannelReportCRUD.get_by_id(db, channel_id)
        if not channel:
            return False
        
        channel.last_sent_at = sent_at
        db.commit()
        return True


class DigestHistoryCRUD:
    """CRUD для истории отправок"""
    
    @staticmethod
    def create(
        db: Session,
        channel_report_id: int,
        cabinet_id: int,
        chat_id: int,
        digest_date: date,
        status: str = "sent",
        message_id: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> DigestHistory:
        """Создать запись об отправке"""
        history = DigestHistory(
            channel_report_id=channel_report_id,
            cabinet_id=cabinet_id,
            chat_id=chat_id,
            digest_date=digest_date,
            sent_at=datetime.utcnow(),
            status=status,
            message_id=message_id,
            error_message=error_message
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    
    @staticmethod
    def get_by_channel(db: Session, channel_id: int, limit: int = 10) -> List[DigestHistory]:
        """Получить историю отправок для канала"""
        return db.query(DigestHistory).filter(
            DigestHistory.channel_report_id == channel_id
        ).order_by(DigestHistory.sent_at.desc()).limit(limit).all()

