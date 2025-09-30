import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command

from .handlers.registration import router as registration_router
from .handlers.commands import router as commands_router
from .keyboards.keyboards import main_keyboard

# Загрузка переменных окружения из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключаем роутеры
dp.include_router(registration_router)
dp.include_router(commands_router)

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
