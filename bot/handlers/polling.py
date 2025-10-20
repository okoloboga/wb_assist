"""
Polling система для получения уведомлений от сервера
"""
import asyncio
import logging
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from core.config import config
from handlers.notifications import (
    handle_new_order_notification,
    handle_critical_stocks_notification,
    handle_new_review_notification,
    handle_cabinet_removal_notification
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
        self.is_running = False
        
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
    
    async def _poll_notifications(self):
        """Опрос сервера на предмет новых уведомлений"""
        try:
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
            # Получаем время последней проверки
            last_check = self.last_check_times.get(telegram_id)
            if not last_check:
                # При первом запуске устанавливаем время на 1 минуту назад
                # чтобы не получить старые данные, но получить данные после синхронизации
                last_check = datetime.now(timezone.utc) - timedelta(minutes=1)
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
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("success") and data.get("events"):
                        await self._process_events(telegram_id, data["events"])
                        logger.info(f"📥 Processed {len(data['events'])} events for user {telegram_id}")
                    
                    # Обновляем время последней проверки по серверному маркеру
                    server_last_check = data.get("last_check")
                    if server_last_check:
                        try:
                            self.last_check_times[telegram_id] = datetime.fromisoformat(server_last_check.replace('Z', '+00:00'))
                        except Exception:
                            self.last_check_times[telegram_id] = datetime.now(timezone.utc)
                    else:
                        self.last_check_times[telegram_id] = datetime.now(timezone.utc)
                    
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
                    if telegram_text and image_url:
                        try:
                            await self.bot.send_photo(chat_id=telegram_id, photo=image_url, caption=telegram_text)
                        except Exception:
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
                else:
                    logger.warning(f"Unknown event type: {event_type}")
                    
            except Exception as e:
                logger.error(f"Error processing event {event.get('type')} for user {telegram_id}: {e}")
    
    async def _handle_new_order_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления о новом заказе"""
        order_data = event_data
        text = self._format_detailed_order_notification(order_data, "ЗАКАЗ")
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ New order notification sent to user {telegram_id}")
    
    async def _handle_critical_stocks_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления о критичных остатках"""
        stock_data = event_data
        
        text = "⚠️ КРИТИЧНЫЕ ОСТАТКИ\n\n"
        product_name = stock_data.get('name') or stock_data.get('product_name') or stock_data.get('title') or f"Товар {stock_data.get('nm_id', 'N/A')}"
        text += f"📦 {product_name}\n"
        text += f"🆔 {stock_data.get('nm_id', 'N/A')}\n"
        text += f"📊 Остатки: {stock_data.get('stocks', {})}\n"
        
        critical_sizes = stock_data.get("critical_sizes", [])
        if critical_sizes:
            text += f"⚠️ Критично: {', '.join(critical_sizes)}\n"
        
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ Critical stocks notification sent to user {telegram_id}")
    
    async def _handle_new_review_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления о новом отзыве"""
        review_data = event_data
        
        text = "⭐ НОВЫЙ ОТЗЫВ!\n\n"
        text += f"📦 {review_data.get('product_name', 'N/A')}\n"
        text += f"⭐ Рейтинг: {review_data.get('rating', 0)}/5\n"
        text += f"💬 \"{review_data.get('text', 'N/A')[:100]}{'...' if len(review_data.get('text', '')) > 100 else ''}\"\n"
        text += f"👤 Автор: {review_data.get('user_name', 'N/A')}\n"
        text += f"🆔 ID отзыва: {review_data.get('review_id', 'N/A')}\n\n"
        text += "💡 Нажмите /reviews для просмотра всех отзывов"
        
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ New review notification sent to user {telegram_id}")
    
    async def _handle_negative_review_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления о негативном отзыве"""
        review_data = event_data
        
        text = "😞 НЕГАТИВНЫЙ ОТЗЫВ\n\n"
        text += f"📦 Товар: {review_data.get('product_name', 'N/A')}\n"
        text += f"⭐ Рейтинг: {review_data.get('rating', 0)}/5\n"
        text += f"💬 Текст: \"{review_data.get('text', 'N/A')[:100]}{'...' if len(review_data.get('text', '')) > 100 else ''}\"\n"
        text += f"👤 Автор: {review_data.get('user_name', 'N/A')}\n"
        text += f"🆔 ID отзыва: {review_data.get('review_id', 'N/A')}\n\n"
        text += "⚠️ Рекомендуется ответить на отзыв или связаться с покупателем"
        
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ Negative review notification sent to user {telegram_id}")
    
    async def _handle_order_buyout_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления о выкупе заказа"""
        order_data = event_data
        text = self._format_detailed_order_notification(order_data, "ВЫКУП")
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ Order buyout notification sent to user {telegram_id}")
    
    async def _handle_order_cancellation_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления об отмене заказа"""
        order_data = event_data
        text = self._format_detailed_order_notification(order_data, "ОТМЕНЕН")
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ Order cancellation notification sent to user {telegram_id}")
    
    async def _handle_order_return_notification(self, telegram_id: int, event_data: dict):
        """Обработка уведомления о возврате заказа"""
        order_data = event_data
        text = self._format_detailed_order_notification(order_data, "ВОЗВРАТ")
        await self.bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ Order return notification sent to user {telegram_id}")
    
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

    def _format_detailed_order_notification(self, order_data: dict, action_type: str) -> str:
        """Форматирование детального уведомления о заказе"""
        from datetime import datetime
        
        # Основная информация
        order_id = order_data.get('order_id', 'N/A')
        order_date = self._format_datetime(order_data.get('date', order_data.get('order_date', '')))
        brand = order_data.get('brand', 'N/A')
        product_name = order_data.get('product_name', order_data.get('name', 'N/A'))
        nm_id = order_data.get('nm_id', 'N/A')
        supplier_article = order_data.get('supplier_article', order_data.get('article', ''))
        size = order_data.get('size', '')
        barcode = order_data.get('barcode', '')
        warehouse_from = order_data.get('warehouse_from', 'N/A')
        warehouse_to = order_data.get('warehouse_to', 'N/A')
        
        # Финансовая информация
        order_amount = order_data.get('amount', order_data.get('total_price', 0))
        commission_percent = order_data.get('commission_percent', 0)
        commission_amount = order_data.get('commission_amount', 0)
        spp_percent = order_data.get('spp_percent', 0)
        customer_price = order_data.get('customer_price', 0)
        logistics_amount = order_data.get('logistics_amount', 0)
        
        # Логистика (могут отсутствовать в событиях)
        dimensions = order_data.get('dimensions', '')
        volume_liters = order_data.get('volume_liters', 0)
        warehouse_rate_per_liter = order_data.get('warehouse_rate_per_liter', 0)
        warehouse_rate_extra = order_data.get('warehouse_rate_extra', 0)
        
        # Рейтинги и отзывы (могут отсутствовать в событиях)
        rating = order_data.get('rating', 0)
        reviews_count = order_data.get('reviews_count', 0)
        
        # Статистика (могут отсутствовать в событиях)
        buyout_rates = order_data.get('buyout_rates', {})
        order_speed = order_data.get('order_speed', {})
        sales_periods = order_data.get('sales_periods', {})
        category_availability = order_data.get('category_availability', '')
        
        # Остатки (могут отсутствовать в событиях)
        stocks = order_data.get('stocks', {})
        stock_days = order_data.get('stock_days', {})
        
        # Формируем сообщение
        message = f"🧾 {action_type} [#{order_id}] {order_date}\n\n"
        message += f"👑 {brand} ({brand})\n"
        message += f"✏ Название: {product_name}\n"
        message += f"🆔 {nm_id} / {supplier_article} / ({size})\n"
        if barcode:
            message += f"🎹 {barcode}\n"
        message += f"🚛 {warehouse_from} ⟶ {warehouse_to}\n"
        message += f"💰 Цена заказа: {order_amount:,.0f}₽\n"
        
        # Финансовая информация (показываем только если есть данные)
        if spp_percent > 0 or customer_price > 0:
            message += f"🛍 СПП: {spp_percent}% (Цена для покупателя: {customer_price:,.0f}₽)\n"
        if logistics_amount > 0:
            message += f"💶 Логистика WB: {logistics_amount:,.1f}₽\n"
        
        # Логистическая информация (показываем только если есть данные)
        if dimensions or volume_liters > 0:
            message += f"        Габариты: {dimensions}. ({volume_liters}л.)\n"
        if warehouse_rate_per_liter > 0 or warehouse_rate_extra > 0:
            message += f"        Тариф склада: {warehouse_rate_per_liter:,.1f}₽ за 1л. | {warehouse_rate_extra:,.1f}₽ за л. свыше)\n"
        
        # Рейтинги и отзывы (показываем только если есть данные)
        if rating > 0 or reviews_count > 0:
            message += f"🌟 Оценка: {rating}\n"
            message += f"💬 Отзывы: {reviews_count}\n"
        
        # Дополнительная статистика (показываем только если есть данные)
        if sales_periods and any(sales_periods.values()):
            message += f"📖 Продаж за 7 / 14 / 30 дней:\n"
            message += f"        {sales_periods.get('7_days', 0)} | {sales_periods.get('14_days', 0)} | {sales_periods.get('30_days', 0)} шт.\n"
        
        # Остатки (показываем только если есть данные)
        if stocks and any(stocks.values()):
            message += f"📦 Остаток:\n"
            for size in ["L", "M", "S", "XL"]:
                stock_count = stocks.get(size, 0)
                stock_days_count = stock_days.get(size, 0)
                if stock_count > 0 or stock_days_count > 0:
                    message += f"        {size} ({stock_count} шт.) ≈ на {stock_days_count} дн.\n"
        
        return message

    def _format_datetime(self, datetime_str: str) -> str:
        """Форматирование даты и времени"""
        try:
            if not datetime_str:
                return "N/A"
            
            # Пытаемся распарсить ISO формат
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
        except:
            return datetime_str


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
