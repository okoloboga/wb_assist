from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from sqlalchemy.sql import func
from ...core.database import Base
from ...core.ai_models import AIModel


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    bot_webhook_url = Column(String(500), nullable=True)  # URL бота для webhook
    webhook_secret = Column(String(100), nullable=True)    # Секрет для подписи
    
    # AI модель пользователя
    preferred_ai_model = Column(
        String(50),
        nullable=False,
        default=AIModel.get_default(),
        server_default="gpt-5.1",
        index=True,
        comment="Предпочитаемая AI модель (gpt-5.1, claude-sonnet-4.5)"
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.telegram_id} - {self.username}>"