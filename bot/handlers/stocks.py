import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from api.client import bot_api_client
from keyboards.keyboards import wb_menu_keyboard, main_keyboard, create_stocks_keyboard, create_stocks_menu_keyboard
from utils.formatters import format_error_message, format_stocks_summary, safe_edit_message

router = Router()


@router.callback_query(F.data == "stock")
async def show_stock_menu(callback: CallbackQuery):
    """Показать меню склада (заглушка)"""
    await safe_edit_message(
        callback=callback,
        text="Заглушка для складов",
        reply_markup=create_stocks_menu_keyboard(),
        user_id=callback.from_user.id
    )
    await callback.answer()


@router.callback_query(F.data == "dynamic_critical_stocks")
async def show_dynamic_critical_stocks(callback: CallbackQuery):
    """Показать критичные остатки на основе динамики"""
    response = await bot_api_client.get_dynamic_critical_stocks(
        user_id=callback.from_user.id,
        limit=20,
        offset=0
    )
    
    if response.success:
        # Получаем данные пагинации из ответа
        stocks_data = response.stocks or {}
        pagination = stocks_data.get("pagination", {})
        has_more = pagination.get("has_more", False)
        offset = pagination.get("offset", 0)
        
        await safe_edit_message(
            callback=callback,
            text=response.telegram_text or "⚠️ Критичные остатки",
            reply_markup=create_stocks_keyboard(has_more=has_more, offset=offset),
            user_id=callback.from_user.id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки остатков:\n\n{error_message}",
            reply_markup=create_stocks_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data == "stock_list")
async def show_critical_stocks(callback: CallbackQuery):
    """Показать критичные остатки"""
    response = await bot_api_client.get_critical_stocks(
        user_id=callback.from_user.id,
        limit=20,
        offset=0
    )
    
    if response.success:
        # Используем новое поле stocks из response
        stocks_data = response.stocks or {}
        critical_products = stocks_data.get("critical_products", [])
        zero_products = stocks_data.get("zero_products", [])
        summary = stocks_data.get("summary", {})
        
        if critical_products or zero_products:
            keyboard = create_stocks_keyboard(
                has_more=len(critical_products) + len(zero_products) >= 20,
                offset=0
            )
            
            await safe_edit_message(
                callback=callback,
                text=response.telegram_text or "📦 Критичные остатки",
                reply_markup=keyboard,
                user_id=callback.from_user.id
            )
        else:
            await safe_edit_message(
                callback=callback,
                text="✅ Все остатки в норме!\n\n"
                     "Критичных остатков не обнаружено.",
                reply_markup=wb_menu_keyboard(),
                user_id=callback.from_user.id
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки остатков:\n\n{error_message}",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("stocks_page_"))
async def show_stocks_page(callback: CallbackQuery):
    """Показать страницу остатков"""
    try:
        offset = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        offset = 0
    
    response = await bot_api_client.get_critical_stocks(
        user_id=callback.from_user.id,
        limit=20,
        offset=offset
    )
    
    if response.success and response.data:
        stocks_data = response.data.get("stocks", {})
        critical_products = stocks_data.get("critical_products", [])
        zero_products = stocks_data.get("zero_products", [])
        
        keyboard = create_stocks_keyboard(
            has_more=len(critical_products) + len(zero_products) >= 20,
            offset=offset
        )
        
        await safe_edit_message(
            callback=callback,
            text=response.telegram_text or "📦 Остатки",
            reply_markup=keyboard,
            user_id=callback.from_user.id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки остатков:\n\n{error_message}",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("dynamic_stocks_page_"))
async def show_dynamic_stocks_page(callback: CallbackQuery):
    """Показать страницу динамических критичных остатков"""
    try:
        offset = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        offset = 0
    
    response = await bot_api_client.get_dynamic_critical_stocks(
        user_id=callback.from_user.id,
        limit=20,
        offset=offset
    )
    
    if response.success:
        # Получаем данные пагинации из ответа
        stocks_data = response.stocks or {}
        pagination = stocks_data.get("pagination", {})
        has_more = pagination.get("has_more", False)
        
        await safe_edit_message(
            callback=callback,
            text=response.telegram_text or "⚠️ Критичные остатки",
            reply_markup=create_stocks_keyboard(has_more=has_more, offset=offset),
            user_id=callback.from_user.id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки остатков:\n\n{error_message}",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data == "stock_notify")
async def show_stock_notifications(callback: CallbackQuery):
    """Показать настройки уведомлений об остатках"""
    # TODO: Реализовать настройки уведомлений
    await safe_edit_message(
        callback=callback,
        text="🔔 УВЕДОМЛЕНИЯ ОБ ОСТАТКАХ\n\n"
             "⚠️ Функция настройки уведомлений будет доступна в следующей версии.\n\n"
             "Сейчас доступен просмотр критичных остатков.",
        reply_markup=create_stocks_keyboard(),
        user_id=callback.from_user.id
    )
    await callback.answer()


@router.callback_query(F.data == "export_stock")
async def export_stocks_to_google(callback: CallbackQuery):
    """Экспорт остатков в Google Sheets"""
    # TODO: Реализовать экспорт в Google Sheets
    await safe_edit_message(
        callback=callback,
        text="📤 ЭКСПОРТ В GOOGLE SHEETS\n\n"
             "⚠️ Функция экспорта в Google Sheets будет доступна в следующей версии.\n\n"
             "Сейчас доступен просмотр критичных остатков.",
        reply_markup=create_stocks_keyboard(),
        user_id=callback.from_user.id
    )
    await callback.answer()


@router.message(Command("stocks"))
async def cmd_stocks(message: Message):
    """Команда /stocks"""
    response = await bot_api_client.get_critical_stocks(
        user_id=message.from_user.id,
        limit=20,
        offset=0
    )
    
    if response.success and response.data:
        stocks_data = response.data.get("stocks", {})
        critical_products = stocks_data.get("critical_products", [])
        zero_products = stocks_data.get("zero_products", [])
        
        if critical_products or zero_products:
            keyboard = create_stocks_keyboard(
                has_more=len(critical_products) + len(zero_products) >= 20,
                offset=0
            )
            
            await message.answer(
                response.telegram_text or "📦 Критичные остатки",
                reply_markup=keyboard
            )
        else:
            await message.answer(
                "✅ Все остатки в норме!\n\n"
                "Критичных остатков не обнаружено.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка загрузки остатков:\n\n{error_message}",
            reply_markup=main_keyboard()
        )