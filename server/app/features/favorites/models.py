"""
Модели для хранения избранных товаров
"""
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, UniqueConstraint
from sqlalchemy.sql import func
from ...core.database import Base


class Favorite(Base):
    """Избранные товары пользователей"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(BigInteger, index=True, nullable=False)
    product_id = Column(String(100), nullable=False)  # ID товара из каталога
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Уникальность: один пользователь не может добавить один товар дважды
    __table_args__ = (
        UniqueConstraint('user_telegram_id', 'product_id', name='uix_user_product'),
    )

    def __repr__(self):
        return f"<Favorite User {self.user_telegram_id} - Product {self.product_id}>"
