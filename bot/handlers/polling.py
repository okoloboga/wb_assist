"""
Polling система для получения уведомлений от сервера
"""
import asyncio
import logging
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from utils.timezone import TimezoneUtils

from core.config import config
from handlers.notifications import (
    handle_new_order_notification,
    handle_critical_stocks_notification,
    handle_new_review_notification,
    handle_cabinet_removal_notification,
    handle_error_notification
)

logger = logging.getLogger(__name__)

class NotificationPoller:
    """Polling система для получения уведомлений"""
    
    def __init__(self, bot):
        self.bot = bot
        self.server_url = config.server_host
        self.api_key = config.api_secret_key
        self.polling_interval = config.polling_interval  # Из конфигурации
        self.last_check_times = {}  # {telegram_id: datetime}
        self.user_last_activity = {}  # {telegram_id: datetime} - время последней активности
        self.is_running = False
        self.max_inactive_hours = 24  # Удаляем пользователей неактивных более 24 часов
        self._last_cleanup = None
        
    async def start_polling(self):
        """Запуск polling системы"""
        self.is_running = True
        logger.info("🔄 Starting notification polling system...")
        
        while self.is_running:
            try:
                await self._poll_notifications()
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(30)  # Пауза при ошибке
    
    async def stop_polling(self):
        """Остановка polling системы"""
        self.is_running = False
        logger.info("🛑 Stopping notification polling system...")
    
    async def _cleanup_inactive_users(self):
        """Очистка неактивных пользователей"""
        now = TimezoneUtils.now_msk()
        inactive_users = []
        
        for telegram_id, last_activity in self.user_last_activity.items():
            if (now - last_activity).total_seconds() > self.max_inactive_hours * 3600:
                inactive_users.append(telegram_id)
        
        for telegram_id in inactive_users:
            self.last_check_times.pop(telegram_id, None)
            self.user_last_activity.pop(telegram_id, None)
            logger.info(f"🧹 Удален неактивный пользователь {telegram_id}")
        
        if inactive_users:
            logger.info(f"🧹 Очищено {len(inactive_users)} неактивных пользователей")
    
    async def _poll_notifications(self):
        """Опрос сервера на предмет новых уведомлений"""
        try:
            # Очищаем неактивных пользователей каждые 10 минут
            if self._last_cleanup is None or (TimezoneUtils.now_msk() - self._last_cleanup).total_seconds() > 600:
                await self._cleanup_inactive_users()
                self._last_cleanup = TimezoneUtils.now_msk()
            
            # Получаем список активных пользователей
            active_users = await self._get_active_users()
            
            if not active_users:
                return
            
            # Получаем уведомления для всех пользователей
            async with aiohttp.ClientSession() as session:
                for telegram_id in active_users:
                    try:
                        await self._check_user_notifications(session, telegram_id)
                    except Exception as e:
                        logger.error(f"Error checking notifications for user {telegram_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in _poll_notifications: {e}")
    
    async def _get_active_users(self) -> List[int]:
        """Получение списка активных пользователей"""
        # Пока возвращаем тестового пользователя
        # В будущем можно получать из базы данных или кэша
        return [5101525651]  # Ваш telegram_id
    
    async def _check_user_notifications(self, session: aiohttp.ClientSession, telegram_id: int):
        """Проверка уведомлений для конкретного пользователя"""
        try:
            logger.info(f"🔍 Checking notifications for user {telegram_id}")
            
            # Обновляем время последней активности пользователя
            self.user_last_activity[telegram_id] = TimezoneUtils.now_msk()
            
            # Получаем время последней проверки в МСК
            last_check = self.last_check_times.get(telegram_id)
            if not last_check:
                # При первом запуске устанавливаем время на 1 минуту назад в МСК
                last_check = TimezoneUtils.now_msk() - timedelta(minutes=1)
                self.last_check_times[telegram_id] = last_check
                logger.info(f"🔄 First polling for user {telegram_id} - using 1 minute ago as last_check")
                # НЕ возвращаемся, продолжаем с запросом
            
            # Формируем URL для запроса
            url = f"{self.server_url}/api/v1/notifications/poll"
            params = {
                "telegram_id": telegram_id,
                "last_check": last_check.isoformat()
            }
            headers = {
                "X-API-SECRET-KEY": self.api_key
            }
            
            # Отправляем запрос
            async with session.get(url, params=params, headers=headers) as response:
                logger.info(f"📡 Server response: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"📊 Response data: success={data.get('success')}, events_count={len(data.get('events', []))}")
                    
                    if data.get("success") and data.get("events"):
                        await self._process_events(telegram_id, data["events"])
                        logger.info(f"📥 Processed {len(data['events'])} events for user {telegram_id}")
                    else:
                        logger.info(f"📭 No events to process for user {telegram_id}")
                    
                    # Обновляем время последней проверки в МСК
                    server_last_check = data.get("last_check")
                    if server_last_check:
                        try:
                            # Парсим время с сервера и конвертируем в МСК
                            server_time = datetime.fromisoformat(server_last_check.replace('Z', '+00:00'))
                            self.last_check_times[telegram_id] = TimezoneUtils.to_msk(server_time)
                        except Exception:
                            self.last_check_times[telegram_id] = TimezoneUtils.now_msk()
                    else:
                        self.last_check_times[telegram_id] = TimezoneUtils.now_msk()
                    
                elif response.status == 404:
                    logger.warning(f"User {telegram_id} not found on server")
                else:
                    logger.error(f"Server returned status {response.status} for user {telegram_id}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking notifications for user {telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking notifications for user {telegram_id}: {e}")
    
    async def _process_events(self, telegram_id: int, events: List[Dict[str, Any]]):
        """Обработка полученных событий"""
        for event in events:
            try:
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                logger.info(f"🔄 Processing event {event_type} for user {telegram_id}")
                
                # Создаем фиктивные объекты для обработчиков
                from aiogram.types import Message, Chat, User
                
                fake_chat = Chat(
                    id=telegram_id,
                    type='private'
                )
                
                fake_user = User(
                    id=telegram_id,
                    is_bot=False,
                    first_name='User'
                )
                
                fake_message = Message(
                    message_id=0,
                    date=datetime.now(),
                    chat=fake_chat,
                    from_user=fake_user,
                    content_type='text',
                    text='',
                    web_app_data=None
                )
                
                # Обрабатываем событие в зависимости от типа
                if event_type == "new_order":
                    # Если сервер прислал готовый текст, используем его. При наличии image_url отправляем как фото
                    telegram_text = event.get("telegram_text")
                    data_payload = event.get("data", {}) or {}
                    image_url = data_payload.get("image_url")
                    
                    # Логируем информацию об изображении для отладки
                    if image_url:
                        logger.info(f"🖼️ Sending photo for order {data_payload.get('order_id', 'unknown')}: {image_url}")
                    else:
                        logger.warning(f"⚠️ No image URL for order {data_payload.get('order_id', 'unknown')}")
                    
                    if telegram_text and image_url:
                        try:
                            await self.bot.send_photo(chat_id=telegram_id, photo=image_url, caption=telegram_text)
                            logger.info(f"✅ Photo sent successfully for order {data_payload.get('order_id', 'unknown')}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send photo: {e}, falling back to text")
                            await self.bot.send_message(chat_id=telegram_id, text=telegram_text)
                    elif telegram_text:
                        await self.bot.send_message(chat_id=telegram_id, text=telegram_text)
                    else:
                        await self._handle_new_order_notification(telegram_id, event_data)
                elif event_type == "critical_stocks":
                    await self._handle_critical_stocks_notification(telegram_id, event_data)
                elif event_type == "new_review":
                    await self._handle_new_review_notification(telegram_id, event_data)
                elif event_type == "negative_review":
                    await self._handle_negative_review_notification(telegram_id, event_data)
                elif event_type == "order_buyout":
                    await self._handle_order_buyout_notification(telegram_id, event_data)
                elif event_type == "order_cancellation":
                    await self._handle_order_cancellation_notification(telegram_id, event_data)
                elif event_type == "order_return":
                    await self._handle_order_return_notification(telegram_id, event_data)
                elif event_type == "cabinet_removal":
                    await self._handle_cabinet_removal_notification(telegram_id, event_data)
                elif event_type == "system_error":
                    await self._handle_error_notification(telegram_id, event_data)
                elif event_type == "sync_completed":
                    await self._handle_sync_completed_notification(telegram_id, event_data)
                else:
                    logger.warning(f"Unknown event type: {event_type}")
                    
            except Exception as e:
                logger.error(f"Error processing event {event.get('type')} for user {telegram_id}: {e}")
                # Отправляем уведомление об ошибке пользователю
                await self._handle_error_notification(telegram_id, {
                    "type": "event_processing_error",
                    "message": f"Ошибка обработки события: {str(e)}"
                })
    
    async def _handle_universal_notification(self, telegram_id: int, event_data: dict, notification_type: str):
        """Универсальная обработка уведомлений в детальном формате"""
        # Специальная обработка для отзывов (оставляем как есть)
        if notification_type in ["new_review", "negative_review"]:
            product_name = event_data.get('product_name', 'N/A')
            rating = event_data.get('rating', 0)
            text = event_data.get('text', 'N/A')
            user_name = event_data.get('user_name', 'N/A')
            review_id = event_data.get('review_id', 'N/A')
            
            # Обрезаем длинный текст
            display_text = text[:100] + ('...' if len(text) > 100 else '')
            
            icon = "⭐" if notification_type == "new_review" else "😞"
            title = "НОВЫЙ ОТЗЫВ" if notification_type == "new_review" else "НЕГАТИВНЫЙ ОТЗЫВ"
            
            message_text = f"""{icon} {title}

📦 {product_name}
⭐ Рейтинг: {rating}/5
💬 "{display_text}"
👤 Автор: {user_name}
🆔 ID отзыва: {review_id}"""
            
            if notification_type == "new_review":
                message_text += "\n\n💡 Нажмите /reviews для просмотра всех отзывов"
            else:
                message_text += "\n\n⚠️ Рекомендуется ответить на отзыв или связаться с покупателем"
            
            await self.bot.send_message(chat_id=telegram_id, text=message_text)
            logger.info(f"✅ {notification_type} notification sent to user {telegram_id}")
            return
        
        # Специальная обработка для остатков (оставляем как есть)
        if notification_type == "critical_stocks":
            product_name = event_data.get('name') or event_data.get('product_name') or event_data.get('title') or f"Товар {event_data.get('nm_id', 'N/A')}"
            nm_id = event_data.get('nm_id', 'N/A')
            stocks = event_data.get('stocks', {})
            critical_sizes = event_data.get("critical_sizes", [])
            
            message_text = f"""⚠️ КРИТИЧЕСКИЕ ОСТАТКИ

📦 {product_name}
🆔 {nm_id}
📊 Остатки: {stocks}"""
            
            if critical_sizes:
                message_text += f"\n⚠️ Критично: {', '.join(critical_sizes)}"
            
            await self.bot.send_message(chat_id=telegram_id, text=message_text)
            logger.info(f"✅ {notification_type} notification sent to user {telegram_id}")
            return
        
        # Для всех типов заказов используем детальный формат
        await self._handle_detailed_order_notification(telegram_id, event_data, notification_type)
    
    async def _handle_detailed_order_notification(self, telegram_id: int, event_data: dict, notification_type: str):
        """Детальное уведомление о заказе (как в меню)"""
        # Определяем статус для заголовка
        status_map = {
            "new_order": "НОВЫЙ ЗАКАЗ",
            "order_buyout": "ЗАКАЗ ВЫКУПЛЕН", 
            "order_cancellation": "ЗАКАЗ ОТМЕНЕН",
            "order_return": "ЗАКАЗ ВОЗВРАЩЕН"
        }
        
        status = status_map.get(notification_type, "ЗАКАЗ")
        
        # Основная информация
        order_id = event_data.get("order_id", event_data.get("id", "N/A"))
        order_date = self._format_datetime(event_data.get("date", event_data.get("order_date", "")))
        brand = event_data.get("brand", "Неизвестно")
        product_name = event_data.get("product_name", event_data.get("name", "Неизвестно"))
        nm_id = event_data.get("nm_id", "N/A")
        supplier_article = event_data.get("supplier_article", event_data.get("article", ""))
        size = event_data.get("size", "")
        barcode = event_data.get("barcode", "")
        warehouse_from = event_data.get("warehouse_from", "")
        warehouse_to = event_data.get("warehouse_to", "")
        
        # Финансовая информация
        order_amount = event_data.get("amount", event_data.get("total_price", 0))
        spp_percent = event_data.get("spp_percent", 0)
        customer_price = event_data.get("customer_price", 0)
        logistics_amount = event_data.get("logistics_amount", 0)
        
        # Логистика
        dimensions = event_data.get("dimensions", "")
        volume_liters = event_data.get("volume_liters", 0)
        warehouse_rate_per_liter = event_data.get("warehouse_rate_per_liter", 0)
        warehouse_rate_extra = event_data.get("warehouse_rate_extra", 0)
        
        # Рейтинги и отзывы
        rating = event_data.get("rating", 0)
        reviews_count = event_data.get("reviews_count", 0)
        
        # Статистика
        sales_periods = event_data.get("sales_periods", {})
        
        # Остатки
        stocks = event_data.get("stocks", {})
        stock_days = event_data.get("stock_days", {})
        
        # Формируем сообщение в том же формате, что и в меню
        message = f"🧾 {status} [#{order_id}] {order_date}\n\n"
        message += f"✏ {product_name}\n"
        message += f"🆔 {nm_id} / {supplier_article} / ({size})\n"
        if barcode:
            message += f"🎹 {barcode}\n"
        message += f"🚛 {warehouse_from} ⟶ {warehouse_to}\n"
        message += f"💰 Цена заказа: {order_amount:,.0f}₽\n"
        
        # Условное отображение полей
        if spp_percent or customer_price:
            message += f"🛍 СПП: {spp_percent}% (Цена для покупателя: {customer_price:,.0f}₽)\n"
        if logistics_amount:
            message += f"💶 Логистика WB: {logistics_amount:,.1f}₽\n"
        if dimensions or volume_liters:
            message += f"        Габариты: {dimensions}. ({volume_liters}л.)\n"
        if warehouse_rate_per_liter or warehouse_rate_extra:
            message += f"        Тариф склада: {warehouse_rate_per_liter:,.1f}₽ за 1л. | {warehouse_rate_extra:,.1f}₽ за л. свыше)\n"
        if rating or reviews_count:
            message += f"🌟 Оценка: {rating}\n"
        message += f"💬 Отзывы: {reviews_count}\n"
        
        # Продажи
        if sales_periods and any(sales_periods.values()):
            message += f"📖 Продаж за 7 / 14 / 30 дней:\n"
            message += f"        {sales_periods.get('7_days', 0)} | {sales_periods.get('14_days', 0)} | {sales_periods.get('30_days', 0)} шт.\n"
        
        # Остатки
        if stocks and any(stocks.values()):
            message += f"📦 Остаток:\n"
            for size in ["L", "M", "S", "XL"]:
                stock_count = stocks.get(size, 0)
                stock_days_count = stock_days.get(size, 0)
                if stock_count > 0 or stock_days_count > 0:
                    message += f"        {size} ({stock_count} шт.) ≈ на {stock_days_count} дн.\n"
        
        # Проверяем наличие изображения
        image_url = event_data.get("image_url")
        
        if image_url:
            try:
                await self.bot.send_photo(chat_id=telegram_id, photo=image_url, caption=message)
                logger.info(f"✅ Photo sent successfully for {notification_type}")
            except Exception as e:
                logger.error(f"❌ Failed to send photo: {e}, falling back to text")
                await self.bot.send_message(chat_id=telegram_id, text=message)
        else:
            await self.bot.send_message(chat_id=telegram_id, text=message)
        
        logger.info(f"✅ {notification_type} notification sent to user {telegram_id}")
    
    def _format_datetime(self, datetime_str: str) -> str:
        """Форматирование даты и времени"""
        try:
            if not datetime_str:
                return "Неизвестно"
            
            # Парсим дату и конвертируем в МСК
            from datetime import datetime
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            msk_dt = TimezoneUtils.to_msk(dt)
            
            return msk_dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return datetime_str

    # Алиасы для обратной совместимости
    async def _handle_new_order_notification(self, telegram_id: int, event_data: dict):
        await self._handle_universal_notification(telegram_id, event_data, "new_order")
    
    async def _handle_critical_stocks_notification(self, telegram_id: int, event_data: dict):
        await self._handle_universal_notification(telegram_id, event_data, "critical_stocks")
    
    async def _handle_new_review_notification(self, telegram_id: int, event_data: dict):
        await self._handle_universal_notification(telegram_id, event_data, "new_review")
    
    async def _handle_negative_review_notification(self, telegram_id: int, event_data: dict):
        await self._handle_universal_notification(telegram_id, event_data, "negative_review")
    
    async def _handle_order_buyout_notification(self, telegram_id: int, event_data: dict):
        await self._handle_universal_notification(telegram_id, event_data, "order_buyout")
    
    async def _handle_order_cancellation_notification(self, telegram_id: int, event_data: dict):
        await self._handle_universal_notification(telegram_id, event_data, "order_cancellation")
    
    async def _handle_order_return_notification(self, telegram_id: int, event_data: dict):
        await self._handle_universal_notification(telegram_id, event_data, "order_return")
    
    async def _handle_cabinet_removal_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления об удалении кабинета"""
        cabinet_data = event_data
        
        text = "🚨 КАБИНЕТ УДАЛЕН\n\n"
        text += f"Кабинет \"{cabinet_data.get('cabinet_name', 'N/A')}\" был автоматически удален из-за недействительного API ключа.\n\n"
        text += f"**Причина:** {cabinet_data.get('removal_reason', 'N/A')}\n"
        text += f"**Время удаления:** {cabinet_data.get('removal_timestamp', 'N/A')}\n\n"
        
        validation_error = cabinet_data.get('validation_error', {})
        if validation_error and validation_error.get('message'):
            text += f"**Детали ошибки:** {validation_error['message']}\n\n"
        
        text += "Для продолжения работы подключите новый кабинет с действующим API ключом."
        
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ Cabinet removal notification sent to user {telegram_id}")

    async def _handle_error_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления об ошибке"""
        error_type = event_data.get("type", "unknown")
        error_message = event_data.get("message", "Произошла ошибка")
        
        text = f"⚠️ **Ошибка системы**\n\n"
        text += f"Тип: {error_type}\n"
        text += f"Описание: {error_message}\n\n"
        text += "🔄 Попробуйте обновить данные или обратитесь в поддержку"
        
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ Error notification sent to user {telegram_id}")
    
    async def _handle_sync_completed_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления о завершении синхронизации"""
        try:
            # Проверяем, это ли первая синхронизация
            is_first_sync = event_data.get("is_first_sync", False)
            
            if not is_first_sync:
                # Это периодическая синхронизация - не показываем меню
                logger.info(f"🔄 Periodic sync completed for user {telegram_id}, skipping menu")
                return
            
            # Это первая синхронизация - показываем главное меню
            logger.info(f"🏁 First sync completed for user {telegram_id}, showing main menu")
            
            # Получаем дашборд и показываем его
            from api.client import bot_api_client
            dashboard_response = await bot_api_client.get_dashboard(
                user_id=telegram_id
            )
            
            if dashboard_response.success:
                # Показываем дашборд с кнопкой главного меню
                from keyboards.keyboards import wb_menu_keyboard
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text="✅ Синхронизация завершена!\n\n" + 
                         (dashboard_response.telegram_text or "📊 Данные готовы к использованию!"),
                    reply_markup=wb_menu_keyboard()
                )
                logger.info(f"✅ Sync completion notification sent to user {telegram_id}")
            else:
                # Если дашборд не загрузился, показываем простое сообщение
                from keyboards.keyboards import wb_menu_keyboard
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text="✅ Синхронизация завершена!\n\n📊 Данные готовы к использованию!",
                    reply_markup=wb_menu_keyboard()
                )
                logger.info(f"✅ Sync completion notification sent to user {telegram_id}")
                
        except Exception as e:
            logger.error(f"Error handling sync completion notification for user {telegram_id}: {e}")
            # Fallback - простое сообщение
            from keyboards.keyboards import wb_menu_keyboard
            await self.bot.send_message(
                chat_id=telegram_id,
                text="✅ Синхронизация завершена!\n\n📊 Данные готовы к использованию!",
                reply_markup=wb_menu_keyboard()
            )


# Глобальный экземпляр poller'а
poller: Optional[NotificationPoller] = None

async def start_notification_polling(bot):
    """Запуск системы polling уведомлений"""
    global poller
    poller = NotificationPoller(bot)
    await poller.start_polling()

async def stop_notification_polling():
    """Остановка системы polling уведомлений"""
    global poller
    if poller:
        await poller.stop_polling()
