"""
Модели для хранения параметров (размеров) пользователей
"""
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Float
from sqlalchemy.sql import func
from ...core.database import Base


class UserMeasurements(Base):
    """Параметры пользователей для подбора размера"""
    __tablename__ = "user_measurements"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    # Основные параметры
    russian_size = Column(String(20), nullable=True)  # Российский размер (например: "42-44")

    # Параметры верхней одежды
    shoulder_length = Column(Float, nullable=True)    # Длина плеч (см)
    back_width = Column(Float, nullable=True)         # Ширина спины (см)
    sleeve_length = Column(Float, nullable=True)      # Длина рукава (см)
    back_length = Column(Float, nullable=True)        # Длина по спинке (см)

    # Обхваты
    chest = Column(Float, nullable=True)              # Обхват груди (см)
    waist = Column(Float, nullable=True)              # Обхват талии (см)
    hips = Column(Float, nullable=True)               # Обхват бедер (см)

    # Параметры брюк
    pants_length = Column(Float, nullable=True)       # Длина брюк (см)
    waist_girth = Column(Float, nullable=True)        # Обхват в поясе (см)
    rise_height = Column(Float, nullable=True)        # Высота посадки (см)
    back_rise_height = Column(Float, nullable=True)   # Высота посадки сзади (см)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<UserMeasurements User {self.user_telegram_id}>"
