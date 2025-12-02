import os
from typing import Optional

try:
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover
    asyncpg = None  # type: ignore

POOL: Optional["asyncpg.pool.Pool"] = None  # type: ignore

async def init_pool() -> None:
    global POOL
    if POOL is not None:
        return
    db_url = os.getenv("AI_CHAT_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url or not db_url.startswith("postgres"):
        # Pool only for Postgres; other DBs are not supported here
        return
    if asyncpg is None:
        raise RuntimeError("asyncpg is not installed but required for Postgres execution")
    POOL = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=5, timeout=10)

async def close_pool() -> None:
    global POOL
    if POOL is not None:
        await POOL.close()
        POOL = None


async def get_asyncpg_pool():
    """
    Получить пул подключений asyncpg.
    
    Инициализирует пул, если он еще не создан.
    
    Returns:
        asyncpg.Pool: Пул подключений к PostgreSQL
    """
    if POOL is None:
        await init_pool()
    
    if POOL is None:
        raise RuntimeError("Не удалось инициализировать пул подключений к БД")
    
    return POOL



