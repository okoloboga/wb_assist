"""
Обработчики раздела избранного
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, URLInputFile, InputMediaPhoto, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.catalog import get_favorites_product_keyboard, get_go_to_catalog_keyboard
# Fitter keyboards removed
# from keyboards.fitter_keyboards import get_fitter_main_menu
from api.client import bot_api_client as api_client

router = Router()


@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery):
    """Показать избранное (заглушка)"""
    await callback.message.edit_text(
        "⭐️ <b>Избранное</b>\n\n"
        "Раздел избранного пока не реализован в интегрированной версии.\n"
        "Эта функция будет добавлена позже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ai_fitter")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fav:add:"))
async def add_favorite(callback: CallbackQuery):
    """Добавить товар в избранное (заглушка)"""
    await callback.answer("Добавление в избранное пока не реализовано")


@router.callback_query(F.data.startswith("fav:remove:"))
async def remove_favorite(callback: CallbackQuery):
    """Удалить товар из избранного (заглушка)"""
    await callback.answer("Удаление из избранного пока не реализовано")


@router.callback_query(F.data.startswith("nav_fav:"))
async def navigate_favorites(callback: CallbackQuery):
    """Навигация по избранному (заглушка)"""
    await callback.answer("Навигация по избранному пока не реализована")


@router.callback_query(F.data.startswith("photos_fav:"))
async def show_favorite_photos(callback: CallbackQuery):
    """Показать все фото товара из избранного (заглушка)"""
    await callback.answer("Просмотр фото избранного пока не реализован")


@router.callback_query(F.data.startswith("back_fav:"))
async def back_to_favorite_product(callback: CallbackQuery):
    """Вернуться к товару в избранном (заглушка)"""
    await callback.answer("Возврат к избранному товару пока не реализован")