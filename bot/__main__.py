import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command

from core.config import config
from middleware.error_handler import ErrorHandlerMiddleware, LoggingMiddleware, RateLimitMiddleware
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
from keyboards.keyboards import main_keyboard

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.bot_token)
dp = Dispatcher()

# Подключаем middleware
dp.message.middleware(ErrorHandlerMiddleware())
dp.callback_query.middleware(ErrorHandlerMiddleware())
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())
dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())

# Подключаем роутеры
dp.include_router(registration_router)
dp.include_router(commands_router)
dp.include_router(wb_cabinet_router)
dp.include_router(dashboard_router)
dp.include_router(orders_router)
dp.include_router(stocks_router)
dp.include_router(reviews_router)
dp.include_router(analytics_router)
dp.include_router(sync_router)
dp.include_router(notifications_router)

# Этот обработчик остаётся здесь, т.к. registration_router
# обрабатывает /start только при ПЕРВОЙ регистрации.
# Нужен резервный обработчик для уже зарегистрированных пользователей.
@dp.message(Command(commands=["start"]))
async def cmd_start(message):
    first_name = message.from_user.first_name
    await message.answer(
        f"Здравствуйте, {first_name}! 👋\n\nЯ помогу работать с кабинетом WB.\nВыбери действие:",
        reply_markup=main_keyboard()
    )

async def main():
    logger.info("Bot started...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
