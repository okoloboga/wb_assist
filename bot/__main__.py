import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
import uvicorn

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent))

from core.config import config
from middleware.error_handler import ErrorHandlerMiddleware, LoggingMiddleware, RateLimitMiddleware
from middleware.api_key_check import APIKeyCheckMiddleware
from handlers.registration import router as registration_router
from handlers.commands import router as commands_router
from handlers.wb_cabinet import router as wb_cabinet_router
from handlers.dashboard import router as dashboard_router
from handlers.orders import router as orders_router
from handlers.stocks import router as stocks_router
from handlers.reviews import router as reviews_router
from handlers.analytics import router as analytics_router
from handlers.sync import router as sync_router
from handlers.notifications import router as notifications_router
from handlers.prices import router as prices_router
from handlers.webhook import router as webhook_router, webhook_app
# from handlers.gpt import router as gpt_router  # Временно отключено
from keyboards.keyboards import main_keyboard, wb_menu_keyboard

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.bot_token)
dp = Dispatcher()

# Создаем экземпляр middleware для глобального доступа
api_key_middleware = APIKeyCheckMiddleware()

# Подключаем middleware
dp.message.middleware(api_key_middleware)
dp.callback_query.middleware(api_key_middleware)
dp.message.middleware(ErrorHandlerMiddleware())
dp.callback_query.middleware(ErrorHandlerMiddleware())
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())
dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())

# Подключаем роутеры
dp.include_router(commands_router)  # commands_router должен быть ПЕРВЫМ
dp.include_router(registration_router)
dp.include_router(wb_cabinet_router)
dp.include_router(dashboard_router)
dp.include_router(orders_router)
dp.include_router(stocks_router)
dp.include_router(reviews_router)
dp.include_router(analytics_router)
dp.include_router(sync_router)
dp.include_router(notifications_router)
dp.include_router(prices_router)
dp.include_router(webhook_router)
# dp.include_router(gpt_router)  # Временно отключено

async def start_webhook_server():
    """Запуск webhook сервера"""
    config_uvicorn = uvicorn.Config(
        webhook_app, 
        host="0.0.0.0", 
        port=8001, 
        log_level="info"
    )
    server = uvicorn.Server(config_uvicorn)
    await server.serve()

async def main():
    logger.info("Bot started...")
    try:
        # Запускаем webhook сервер в фоне
        webhook_task = asyncio.create_task(start_webhook_server())
        logger.info("Webhook server started on port 8001")
        
        # Запускаем основной бот с webhook системой
        await dp.start_polling(bot)
    finally:
        webhook_task.cancel()
        try:
            await webhook_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())