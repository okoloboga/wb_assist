"""
Системные функции - здоровье и метрики приложения.

Этот модуль содержит:
- routes: маршруты для проверки здоровья системы (/health, /status)
"""

from .routes import system_router

__all__ = ["system_router"]