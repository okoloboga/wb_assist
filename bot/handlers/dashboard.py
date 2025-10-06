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
from utils.formatters import format_error_message

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "dashboard")
async def show_dashboard(callback: CallbackQuery):
    """Показать дашборд с общей информацией по кабинету"""
    logger.info(f"🔍 DEBUG: Обработчик dashboard вызван для пользователя {callback.from_user.id}")
    
    logger.info(f"🔍 DEBUG: Вызываем bot_api_client.get_dashboard с user_id={callback.from_user.id}")
    response = await bot_api_client.get_dashboard(
        user_id=callback.from_user.id
    )
    
    logger.info(f"🔍 DEBUG: Получен ответ от API: success={response.success}, status_code={response.status_code}")
    if response.error:
        logger.info(f"🔍 DEBUG: Ошибка API: {response.error}")
    
    if response.success:
        new_text = response.telegram_text or "📊 Дашборд загружен"
        new_markup = wb_menu_keyboard()
        
        # Проверяем, изменилось ли содержимое
        if (callback.message.text != new_text or 
            callback.message.reply_markup != new_markup):
            await callback.message.edit_text(
                new_text,
                reply_markup=new_markup
            )
        else:
            logger.info("🔍 DEBUG: Содержимое не изменилось, пропускаем редактирование")
    else:
        error_message = format_error_message(response.error, response.status_code)
        new_text = f"❌ Ошибка загрузки дашборда:\n\n{error_message}"
        new_markup = main_keyboard()
        
        # Проверяем, изменилось ли содержимое
        if (callback.message.text != new_text or 
            callback.message.reply_markup != new_markup):
            await callback.message.edit_text(
                new_text,
                reply_markup=new_markup
            )
        else:
            logger.info("🔍 DEBUG: Содержимое не изменилось, пропускаем редактирование")
    
    await callback.answer()


@router.callback_query(F.data == "refresh_dashboard")
async def refresh_dashboard(callback: CallbackQuery):
    """Обновить данные дашборда"""
    await callback.message.edit_text("⏳ Обновляю данные...")
    
    response = await bot_api_client.get_dashboard(
        user_id=callback.from_user.id
    )
    
    if response.success:
        await callback.message.edit_text(
            response.telegram_text or "📊 Дашборд обновлен",
            reply_markup=wb_menu_keyboard()
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка обновления дашборда:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
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