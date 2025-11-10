"""
Модели базы данных для системы ежедневных сводок
"""
from sqlalchemy import Column, Integer, String, BigInteger, Time, Boolean, DateTime, Date, Text, ForeignKey, Index
from sqlalchemy.sql import func
from ...core.database import Base


class ChannelReport(Base):
    """Настройки каналов для отправки сводок"""
    __tablename__ = "channel_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)  # Telegram chat ID
    chat_title = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=True)  # channel, group, supergroup
    report_time = Column(Time, nullable=False)  # Время отправки (UTC)
    timezone = Column(String(50), nullable=False, default="Europe/Moscow")
    is_active = Column(Boolean, nullable=False, default=True)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Индексы
    __table_args__ = (
        Index('idx_active_time', 'is_active', 'report_time'),  # Для планировщика
        Index('idx_chat_cabinet', 'chat_id', 'cabinet_id', unique=True),  # Уникальность
    )
    
    def __repr__(self):
        return f"<ChannelReport {self.id} - {self.chat_title}>"


class DigestHistory(Base):
    """История отправленных сводок"""
    __tablename__ = "digest_history"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_report_id = Column(Integer, ForeignKey("channel_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    digest_date = Column(Date, nullable=False, index=True)  # За какой день сводка
    sent_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="sent")  # sent, failed, retry
    error_message = Column(Text, nullable=True)
    message_id = Column(BigInteger, nullable=True)  # ID сообщения в Telegram
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Индексы
    __table_args__ = (
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<DigestHistory {self.id} - {self.status}>"

