import sys
import logging
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

from core.states import NotificationStates
from core.config import config
from keyboards.keyboards import wb_menu_keyboard, main_keyboard, create_notification_keyboard
from api.client import bot_api_client
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
    """Показать настройки уведомлений (с сервера)"""
    await state.set_state(NotificationStates.settings_menu)

    user_id = callback.from_user.id
    response = await bot_api_client.get_notification_settings(user_id)

    if response.success and response.data:
        settings = response.data.get("data", response.data)  # APIResponse wraps data
        await callback.message.edit_text(
            "🔔 НАСТРОЙКИ УВЕДОМЛЕНИЙ\n\n"
            "Нажмите на тип уведомления для переключения:\n\n"
            "✅ Вкл | ❌ Выкл",
            reply_markup=create_notification_keyboard(settings)
        )
    else:
        await callback.message.edit_text(
            f"❌ Не удалось получить настройки уведомлений.\n\n{response.error or ''}",
            reply_markup=wb_menu_keyboard()
        )
    await callback.answer()


async def _toggle_and_refresh(callback: CallbackQuery, key: str):
    """Вспомогательная: инвертировать флаг key и перерисовать меню"""
    user_id = callback.from_user.id
    # Получаем текущие настройки
    current = await bot_api_client.get_notification_settings(user_id)
    settings = current.data.get("data", current.data) if current.success and current.data else {}
    current_value = bool(settings.get(key, False))
    # Отправляем обновление
    update = {key: not current_value}
    upd_resp = await bot_api_client.update_notification_settings(user_id, update)
    if not upd_resp.success:
        await callback.answer(f"❌ Ошибка обновления: {upd_resp.error or upd_resp.status_code}", show_alert=True)
        return
    # Получаем обновлённые
    refreshed = await bot_api_client.get_notification_settings(user_id)
    new_settings = refreshed.data.get("data", refreshed.data) if refreshed.success and refreshed.data else settings
    # Обновляем текст/клавиатуру
    await callback.message.edit_text(
        "🔔 НАСТРОЙКИ УВЕДОМЛЕНИЙ\n\n"
        "Нажмите на тип уведомления для переключения:\n\n"
        "✅ Вкл | ❌ Выкл",
        reply_markup=create_notification_keyboard(new_settings)
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notif_new_orders")
async def toggle_notif_new_orders(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "new_orders_enabled")


@router.callback_query(F.data == "toggle_notif_critical_stocks")
async def toggle_notif_critical_stocks(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "critical_stocks_enabled")


@router.callback_query(F.data == "toggle_notif_negative_reviews")
async def toggle_notif_negative_reviews(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "negative_reviews_enabled")


@router.callback_query(F.data == "toggle_notif_grouping")
async def toggle_notif_grouping(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "grouping_enabled")


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


# Polling обработчики для получения уведомлений от сервера
async def handle_new_order_notification(message: Message, data: dict):
    """Обработать уведомление о новом заказе"""
    order_data = data.get("data", {})
    
    order_id = order_data.get('order_id', 'N/A')
    order_date = order_data.get('date', 'N/A')
    brand = order_data.get('brand', 'N/A')
    product_name = order_data.get('product_name', 'N/A')
    nm_id = order_data.get('nm_id', 'N/A')
    supplier_article = order_data.get('supplier_article', '')
    size = order_data.get('size', '')
    barcode = order_data.get('barcode', '')
    warehouse_from = order_data.get('warehouse_from', 'N/A')
    warehouse_to = order_data.get('warehouse_to', 'N/A')
    order_amount = order_data.get('amount', 0)
    commission_percent = order_data.get('commission_percent', 0)
    commission_amount = order_data.get('commission_amount', 0)
    spp_percent = order_data.get('spp_percent', 0)
    customer_price = order_data.get('customer_price', 0)
    # Логистика исключена из системы
    dimensions = order_data.get('dimensions', '')
    volume_liters = order_data.get('volume_liters', 0)
    warehouse_rate_per_liter = order_data.get('warehouse_rate_per_liter', 0)
    warehouse_rate_extra = order_data.get('warehouse_rate_extra', 0)
    rating = order_data.get('rating', 0)
    reviews_count = order_data.get('reviews_count', 0)
    buyout_rates = order_data.get('buyout_rates', {})
    order_speed = order_data.get('order_speed', {})
    sales_periods = order_data.get('sales_periods', {})
    category_availability = order_data.get('category_availability', '')
    stocks = order_data.get('stocks', {})
    stock_days = order_data.get('stock_days', {})
    
    text = f"🧾 Заказ [#{order_id}] {order_date}\n\n"
    text += f"👑 {brand} ({brand})\n"
    text += f"✏ Название: {product_name}\n"
    text += f"🆔 {nm_id} / {supplier_article} / ({size})\n"
    text += f"🎹 {barcode}\n"
    text += f"🚛 {warehouse_from} ⟶ {warehouse_to}\n"
    text += f"💰 Цена заказа: {order_amount:,.0f}₽\n"
    text += f"💶 Комиссия WB: {commission_percent}% ({commission_amount:,.0f}₽)\n"
    text += f"🛍 СПП: {spp_percent}% (Цена для покупателя: {customer_price:,.0f}₽)\n"
    # Логистика исключена из системы
    text += f"        Габариты: {dimensions}. ({volume_liters}л.)\n"
    text += f"        Тариф склада: {warehouse_rate_per_liter:,.1f}₽ за 1л. | {warehouse_rate_extra:,.1f}₽ за л. свыше)\n"
    text += f"🌟 Оценка: {rating}\n"
    text += f"💬 Отзывы: {reviews_count}\n"
    text += f"⚖️ Выкуп/с учетом возврата (7/14/30):\n"
    text += f"        {buyout_rates.get('7_days', 0):.1f}% / {buyout_rates.get('14_days', 0):.1f}% / {buyout_rates.get('30_days', 0):.1f}%\n"
    text += f"💠 Скорость заказов за 7/14/30 дней:\n"
    text += f"        {order_speed.get('7_days', 0):.2f} | {order_speed.get('14_days', 0):.1f} | {order_speed.get('30_days', 0):.1f} шт. в день\n"
    text += f"📖 Продаж за 7 / 14 / 30 дней:\n"
    text += f"        {sales_periods.get('7_days', 0)} | {sales_periods.get('14_days', 0)} | {sales_periods.get('30_days', 0)} шт.\n"
    text += f"💈 Оборачиваемость категории 90:\n"
    text += f"        {category_availability}\n"
    text += f"📦 Остаток:\n"
    for size in ["L", "M", "S", "XL"]:
        stock_count = stocks.get(size, 0)
        stock_days_count = stock_days.get(size, 0)
        text += f"        {size} ({stock_count} шт.) ≈ на {stock_days_count} дн.\n"
    
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


async def handle_error_notification(message: Message, data: dict):
    """Обработать уведомление об ошибке"""
    error_data = data.get("data", {})
    error_type = error_data.get("type", "unknown")
    error_message = error_data.get("message", "Произошла ошибка")
    
    text = f"⚠️ **Ошибка системы**\n\n"
    text += f"Тип: {error_type}\n"
    text += f"Описание: {error_message}\n\n"
    text += "🔄 Попробуйте обновить данные или обратитесь в поддержку"
    
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


async def handle_cabinet_removal_notification(telegram_id: int, data: dict):
    """Обработать уведомление об удалении кабинета"""
    try:
        # Импортируем бота из основного модуля
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from core.config import config
        from aiogram import Bot
        
        # Создаем экземпляр бота
        bot = Bot(token=config.bot_token)
        
        from keyboards.keyboards import create_cabinet_removal_keyboard
        from utils.formatters import format_datetime
        
        cabinet_id = data.get('cabinet_id', 'N/A')
        cabinet_name = data.get('cabinet_name', 'Неизвестный кабинет')
        removal_reason = data.get('removal_reason', 'Неизвестная причина')
        removal_timestamp = data.get('removal_timestamp', '')
        validation_error = data.get('validation_error', {})
        
        # Форматируем время удаления
        if removal_timestamp:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(removal_timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%d.%m.%Y %H:%M')
            except:
                formatted_time = removal_timestamp
        else:
            formatted_time = 'Неизвестно'
        
        # Формируем сообщение
        text = "🚨 КАБИНЕТ УДАЛЕН\n\n"
        text += f"Кабинет \"{cabinet_name}\" был автоматически удален из-за недействительного API ключа.\n\n"
        text += f"**Причина:** {removal_reason}\n"
        text += f"**Время удаления:** {formatted_time}\n\n"
        
        # Добавляем детали ошибки валидации, если есть
        if validation_error and validation_error.get('message'):
            text += f"**Детали ошибки:** {validation_error['message']}\n\n"
        
        text += "Для продолжения работы подключите новый кабинет с действующим API ключом."
        
        # Создаем клавиатуру
        keyboard = create_cabinet_removal_keyboard()
        
        # Отправляем уведомление пользователю
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Cabinet removal notification sent to user {telegram_id}")
        
        # Закрываем сессию бота
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Error sending cabinet removal notification to user {telegram_id}: {e}")
        # Закрываем сессию бота в случае ошибки
        try:
            await bot.session.close()
        except:
            pass
        raise