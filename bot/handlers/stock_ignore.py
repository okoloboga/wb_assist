"""
Handler for managing the stock alert ignore list.
"""

import logging
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.client import bot_api_client
from core.states import StockIgnoreStates
from utils.formatters import handle_telegram_errors

logger = logging.getLogger(__name__)

router = Router()

# --- Keyboards ---

def stock_ignore_menu_keyboard() -> InlineKeyboardMarkup:
    """Main keyboard for the ignore list menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить артикулы", callback_data="add_to_ignore_list")],
        [InlineKeyboardButton(text="➖ Удалить артикулы", callback_data="remove_from_ignore_list")],
        [InlineKeyboardButton(text="🔙 Назад в Уведомления", callback_data="notifications")]
    ])

def remove_ignore_list_keyboard(nm_ids: list, page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
    """Keyboard for removing items from the ignore list."""
    builder = InlineKeyboardBuilder()
    start, end = page * page_size, page * page_size + page_size
    
    for nm_id in nm_ids[start:end]:
        builder.button(text=f"❌ {nm_id}", callback_data=f"remove_ignore_{nm_id}")
    
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"remove_ignore_page_{page-1}"))
    if end < len(nm_ids):
        pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"remove_ignore_page_{page+1}"))
    
    if pagination_buttons:
        builder.row(*pagination_buttons)
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="stock_ignore_list_menu"))
    builder.adjust(2)
    return builder.as_markup()

# --- Handlers ---

async def _display_ignore_list_menu(message: Message, telegram_id: int, edit: bool = False):
    """Helper function to display the ignore list menu, either by editing or sending a new message."""
    response = await bot_api_client.get_stock_ignore_list(user_id=telegram_id)
    
    # --- DEBUG LOGGING ---
    logger.info(f"--- IGNORE LIST DEBUG ---")
    logger.info(f"Response success: {response.success}")
    logger.info(f"Response data type: {type(response.data)}")
    logger.info(f"Response data content: {response.data}")
    # --- END DEBUG LOGGING ---

    if not response.success:
        text = "❌ Не удалось загрузить список игнорирования."
        keyboard = stock_ignore_menu_keyboard()
    else:
        nm_ids = (response.data.get("data") or {}).get("nm_ids", [])
        
        # --- DEBUG LOGGING ---
        logger.info(f"Extracted nm_ids type: {type(nm_ids)}")
        logger.info(f"Extracted nm_ids content: {nm_ids}")
        logger.info(f"Check 'if not nm_ids': {not nm_ids}")
        # --- END DEBUG LOGGING ---

        if not nm_ids:
            text = (
                "🚫 <b>Список игнорирования остатков</b>\n\n"
                "Ваш список пуст. Вы получаете уведомления по всем товарам.\n\n"
                "Нажмите 'Добавить', чтобы исключить артикулы из уведомлений."
            )
        else:
            id_list_str = ", ".join(map(str, sorted(nm_ids)))
            text = (
                "🚫 <b>Список игнорирования остатков</b>\n\n"
                "Вы не будете получать уведомления о критических остатках для следующих артикулов:\n\n"
                f"<code>{id_list_str}</code>\n\n"
                f"Всего в списке: {len(nm_ids)}."
            )
        keyboard = stock_ignore_menu_keyboard()

    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "stock_ignore_list_menu")
@handle_telegram_errors
async def ignore_list_menu(callback: CallbackQuery, state: FSMContext):
    """Displays the current ignore list and management options by editing the message."""
    await state.clear()
    await _display_ignore_list_menu(callback.message, callback.from_user.id, edit=True)
    await callback.answer()

@router.callback_query(F.data == "add_to_ignore_list")
@handle_telegram_errors
async def add_to_ignore_list_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompts the user to enter nm_ids to add."""
    await state.set_state(StockIgnoreStates.waiting_for_add)
    text = (
        "➕ <b>Добавление в список игнорирования</b>\n\n"
        "Отправьте сообщением один или несколько артикулов (nm_id), которые вы хотите игнорировать. "
        "Разделяйте их пробелами.\n\n"
        "Например:\n"
        "<code>12345678 87654321</code>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="stock_ignore_list_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.message(StateFilter(StockIgnoreStates.waiting_for_add), F.text)
@handle_telegram_errors
async def process_add_to_ignore_list(message: Message, state: FSMContext):
    """Processes the user's message to add nm_ids."""
    await state.clear()
    telegram_id = message.from_user.id
    
    nm_ids_str = re.findall(r'\d+', message.text)
    
    if not nm_ids_str:
        await message.answer("⚠️ Не найдено ни одного артикула. Попробуйте еще раз.")
        await state.set_state(StockIgnoreStates.waiting_for_add)
        return

    try:
        nm_ids = [int(nm_id) for nm_id in nm_ids_str]
    except ValueError:
        await message.answer("⚠️ Артикулы должны быть числами. Попробуйте еще раз.")
        await state.set_state(StockIgnoreStates.waiting_for_add)
        return

    add_response = await bot_api_client.add_to_stock_ignore_list(user_id=telegram_id, nm_ids=nm_ids)

    if not add_response.success:
        await message.answer(f"❌ Не удалось добавить артикулы: {add_response.error}")
    
    # Always show the updated list menu as a new message
    await _display_ignore_list_menu(message, telegram_id, edit=False)


@router.callback_query(F.data == "remove_from_ignore_list")
@router.callback_query(F.data.startswith("remove_ignore_page_"))
@handle_telegram_errors
async def remove_from_ignore_list_menu(callback: CallbackQuery, state: FSMContext):
    """Displays the list of ignored items with remove buttons."""
    telegram_id = callback.from_user.id
    page = 0
    if callback.data.startswith("remove_ignore_page_"):
        try:
            page = int(callback.data.split("_")[-1])
        except (ValueError, IndexError):
            page = 0

    response = await bot_api_client.get_stock_ignore_list(user_id=telegram_id)
    
    nm_ids = (response.data.get("data") or {}).get("nm_ids", [])

    if not response.success or not nm_ids:
        await callback.message.edit_text("🚫 Ваш список игнорирования пуст.", reply_markup=stock_ignore_menu_keyboard())
        await callback.answer()
        return

    keyboard = remove_ignore_list_keyboard(sorted(nm_ids), page)
    
    text = (
        "➖ <b>Удаление из списка игнорирования</b>\n\n"
        "Нажмите на артикул, чтобы удалить его из списка."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("remove_ignore_"))
@handle_telegram_errors
async def process_remove_from_ignore_list(callback: CallbackQuery, state: FSMContext):
    """Processes the removal of a single nm_id."""
    telegram_id = callback.from_user.id
    try:
        nm_id_to_remove = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный формат артикула.", show_alert=True)
        return

    response = await bot_api_client.remove_from_stock_ignore_list(user_id=telegram_id, nm_id=nm_id_to_remove)

    if not response.success:
        await callback.answer(f"❌ Не удалось удалить: {response.error}", show_alert=True)
        return
    
    await callback.answer(f"✅ Артикул {nm_id_to_remove} удален.", show_alert=False)

    # Refresh the removal list
    await remove_from_ignore_list_menu(callback, state)

