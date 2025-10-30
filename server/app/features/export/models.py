"""
Модели данных для экспорта в Google Sheets
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Float, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import secrets
import hashlib

from ...core.database import Base


class ExportToken(Base):
    """Модель токена экспорта для Google Sheets"""
    __tablename__ = "export_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user ID
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit_remaining = Column(Integer, default=60, nullable=False)  # 60 запросов в час
    rate_limit_reset = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    cabinet = relationship("WBCabinet", backref="export_tokens")
    logs = relationship("ExportLog", back_populates="token", cascade="all, delete-orphan")

    # Индексы и ограничения
    __table_args__ = (
        Index('idx_user_cabinet', 'user_id', 'cabinet_id'),
        Index('idx_token_active', 'token', 'is_active'),
        Index('idx_last_used', 'last_used'),
    )

    @classmethod
    def generate_token(cls, cabinet_id: int) -> str:
        """Генерирует фиксированный токен экспорта на основе cabinet_id"""
        # Создаем детерминированный токен на основе cabinet_id
        # Формат: [hash_based_on_cabinet_id].[checksum]
        hash_input = f"wb_assist_export_{cabinet_id}"
        fixed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Берем первые 32 символа как основную часть токена
        fixed_part = fixed_hash[:32]
        
        # Создаем контрольную сумму
        checksum = hashlib.sha256(f"{cabinet_id}{fixed_part}".encode()).hexdigest()[:8]
        
        return f"{fixed_part}.{checksum}"

    def verify_token(self, cabinet_id: int) -> bool:
        """Проверяет целостность токена"""
        if not self.token or '.' not in self.token:
            return False
            
        random_part, checksum = self.token.rsplit('.', 1)
        expected_checksum = hashlib.sha256(f"{cabinet_id}{random_part}".encode()).hexdigest()[:8]
        
        return checksum == expected_checksum

    def is_rate_limited(self) -> bool:
        """Проверяет, не превышен ли лимит запросов"""
        if not self.rate_limit_reset:
            return False
            
        now = datetime.now(timezone.utc)
        if now >= self.rate_limit_reset:
            # Сброс лимита
            self.rate_limit_remaining = 60
            self.rate_limit_reset = None
            return False
            
        return self.rate_limit_remaining <= 0

    def consume_rate_limit(self):
        """Использует один запрос из лимита"""
        if self.rate_limit_remaining > 0:
            self.rate_limit_remaining -= 1
            self.last_used = datetime.now(timezone.utc)
            
            # Устанавливаем время сброса лимита (через час)
            if not self.rate_limit_reset:
                now = datetime.now(timezone.utc)
                next_hour = now.replace(minute=0, second=0, microsecond=0, hour=now.hour + 1)
                if next_hour.hour == 0 and now.hour == 23:
                    # Переход на следующий день
                    from datetime import timedelta
                    next_hour = next_hour + timedelta(days=1)
                self.rate_limit_reset = next_hour

    def __repr__(self):
        return f"<ExportToken {self.token[:8]}... - Cabinet {self.cabinet_id}>"


class ExportLog(Base):
    """Модель логов экспорта данных"""
    __tablename__ = "export_logs"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("export_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    status = Column(String(20), nullable=False, index=True)  # success, error, rate_limit
    data_type = Column(String(20), nullable=False, index=True)  # orders, stocks, reviews
    rows_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    
    # Связи
    token = relationship("ExportToken", back_populates="logs")

    # Индексы и ограничения
    __table_args__ = (
        Index('idx_token_timestamp', 'token_id', 'timestamp'),
        Index('idx_status_data_type', 'status', 'data_type'),
        Index('idx_timestamp_status', 'timestamp', 'status'),
    )

    def __repr__(self):
        return f"<ExportLog {self.status} - {self.data_type} - {self.timestamp}>"
