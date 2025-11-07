"""
Pydantic схемы для digest API
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time, date


class ChannelReportCreate(BaseModel):
    """Схема создания настройки канала"""
    user_id: int
    cabinet_id: int
    chat_id: int
    chat_title: str
    chat_type: str
    report_time: str  # "HH:MM" format
    timezone: str = "Europe/Moscow"


class ChannelReportUpdate(BaseModel):
    """Схема обновления настройки канала"""
    report_time: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelReportResponse(BaseModel):
    """Схема ответа с данными канала"""
    id: int
    user_id: int
    cabinet_id: int
    chat_id: int
    chat_title: Optional[str]
    chat_type: Optional[str]
    report_time: str
    timezone: str
    is_active: bool
    last_sent_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DigestHistoryResponse(BaseModel):
    """Схема ответа с историей отправки"""
    id: int
    channel_report_id: int
    cabinet_id: int
    chat_id: int
    digest_date: date
    sent_at: datetime
    status: str
    error_message: Optional[str]
    message_id: Optional[int]
    retry_count: int
    
    class Config:
        from_attributes = True

