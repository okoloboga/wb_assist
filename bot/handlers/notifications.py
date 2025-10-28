import sys
import logging
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from utils.formatters import format_currency
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
    user_id = callback.from_user.id
    
    # Загружаем реальные настройки с сервера
    response = await bot_api_client.get_notification_settings(user_id)
    
    if response.success and response.data:
        settings = response.data.get("data", response.data)
        
        # Вспомогательная функция для форматирования порога отзывов
        review_threshold = settings.get('review_rating_threshold', 3)
        if review_threshold == 0:
            review_status = "Выключены"
        else:
            stars = "⭐" * review_threshold
            review_status = f"Включены {stars} (≤{review_threshold}★)"
        
        # Формируем статус на основе реальных настроек
        status_text = "📊 Статус уведомлений:\n"
        status_text += f"✅ Заказы: {'Включены' if settings.get('new_orders_enabled', True) else 'Выключены'}\n"
        status_text += f"✅ Выкупы: {'Включены' if settings.get('order_buyouts_enabled', True) else 'Выключены'}\n"
        status_text += f"✅ Отмены: {'Включены' if settings.get('order_cancellations_enabled', True) else 'Выключены'}\n"
        status_text += f"✅ Возвраты: {'Включены' if settings.get('order_returns_enabled', True) else 'Выключены'}\n"
        status_text += f"✅ Отзывы: {review_status}\n"  # ИЗМЕНЕНО
        status_text += f"✅ Остатки: {'Включены' if settings.get('critical_stocks_enabled', True) else 'Выключены'}\n"
        
        await callback.message.edit_text(
            f"🔔 УВЕДОМЛЕНИЯ\n\n{status_text}\n"
            "Нажмите на тип уведомления для переключения:",
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
    
    # Вспомогательная функция для форматирования порога отзывов
    review_threshold = new_settings.get('review_rating_threshold', 3)
    if review_threshold == 0:
        review_status = "Выключены"
    else:
        stars = "⭐" * review_threshold
        review_status = f"Включены {stars} (≤{review_threshold}★)"
    
    # Формируем статус на основе обновленных настроек
    status_text = "📊 Статус уведомлений:\n"
    status_text += f"✅ Заказы: {'Включены' if new_settings.get('new_orders_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Выкупы: {'Включены' if new_settings.get('order_buyouts_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Отмены: {'Включены' if new_settings.get('order_cancellations_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Возвраты: {'Включены' if new_settings.get('order_returns_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Отзывы: {review_status}\n"  # ИЗМЕНЕНО
    status_text += f"✅ Остатки: {'Включены' if new_settings.get('critical_stocks_enabled', True) else 'Выключены'}\n"
    
    # Обновляем текст/клавиатуру
    await callback.message.edit_text(
        f"🔔 УВЕДОМЛЕНИЯ\n\n{status_text}\n"
        "Нажмите на тип уведомления для переключения:",
        reply_markup=create_notification_keyboard(new_settings)
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notif_new_orders")
async def toggle_notif_new_orders(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "new_orders_enabled")


@router.callback_query(F.data == "toggle_notif_buyouts")
async def toggle_notif_buyouts(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "order_buyouts_enabled")


@router.callback_query(F.data == "toggle_notif_cancellations")
async def toggle_notif_cancellations(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "order_cancellations_enabled")


@router.callback_query(F.data == "toggle_notif_returns")
async def toggle_notif_returns(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "order_returns_enabled")


@router.callback_query(F.data == "toggle_notif_negative_reviews")
async def toggle_notif_negative_reviews(callback: CallbackQuery):
    """Циклически изменяем порог: 3 -> 4 -> 5 -> 0 -> 1 -> 2 -> 3"""
    user_id = callback.from_user.id
    
    # Получаем текущие настройки
    current = await bot_api_client.get_notification_settings(user_id)
    settings = current.data.get("data", current.data) if current.success and current.data else {}
    
    # Получаем текущий порог (по умолчанию 3)
    current_threshold = settings.get('review_rating_threshold', 3)
    
    # Циклическое переключение: 3 -> 4 -> 5 -> 0 -> 1 -> 2 -> 3
    next_threshold = (current_threshold % 5) + 1 if current_threshold < 5 else 0
    
    # Если включили с 0, начинаем с 1
    if current_threshold == 0:
        next_threshold = 1
    
    # Обновляем порог и включаем уведомления, если порог > 0
    update = {
        "review_rating_threshold": next_threshold,
        "negative_reviews_enabled": next_threshold > 0  # Автоматически включаем/выключаем
    }
    
    upd_resp = await bot_api_client.update_notification_settings(user_id, update)
    if not upd_resp.success:
        await callback.answer(f"❌ Ошибка обновления: {upd_resp.error or upd_resp.status_code}", show_alert=True)
        return
    
    # Получаем обновлённые настройки
    refreshed = await bot_api_client.get_notification_settings(user_id)
    new_settings = refreshed.data.get("data", refreshed.data) if refreshed.success and refreshed.data else settings
    
    # Формируем обновленный статус
    review_threshold = new_settings.get('review_rating_threshold', 3)
    if review_threshold == 0:
        review_status = "Выключены"
        callback_text = "❌ Уведомления по отзывам отключены"
    else:
        stars = "⭐" * review_threshold
        review_status = f"Включены {stars} (≤{review_threshold}★)"
        callback_text = f"✅ Порог установлен: {stars} (≤{review_threshold}★)"
    
    status_text = "📊 Статус уведомлений:\n"
    status_text += f"✅ Заказы: {'Включены' if new_settings.get('new_orders_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Выкупы: {'Включены' if new_settings.get('order_buyouts_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Отмены: {'Включены' if new_settings.get('order_cancellations_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Возвраты: {'Включены' if new_settings.get('order_returns_enabled', True) else 'Выключены'}\n"
    status_text += f"✅ Отзывы: {review_status}\n"
    status_text += f"✅ Остатки: {'Включены' if new_settings.get('critical_stocks_enabled', True) else 'Выключены'}\n"
    
    # Обновляем текст/клавиатуру
    await callback.message.edit_text(
        f"🔔 УВЕДОМЛЕНИЯ\n\n{status_text}\n"
        "Нажмите на тип уведомления для переключения:",
        reply_markup=create_notification_keyboard(new_settings)
    )
    await callback.answer(callback_text)


@router.callback_query(F.data == "toggle_notif_critical_stocks")
async def toggle_notif_critical_stocks(callback: CallbackQuery):
    await _toggle_and_refresh(callback, "critical_stocks_enabled")


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
    text += f"💰 Цена заказа: {format_currency(order_amount)}\n"
    text += f"💶 Комиссия WB: {commission_percent}% ({format_currency(commission_amount)})\n"
    text += f"🛍 СПП: {spp_percent}% (Цена для покупателя: {format_currency(customer_price)})\n"
    # Логистика исключена из системы
    text += f"        Габариты: {dimensions}. ({volume_liters}л.)\n"
    text += f"        Тариф склада: {format_currency(warehouse_rate_per_liter)} за 1л. | {format_currency(warehouse_rate_extra)} за л. свыше)\n"
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
    """Обработать уведомление о критичных остатках - СТАРАЯ ЛОГИКА (пороговая)"""
    nm_id = data.get("nm_id", "N/A")
    name = data.get("name", f"Товар {nm_id}")
    brand = data.get("brand", "")
    total_quantity = data.get("total_quantity", 0)
    stocks_by_warehouse = data.get("stocks_by_warehouse", {})
    image_url = data.get("image_url")
    
    text = f"""⚠️ КРИТИЧНЫЕ ОСТАТКИ

👗 {name} ({brand})
🆔 {nm_id}

📊 Остатки:"""
    
    # Показываем только склады с остатками > 0 (без размеров)
    for warehouse_name, sizes in stocks_by_warehouse.items():
        warehouse_total = sum(sizes.values())
        if warehouse_total > 0:
            text += f"\n📦 {warehouse_name}: {warehouse_total} шт."
    
    text += f"""

⚠️ Общий остаток: {total_quantity} шт. (критично ≤ 10)"""
    
    # Отправляем с изображением если есть
    if image_url:
        await message.answer_photo(
            photo=image_url,
            caption=text
        )
    else:
        await message.answer(text)


async def handle_dynamic_stock_alert(message: Message, data: dict):
    """Обработать динамический алерт остатков - НОВАЯ ЛОГИКА на основе заказов"""
    # Сервер уже формирует готовый текст, просто отправляем его
    telegram_text = data.get("telegram_text", "⚠️ Критические остатки")
    image_url = data.get("data", {}).get("image_url")
    
    # Отправляем с изображением если есть
    if image_url:
        await message.answer_photo(
            photo=image_url,
            caption=telegram_text
        )
    else:
        await message.answer(telegram_text)


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