import sys
import logging
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from api.client import bot_api_client
from keyboards.keyboards import wb_menu_keyboard, main_keyboard, create_orders_keyboard
from utils.formatters import format_error_message

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "orders")
async def show_orders_menu(callback: CallbackQuery):
    """Показать меню заказов"""
    logger.info(f"🔍 DEBUG: Обработчик orders вызван для пользователя {callback.from_user.id}")
    
    logger.info(f"🔍 DEBUG: Вызываем bot_api_client.get_recent_orders с user_id={callback.from_user.id}")
    response = await bot_api_client.get_recent_orders(
        user_id=callback.from_user.id,
        limit=10,
        offset=0
    )
    
    logger.info(f"🔍 DEBUG: Получен ответ от API: success={response.success}, status_code={response.status_code}")
    if response.error:
        logger.info(f"🔍 DEBUG: Ошибка API: {response.error}")
    
    if response.success and response.data:
        orders = response.data.get("orders", [])
        pagination = response.data.get("pagination", {})
        
        if orders:
            keyboard = create_orders_keyboard(
                orders=orders,
                offset=pagination.get("offset", 0),
                has_more=pagination.get("has_more", False)
            )
            
            await callback.message.edit_text(
                response.telegram_text or "🛒 Последние заказы",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "📭 Заказов пока нет\n\n"
                "Заказы появятся здесь после первой продажи.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки заказов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "recent_orders")
async def show_recent_orders(callback: CallbackQuery):
    """Показать последние заказы"""
    response = await bot_api_client.get_recent_orders(
        user_id=callback.from_user.id,
        limit=10,
        offset=0
    )
    
    if response.success and response.data:
        orders = response.data.get("orders", [])
        pagination = response.data.get("pagination", {})
        
        if orders:
            keyboard = create_orders_keyboard(
                orders=orders,
                offset=pagination.get("offset", 0),
                has_more=pagination.get("has_more", False)
            )
            
            await callback.message.edit_text(
                response.telegram_text or "🛒 Последние заказы",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "📭 Заказов пока нет\n\n"
                "Заказы появятся здесь после первой продажи.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки заказов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("orders_page_"))
async def show_orders_page(callback: CallbackQuery):
    """Показать страницу заказов"""
    try:
        offset = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        offset = 0
    
    response = await bot_api_client.get_recent_orders(
        user_id=callback.from_user.id,
        limit=10,
        offset=offset
    )
    
    if response.success and response.data:
        orders = response.data.get("orders", [])
        pagination = response.data.get("pagination", {})
        
        keyboard = create_orders_keyboard(
            orders=orders,
            offset=offset,
            has_more=pagination.get("has_more", False)
        )
        
        await callback.message.edit_text(
            response.telegram_text or "🛒 Заказы",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки заказов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("order_details_"))
async def show_order_details(callback: CallbackQuery):
    """Показать детальную информацию о заказе"""
    try:
        order_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Неверный ID заказа")
        return
    
    response = await bot_api_client.get_order_details(order_id=order_id)
    
    if response.success and response.data:
        order = response.data.get("order", {})
        
        # Создаем клавиатуру для детального просмотра
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 К списку заказов",
                callback_data="sales_period"
            )],
            [InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"order_details_{order_id}"
            )]
        ])
        
        await callback.message.edit_text(
            response.telegram_text or "🧾 Детали заказа",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки заказа:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    """Команда /orders"""
    response = await bot_api_client.get_recent_orders(
        user_id=message.from_user.id,
        limit=10,
        offset=0
    )
    
    if response.success and response.data:
        orders = response.data.get("orders", [])
        pagination = response.data.get("pagination", {})
        
        if orders:
            keyboard = create_orders_keyboard(
                orders=orders,
                offset=0,
                has_more=pagination.get("has_more", False)
            )
            
            await message.answer(
                response.telegram_text or "🛒 Последние заказы",
                reply_markup=keyboard
            )
        else:
            await message.answer(
                "📭 Заказов пока нет\n\n"
                "Заказы появятся здесь после первой продажи.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка загрузки заказов:\n\n{error_message}",
            reply_markup=main_keyboard()
        )