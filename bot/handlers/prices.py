import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from keyboards.keyboards import wb_menu_keyboard, main_keyboard, prices_keyboard
from utils.formatters import format_error_message

router = Router()


@router.callback_query(F.data == "my_prices")
async def show_my_prices(callback: CallbackQuery):
    """Показать мои цены"""
    # TODO: Реализовать получение цен через API
    await callback.message.edit_text(
        "💲 МОИ ЦЕНЫ\n\n"
        "⚠️ Функция просмотра цен будет доступна в следующей версии.\n\n"
        "Сейчас доступен просмотр заказов, остатков и отзывов.",
        reply_markup=prices_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "competitor_prices")
async def show_competitor_prices(callback: CallbackQuery):
    """Показать меню конкурентов"""
    # Импортируем handler конкурентов для перенаправления
    from handlers.competitors import show_competitors_menu
    await show_competitors_menu(callback)


@router.callback_query(F.data == "price_history")
async def show_price_history(callback: CallbackQuery):
    """Показать историю цен"""
    # TODO: Реализовать историю цен
    await callback.message.edit_text(
        "📊 ИСТОРИЯ ЦЕН\n\n"
        "⚠️ Функция истории цен будет доступна в следующей версии.\n\n"
        "Сейчас доступен просмотр заказов, остатков и отзывов.",
        reply_markup=prices_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "export_prices")
async def export_prices_to_google(callback: CallbackQuery):
    """Экспорт цен в Google Sheets"""
    # TODO: Реализовать экспорт в Google Sheets
    await callback.message.edit_text(
        "📤 ЭКСПОРТ В GOOGLE SHEETS\n\n"
        "⚠️ Функция экспорта в Google Sheets будет доступна в следующей версии.\n\n"
        "Сейчас доступен просмотр заказов, остатков и отзывов.",
        reply_markup=prices_keyboard()
    )
    await callback.answer()


@router.message(Command("prices"))
async def cmd_prices(message: Message):
    """Команда /prices"""
    await message.answer(
        "💲 УПРАВЛЕНИЕ ЦЕНАМИ\n\n"
        "⚠️ Функции управления ценами будут доступны в следующей версии.\n\n"
        "Сейчас доступен просмотр заказов, остатков и отзывов.",
        reply_markup=main_keyboard()
    )