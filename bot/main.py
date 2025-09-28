import asyncio
import logging
import os
from dotenv import load_dotenv
from registration import router as registration_router
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.filters import Command

from keyboards import (
    main_keyboard, wb_menu_keyboard, analytics_keyboard, stock_keyboard,
    reviews_keyboard, prices_keyboard, content_keyboard,
    ai_assistant_keyboard, settings_keyboard
)

# Загрузка .env из другой папки
load_dotenv(dotenv_path=r"C:\configs\botkey.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Проверьте botkey.env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Навигация кнопки "назад"
navigation = {
    "analytics": "wb_menu",
    "stock": "wb_menu",
    "reviews": "wb_menu",
    "prices": "wb_menu",
    "content": "wb_menu",
    "ai_assistant": "wb_menu",
    "settings": "wb_menu",
    "wb_menu": "main"
}

keyboards_map = {
    "main": main_keyboard,
    "wb_menu": wb_menu_keyboard,
    "analytics": analytics_keyboard,
    "stock": stock_keyboard,
    "reviews": reviews_keyboard,
    "prices": prices_keyboard,
    "content": content_keyboard,
    "ai_assistant": ai_assistant_keyboard,
    "settings": settings_keyboard
}

section_titles = {
    "main": "Я помогу работать с кабинетом WB.\nВыбери действие:",
    "wb_menu": "Раздел: WB Menu",
    "analytics": "Раздел: Аналитика",
    "stock": "Раздел: Склад",
    "reviews": "Раздел: Отзывы",
    "prices": "Раздел: Цены и конкуренты",
    "content": "Раздел: Контент",
    "ai_assistant": "Раздел: AI-помощник",
    "settings": "Раздел: Настройки"
}

dp.include_router(registration_router)

@dp.message(Command(commands=["start"]))
async def cmd_start(message):
    first_name = message.from_user.first_name  # берём имя пользователя
    await message.answer(
        f"Здравствуйте, {first_name}! 👋\n\n{section_titles['main']}",
        reply_markup=main_keyboard()
    )


@dp.callback_query(F.data == "connect_wb")
async def connect_wb_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        section_titles["wb_menu"],
        reply_markup=wb_menu_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    text = (
        "Команды:\n"
        "/sales — продажи\n"
        "/stock — остатки\n"
        "/reviews — отзывы\n"
        "/digest — аналитический дайджест\n\n"
        "Навигация через кнопки в чате."
    )
    await callback.message.edit_text(text, reply_markup=main_keyboard())
    await callback.answer()


@dp.callback_query(F.data)
async def menu_callback(callback: CallbackQuery):
    data = callback.data

    if data in keyboards_map:
        await callback.message.edit_text(
            section_titles.get(data, ""),
            reply_markup=keyboards_map[data]()
        )
        await callback.answer()

    elif data.startswith("back_"):
        target_menu = navigation.get(data.replace("back_", ""), "main")
        await callback.message.edit_text(
            section_titles.get(target_menu, ""),
            reply_markup=keyboards_map[target_menu]()
        )
        await callback.answer()


async def main():
    logger.info("Bot started...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
