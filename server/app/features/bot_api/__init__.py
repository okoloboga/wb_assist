"""
Bot API модуль для интеграции с Telegram ботом
"""

from .routes import router as bot_router
from .formatter import BotMessageFormatter
from .service import BotAPIService
# Webhook удален - используется только polling

__all__ = ["bot_router", "BotMessageFormatter", "BotAPIService"]