from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ...core.database import Base


class CabinetUser(Base):
    """Простая связь пользователей с кабинетами"""
    __tablename__ = "cabinet_users"
    
    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # Без ForeignKey для простоты
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    cabinet = relationship("WBCabinet", back_populates="cabinet_users")
    
    # Уникальность: один пользователь не может быть в одном кабинете дважды
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'user_id', name='unique_cabinet_user'),
    )
    
    def __repr__(self):
        return f"<CabinetUser cabinet_id={self.cabinet_id} user_id={self.user_id}>"
