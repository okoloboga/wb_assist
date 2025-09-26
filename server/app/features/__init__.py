"""
Функциональные возможности приложения - бизнес-логика.

Этот модуль содержит все функциональные модули:
- system: системные функции (здоровье, метрики)
- user: управление пользователями
- stats: статистика и аналитика
"""

from .system.routes import system_router
from .user.routes import user_router
from .stats.routes import stats_router

__all__ = [
    "system_router",
    "user_router", 
    "stats_router"
]