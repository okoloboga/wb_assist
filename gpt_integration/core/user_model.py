"""
Helper для получения предпочитаемой AI модели пользователя из БД
"""
import os
import logging
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/wb_assist_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_user_preferred_model(telegram_id: int) -> str:
    """
    Получить предпочитаемую AI модель пользователя из БД
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        str: ID модели (gpt-5.1, claude-sonnet-4.5) или дефолт gpt-5.1
    """
    default_model = "gpt-5.1"
    
    try:
        db = SessionLocal()
        
        query = text("""
            SELECT preferred_ai_model 
            FROM users 
            WHERE telegram_id = :telegram_id
        """)
        
        result = db.execute(query, {"telegram_id": telegram_id}).fetchone()
        db.close()
        
        if result and result[0]:
            model = result[0]
            logger.info(f"✅ User {telegram_id} preferred model: {model}")
            return model
        else:
            logger.info(f"⚠️ User {telegram_id} not found, using default: {default_model}")
            return default_model
            
    except Exception as e:
        logger.error(f"❌ Error getting user model for {telegram_id}: {e}")
        return default_model


async def get_user_preferred_model_async(telegram_id: int) -> str:
    """
    Асинхронная версия получения модели пользователя
    (для совместимости с async кодом)
    """
    return get_user_preferred_model(telegram_id)
