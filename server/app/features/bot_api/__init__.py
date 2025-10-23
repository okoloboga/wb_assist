"""
Bot API модуль для интеграции с Telegram ботом
"""

from .routes import router as bot_router
from .formatter import BotMessageFormatter
from .service import BotAPIService
# Webhook система для уведомлений

__all__ = ["bot_router", "BotMessageFormatter", "BotAPIService"]