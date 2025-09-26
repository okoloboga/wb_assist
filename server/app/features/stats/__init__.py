"""
Статистика и аналитика.

Этот модуль содержит:
- routes: маршруты для получения статистики (/stats, /analytics)
"""

from .routes import stats_router

__all__ = ["stats_router"]