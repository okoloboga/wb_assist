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
from utils.formatters import format_error_message, safe_edit_message, handle_telegram_errors

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "orders")
async def show_orders_menu(callback: CallbackQuery):
    """Показать меню заказов"""
    logger.info(f"🔍 [show_orders_menu] User {callback.from_user.id} requested orders menu")
    
    response = await bot_api_client.get_recent_orders(
        user_id=callback.from_user.id,
        limit=10,
        offset=0
    )
    
    
    if response.success:
        # Новая структура ответа: данные в корне response
        orders = response.orders or []
        pagination = response.pagination or {}
        
        if orders:
            keyboard = create_orders_keyboard(
                orders=orders,
                offset=pagination.get("offset", 0),
                has_more=pagination.get("has_more", False)
            )
            new_text = response.telegram_text or "🛒 Последние заказы"
            new_markup = keyboard
        else:
            new_text = ("📭 Заказов пока нет\n\n"
                       "Заказы появятся здесь после первой продажи.")
            new_markup = wb_menu_keyboard()
        
        # Проверяем, есть ли текст в текущем сообщении
        current_text = getattr(callback.message, "text", None)
        if current_text:
            # Если есть текст, пытаемся отредактировать
            await safe_edit_message(
                callback=callback,
                text=new_text,
                reply_markup=new_markup,
                user_id=callback.from_user.id
            )
        else:
            # Если нет текста (только фото), удаляем старое и отправляем новое
            await callback.message.delete()
            await callback.message.answer(
                text=new_text,
                reply_markup=new_markup
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        new_text = f"❌ Ошибка загрузки заказов:\n\n{error_message}"
        new_markup = wb_menu_keyboard()
        
        # Проверяем, есть ли текст в текущем сообщении
        current_text = getattr(callback.message, "text", None)
        if current_text:
            # Если есть текст, пытаемся отредактировать
            await safe_edit_message(
                callback=callback,
                text=new_text,
                reply_markup=new_markup,
                user_id=callback.from_user.id
            )
        else:
            # Если нет текста (только фото), удаляем старое и отправляем новое
            await callback.message.delete()
            await callback.message.answer(
                text=new_text,
                reply_markup=new_markup
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
    
    if response.success:
        # Новая структура ответа: данные в корне response
        orders = response.orders or []
        pagination = response.pagination or {}
        
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
    
    if response.success:
        # Новая структура ответа: данные в корне response
        orders = response.orders or []
        pagination = response.pagination or {}
        
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
    
    response = await bot_api_client.get_order_details(order_id=order_id, user_id=callback.from_user.id)
    
    if response.success:
        # Используем новое поле order из response
        order = response.order or {}
        image_url = order.get("image_url")
        
        # Детальные логи для отладки
        logger.info(f"📢 Order detail response: {response}")
        logger.info(f"📢 Order data: {order}")
        logger.info(f"📢 Order image_url: {image_url}")
        logger.info(f"📢 Telegram text: {response.telegram_text}")
        
        # Создаем клавиатуру для детального просмотра
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 К списку заказов",
                callback_data="orders"
            )]
            # [InlineKeyboardButton(
            #     text="🔄 Обновить",
            #     callback_data=f"order_details_{order_id}"
            # )]
        ])
        
        # Если есть изображение, отправляем фото с подписью, иначе обычное сообщение
        if image_url:
            try:
                logger.info(f"📢 Sending photo for order detail: {image_url}")
                await callback.message.delete()
                await callback.message.answer_photo(
                    photo=image_url,
                    caption=response.telegram_text or "🧾 Детали заказа",
                    reply_markup=keyboard
                )
                logger.info(f"📢 Photo sent successfully for order {order_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки фото: {e}")
                await callback.message.edit_text(
                    response.telegram_text or "🧾 Детали заказа",
                    reply_markup=keyboard
                )
        else:
            logger.info(f"📢 No image_url for order {order_id}, sending text only")
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
    logger.info(f"🔍 [cmd_orders] User {message.from_user.id} used /orders command")
    
    response = await bot_api_client.get_recent_orders(
        user_id=message.from_user.id,
        limit=10,
        offset=0
    )
    
    logger.info(f"📡 [cmd_orders] API response: success={response.success}, error={response.error}")
    
    if response.success:
        # Новая структура ответа: данные в корне response
        orders = response.orders or []
        pagination = response.pagination or {}
        
        logger.info(f"📋 [cmd_orders] Received {len(orders)} orders from API")
        for i, order in enumerate(orders[:3]):  # Показываем первые 3 заказа
            logger.info(f"   Order {i+1}: ID={order.get('id')}, WB_ID={order.get('order_id')}, Date={order.get('date')}, Amount={order.get('amount')}")
        
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