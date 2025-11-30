"""
SQLAlchemy models for Photo Processing Service.

Модели:
    - PhotoProcessingResult: Хранение результатов обработки фотографий (Вариант 1: ссылки)
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, DateTime, Index
from sqlalchemy.sql import func
from .database import Base


class PhotoProcessingResult(Base):
    """
    Результаты обработки фотографий (Вариант 1: Хранение ссылок).
    
    Хранит URL обработанного изображения в БД.
    """
    __tablename__ = "photo_processing_results"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # Связь с основной таблицей пользователей (опционально)
    original_photo_file_id = Column(String(255), nullable=False)  # Telegram file_id исходного фото
    prompt = Column(Text, nullable=False)  # Текст промпта
    result_photo_url = Column(Text, nullable=False)  # URL обработанного изображения
    processing_service = Column(String(100), nullable=True)  # Название сервиса генерации (например, "midjourney", "stable_diffusion")
    processing_time = Column(Float, nullable=True)  # Время обработки в секундах
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Индексы для производительности
    __table_args__ = (
        Index('idx_photo_processing_telegram_id', 'telegram_id'),
        Index('idx_photo_processing_created_at', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<PhotoProcessingResult(id={self.id}, telegram_id={self.telegram_id}, created_at={self.created_at})>"













