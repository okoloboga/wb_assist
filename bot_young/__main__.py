"""
Точка входа для bot_young
"""
import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent))

from core.config import config
from handlers.start import router as start_router
from handlers.channels import router as channels_router
from handlers.add_channel import router as add_channel_router

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем бота и диспетчер
bot = Bot(token=config.bot_token)
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(start_router)
dp.include_router(add_channel_router)  # FSM должен быть раньше
dp.include_router(channels_router)


async def main():
    logger.info("Bot Young started...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

