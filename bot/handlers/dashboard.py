import sys
import logging
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from api.client import bot_api_client
from keyboards.keyboards import wb_menu_keyboard, main_keyboard
from utils.formatters import format_error_message, safe_edit_message

logger = logging.getLogger(__name__)

router = Router()


# Обработчик dashboard убран, так как кнопка удалена из меню
# Данные дашборда теперь показываются в главном меню


@router.callback_query(F.data == "refresh_dashboard")
async def refresh_dashboard(callback: CallbackQuery):
    """Обновить данные дашборда"""
    await safe_edit_message(
        callback=callback,
        text="⏳ Обновляю данные...",
        reply_markup=None,
        user_id=callback.from_user.id
    )
    
    response = await bot_api_client.get_dashboard(
        user_id=callback.from_user.id
    )
    
    if response.success:
        await safe_edit_message(
            callback=callback,
            text=response.telegram_text or "📊 Дашборд обновлен",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка обновления дашборда:\n\n{error_message}",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer("✅ Данные обновлены")


@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message):
    """Команда /dashboard"""
    response = await bot_api_client.get_dashboard(
        user_id=message.from_user.id
    )
    
    if response.success:
        await message.answer(
            response.telegram_text or "📊 Дашборд загружен",
            reply_markup=wb_menu_keyboard()
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка загрузки дашборда:\n\n{error_message}",
            reply_markup=main_keyboard()
        )