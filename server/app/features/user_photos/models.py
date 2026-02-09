"""
Модели для хранения фото пользователей
"""
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean
from sqlalchemy.sql import func
from ...core.database import Base


class UserPhoto(Base):
    """Фото пользователей для виртуальной примерки"""
    __tablename__ = "user_photos"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(BigInteger, index=True, nullable=False)
    file_path = Column(String(500), nullable=False)  # Путь к файлу на диске
    file_url = Column(String(500), nullable=True)    # URL для доступа (если нужен)
    is_active = Column(Boolean, default=True)        # Активно ли фото
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<UserPhoto {self.id} - User {self.user_telegram_id}>"
