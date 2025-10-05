import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from core.states import NotificationStates
from core.config import config
from keyboards.keyboards import wb_menu_keyboard, main_keyboard, create_notification_keyboard
from utils.formatters import format_error_message, format_stocks_summary

router = Router()


@router.callback_query(F.data == "notifications")
async def show_notifications_menu(callback: CallbackQuery):
    """Показать меню уведомлений"""
    await callback.message.edit_text(
        "🔔 УВЕДОМЛЕНИЯ\n\n"
        "📊 Статус уведомлений:\n"
        "✅ Заказы: Включены\n"
        "✅ Остатки: Включены\n"
        "✅ Отзывы: Включены\n"
        "✅ Синхронизация: Включены\n\n"
        "🔧 Настройте уведомления в разделе 'Настройки' → 'Уведомления'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="⚙️ Настройки уведомлений",
                callback_data="settings_notifications"
            )],
            [InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="wb_menu"
            )]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "settings_notifications")
async def show_notification_settings(callback: CallbackQuery, state: FSMContext):
    """Показать настройки уведомлений"""
    await state.set_state(NotificationStates.settings_menu)
    
    await callback.message.edit_text(
        "🔔 НАСТРОЙКИ УВЕДОМЛЕНИЙ\n\n"
        "Выберите типы уведомлений, которые хотите получать:\n\n"
        "✅ Включено\n"
        "❌ Выключено\n\n"
        "Нажмите на тип уведомления для переключения:",
        reply_markup=create_notification_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_orders_notifications")
async def toggle_orders_notifications(callback: CallbackQuery):
    """Переключить уведомления о заказах"""
    # TODO: Реализовать переключение через API
    await callback.answer(
        "⚠️ Функция переключения уведомлений будет доступна в следующей версии",
        show_alert=True
    )


@router.callback_query(F.data == "toggle_stocks_notifications")
async def toggle_stocks_notifications(callback: CallbackQuery):
    """Переключить уведомления об остатках"""
    # TODO: Реализовать переключение через API
    await callback.answer(
        "⚠️ Функция переключения уведомлений будет доступна в следующей версии",
        show_alert=True
    )


@router.callback_query(F.data == "toggle_reviews_notifications")
async def toggle_reviews_notifications(callback: CallbackQuery):
    """Переключить уведомления об отзывах"""
    # TODO: Реализовать переключение через API
    await callback.answer(
        "⚠️ Функция переключения уведомлений будет доступна в следующей версии",
        show_alert=True
    )


@router.callback_query(F.data == "toggle_sync_notifications")
async def toggle_sync_notifications(callback: CallbackQuery):
    """Переключить уведомления о синхронизации"""
    # TODO: Реализовать переключение через API
    await callback.answer(
        "⚠️ Функция переключения уведомлений будет доступна в следующей версии",
        show_alert=True
    )


@router.callback_query(F.data == "test_notification")
async def test_notification(callback: CallbackQuery):
    """Отправить тестовое уведомление"""
    await callback.message.edit_text(
        "🧪 ТЕСТОВОЕ УВЕДОМЛЕНИЕ\n\n"
        "✅ Уведомления работают корректно!\n\n"
        "Это тестовое уведомление показывает, что система уведомлений функционирует.",
        reply_markup=create_notification_keyboard()
    )
    await callback.answer("✅ Тестовое уведомление отправлено")


@router.message(Command("notifications"))
async def cmd_notifications(message: Message, state: FSMContext):
    """Команда /notifications"""
    await state.set_state(NotificationStates.settings_menu)
    
    await message.answer(
        "🔔 НАСТРОЙКИ УВЕДОМЛЕНИЙ\n\n"
        "Выберите типы уведомлений, которые хотите получать:\n\n"
        "✅ Включено\n"
        "❌ Выключено\n\n"
        "Нажмите на тип уведомления для переключения:",
        reply_markup=create_notification_keyboard()
    )


# Webhook обработчики для получения уведомлений от сервера
@router.message()
async def handle_webhook_notification(message: Message):
    """Обработать уведомление от webhook"""
    # Проверяем, является ли сообщение уведомлением от сервера
    if hasattr(message, 'web_app_data') and message.web_app_data:
        try:
            import json
            data = json.loads(message.web_app_data.data)
            
            if data.get("type") == "new_order":
                await handle_new_order_notification(message, data)
            elif data.get("type") == "critical_stocks":
                await handle_critical_stocks_notification(message, data)
            elif data.get("type") == "new_review":
                await handle_new_review_notification(message, data)
            elif data.get("type") == "sync_completed":
                await handle_sync_completed_notification(message, data)
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Ошибка обработки webhook уведомления: {e}")


async def handle_new_order_notification(message: Message, data: dict):
    """Обработать уведомление о новом заказе"""
    order_data = data.get("data", {})
    
    text = f"🎉 НОВЫЙ ЗАКАЗ!\n\n"
    text += f"🧾 #{order_data.get('order_id', 'N/A')} | {order_data.get('amount', 0):,}₽\n"
    text += f"👑 {order_data.get('brand', 'N/A')}\n"
    text += f"✏ {order_data.get('product_name', 'N/A')}\n"
    text += f"🚛 {order_data.get('warehouse_from', 'N/A')} → {order_data.get('warehouse_to', 'N/A')}\n\n"
    
    today_stats = order_data.get("today_stats", {})
    if today_stats:
        text += f"📊 Сегодня: {today_stats.get('count', 0)} заказов на {today_stats.get('amount', 0):,}₽\n"
    
    stocks = order_data.get("stocks", {})
    if stocks:
        text += f"📦 Остаток: {format_stocks_summary(stocks)}\n"
    
    text += f"\n💡 Нажмите /order_{order_data.get('order_id', 'N/A')} для полного отчета"
    
    await message.answer(text)


async def handle_critical_stocks_notification(message: Message, data: dict):
    """Обработать уведомление о критичных остатках"""
    products = data.get("data", {}).get("products", [])
    
    text = "⚠️ КРИТИЧНЫЕ ОСТАТКИ!\n\n"
    
    for product in products[:3]:  # Показываем максимум 3 товара
        text += f"📦 {product.get('name', 'N/A')} ({product.get('brand', 'N/A')})\n"
        text += f"🆔 {product.get('nm_id', 'N/A')}\n"
        text += f"📊 Остатки: {format_stocks_summary(product.get('stocks', {}))}\n"
        
        critical_sizes = product.get("critical_sizes", [])
        zero_sizes = product.get("zero_sizes", [])
        
        if critical_sizes:
            text += f"⚠️ Критично: {', '.join(critical_sizes)}\n"
        if zero_sizes:
            text += f"🔴 Нулевые: {', '.join(zero_sizes)}\n"
        
        text += "\n"
    
    if len(products) > 3:
        text += f"... и еще {len(products) - 3} товаров\n\n"
    
    text += "💡 Нажмите /stocks для подробного отчета"
    
    await message.answer(text)


async def handle_new_review_notification(message: Message, data: dict):
    """Обработать уведомление о новом отзыве"""
    review_data = data.get("data", {})
    
    text = "⭐ НОВЫЙ ОТЗЫВ!\n\n"
    text += f"📦 {review_data.get('product_name', 'N/A')}\n"
    text += f"⭐ Рейтинг: {review_data.get('rating', 0)}/5\n"
    text += f"💬 \"{review_data.get('text', 'N/A')[:100]}{'...' if len(review_data.get('text', '')) > 100 else ''}\"\n"
    text += f"⏰ {review_data.get('time_ago', 'N/A')}\n\n"
    text += "💡 Нажмите /reviews для просмотра всех отзывов"
    
    await message.answer(text)


async def handle_sync_completed_notification(message: Message, data: dict):
    """Обработать уведомление о завершении синхронизации"""
    sync_data = data.get("data", {})
    
    text = "✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА\n\n"
    text += f"⏱️ Время: {sync_data.get('duration_seconds', 0)} сек\n"
    text += f"📊 Обновлено: {sync_data.get('updates_count', 0)} записей\n"
    
    if sync_data.get("errors_count", 0) > 0:
        text += f"⚠️ Ошибок: {sync_data.get('errors_count', 0)}\n"
    
    text += "\n💡 Данные обновлены и готовы к использованию"
    
    await message.answer(text)