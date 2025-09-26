"""
Ядро приложения - настройки и инфраструктура.

Этот модуль содержит основные компоненты приложения:
- config: настройки приложения и переменные окружения
- database: подключение к базе данных
- middleware: промежуточное ПО (CORS, логирование)
"""

from .config import settings
from .database import get_db, init_db
from .middleware import setup_middleware, setup_exception_handlers

__all__ = [
    "settings",
    "get_db", 
    "init_db",
    "setup_middleware",
    "setup_exception_handlers"
]