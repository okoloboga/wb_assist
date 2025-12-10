"""
RAG Utilities - вспомогательные функции для RAG модуля.
"""

import logging
from typing import Optional
from ..tools.db_pool import get_asyncpg_pool

logger = logging.getLogger(__name__)


async def get_cabinet_id_for_user(telegram_id: int) -> Optional[int]:
    """
    Получение cabinet_id для пользователя по telegram_id.
    
    Логика:
    1. Найти пользователя по telegram_id в таблице users
    2. Найти кабинеты пользователя через cabinet_users
    3. Вернуть первый активный кабинет
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        ID кабинета или None, если не найден
    """
    try:
        pool = await get_asyncpg_pool()
        
        async with pool.acquire() as conn:
            # 1. Получить user_id по telegram_id
            user_row = await conn.fetchrow("""
                SELECT id
                FROM users
                WHERE telegram_id = $1
            """, telegram_id)
            
            if not user_row:
                logger.debug(f"⚠️ User with telegram_id={telegram_id} not found")
                return None
            
            user_id = user_row['id']
            
            # 2. Получить первый активный кабинет пользователя
            cabinet_row = await conn.fetchrow("""
                SELECT cu.cabinet_id
                FROM cabinet_users cu
                JOIN wb_cabinets wc ON cu.cabinet_id = wc.id
                WHERE cu.user_id = $1
                  AND cu.is_active = true
                  AND wc.is_active = true
                ORDER BY cu.joined_at DESC
                LIMIT 1
            """, user_id)
            
            if not cabinet_row:
                logger.debug(
                    f"⚠️ Кабинет не найден для пользователя "
                    f"telegram_id={telegram_id}, user_id={user_id}"
                )
                return None
            
            cabinet_id = cabinet_row['cabinet_id']
            logger.debug(
                f"✅ Найден кабинет {cabinet_id} для пользователя "
                f"telegram_id={telegram_id}"
            )
            
            return cabinet_id
            
    except Exception as e:
        logger.error(f"❌ Error getting cabinet_id for telegram_id={telegram_id}: {e}")
        return None






