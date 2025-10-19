"""
Notification Service - единый сервис для всех типов уведомлений S3
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from .event_detector import EventDetector
from .status_monitor import StatusChangeMonitor
from .notification_generator import NotificationGenerator
from .crud import (
    NotificationSettingsCRUD,
    NotificationHistoryCRUD,
    OrderStatusHistoryCRUD
)
from app.features.bot_api.webhook import WebhookSender
from app.features.bot_api.formatter import BotMessageFormatter

logger = logging.getLogger(__name__)


class NotificationService:
    """Единый сервис для управления всеми уведомлениями"""
    
    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis_client = redis_client
        
        # Инициализируем компоненты
        self.event_detector = EventDetector()
        self.status_monitor = StatusChangeMonitor()
        self.notification_generator = NotificationGenerator()
        self.webhook_sender = WebhookSender()
        self.message_formatter = BotMessageFormatter()
        
        # Инициализируем CRUD
        self.settings_crud = NotificationSettingsCRUD()
        self.history_crud = NotificationHistoryCRUD()
        self.order_crud = OrderStatusHistoryCRUD()
    
    async def process_sync_events(
        self, 
        user_id: int, 
        cabinet_id: int,
        current_orders: List[Dict[str, Any]],
        previous_orders: List[Dict[str, Any]],
        current_reviews: List[Dict[str, Any]] = None,
        previous_reviews: List[Dict[str, Any]] = None,
        current_stocks: List[Dict[str, Any]] = None,
        previous_stocks: List[Dict[str, Any]] = None,
        bot_webhook_url: str = None
    ) -> Dict[str, Any]:
        """Обработка всех событий синхронизации и отправка уведомлений"""
        try:
            # Получаем настройки пользователя
            user_settings = self.settings_crud.get_user_settings(self.db, user_id)
            if not user_settings:
                user_settings = self.settings_crud.create_default_settings(self.db, user_id)
            
            # Проверяем, включены ли уведомления
            if not user_settings.notifications_enabled:
                logger.info(f"Notifications disabled for user {user_id}")
                return {"status": "disabled", "notifications_sent": 0}
            
            notifications_sent = 0
            events_processed = []
            
            # 1. Обрабатываем заказы (новые заказы + изменения статуса)
            order_events = await self._process_order_events(
                user_id, current_orders, previous_orders, user_settings
            )
            events_processed.extend(order_events)
            
            # 2. Обрабатываем отзывы (негативные отзывы)
            if current_reviews and previous_reviews:
                review_events = await self._process_review_events(
                    user_id, current_reviews, previous_reviews, user_settings
                )
                events_processed.extend(review_events)
            
            # 3. Обрабатываем остатки (критичные остатки)
            if current_stocks and previous_stocks:
                stock_events = await self._process_stock_events(
                    user_id, current_stocks, previous_stocks, user_settings
                )
                events_processed.extend(stock_events)
            
            # 4. Генерируем и отправляем уведомления
            if events_processed and bot_webhook_url:
                notifications_sent = await self._send_notifications(
                    user_id, events_processed, user_settings, bot_webhook_url
                )
            
            return {
                "status": "success",
                "events_processed": len(events_processed),
                "notifications_sent": notifications_sent,
                "events": events_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing sync events for user {user_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _process_order_events(
        self, 
        user_id: int, 
        current_orders: List[Dict[str, Any]], 
        previous_orders: List[Dict[str, Any]], 
        user_settings
    ) -> List[Dict[str, Any]]:
        """Обработка событий заказов"""
        events = []
        
        # Обнаруживаем новые заказы
        if user_settings.new_orders_enabled:
            new_order_events = self.event_detector.detect_new_orders(
                user_id, current_orders, previous_orders
            )
            events.extend(new_order_events)
        
        # Обнаруживаем изменения статуса заказов
        if (user_settings.order_buyouts_enabled or 
            user_settings.order_cancellations_enabled or 
            user_settings.order_returns_enabled):
            
            status_change_events = self.event_detector.detect_status_changes(
                user_id, current_orders, previous_orders
            )
            events.extend(status_change_events)
        
        return events
    
    async def _process_review_events(
        self, 
        user_id: int, 
        current_reviews: List[Dict[str, Any]], 
        previous_reviews: List[Dict[str, Any]], 
        user_settings
    ) -> List[Dict[str, Any]]:
        """Обработка событий отзывов"""
        events = []
        
        if user_settings.negative_reviews_enabled:
            negative_review_events = self.event_detector.detect_negative_reviews(
                user_id, current_reviews, previous_reviews
            )
            events.extend(negative_review_events)
        
        return events
    
    async def _process_stock_events(
        self, 
        user_id: int, 
        current_stocks: List[Dict[str, Any]], 
        previous_stocks: List[Dict[str, Any]], 
        user_settings
    ) -> List[Dict[str, Any]]:
        """Обработка событий остатков"""
        events = []
        
        if user_settings.critical_stocks_enabled:
            critical_stocks_events = self.event_detector.detect_critical_stocks(
                user_id, current_stocks, previous_stocks
            )
            events.extend(critical_stocks_events)
        
        return events
    
    async def _send_notifications(
        self, 
        user_id: int, 
        events: List[Dict[str, Any]], 
        user_settings, 
        bot_webhook_url: str
    ) -> int:
        """Отправка уведомлений"""
        notifications_sent = 0
        
        for event in events:
            try:
                # Генерируем уведомление
                notification = self.notification_generator.generate_notification(
                    event, self._settings_to_dict(user_settings)
                )
                
                if not notification:
                    continue
                
                # Форматируем сообщение для Telegram
                telegram_text = self._format_notification_for_telegram(notification)
                
                # Отправляем через webhook
                result = await self._send_webhook_notification(
                    user_id, notification, telegram_text, bot_webhook_url
                )
                
                if result.get("success"):
                    notifications_sent += 1
                    
                    # Записываем в историю
                    self._save_notification_to_history(user_id, notification, result)
                
            except Exception as e:
                logger.error(f"Error sending notification for event {event}: {e}")
        
        return notifications_sent
    
    def _format_notification_for_telegram(self, notification: Dict[str, Any]) -> str:
        """Форматирование уведомления для Telegram"""
        notification_type = notification.get("type")
        
        if notification_type == "new_order":
            return self.message_formatter.format_new_order_notification(notification)
        elif notification_type == "order_buyout":
            return self._format_order_buyout_for_telegram(notification)
        elif notification_type == "order_cancellation":
            return self._format_order_cancellation_for_telegram(notification)
        elif notification_type == "order_return":
            return self._format_order_return_for_telegram(notification)
        elif notification_type == "negative_review":
            return self._format_negative_review_for_telegram(notification)
        elif notification_type == "critical_stocks":
            return self.message_formatter.format_critical_stocks_notification(notification)
        
        return notification.get("content", "Уведомление")
    
    def _format_order_buyout_for_telegram(self, notification: Dict[str, Any]) -> str:
        """Форматирование уведомления о выкупе для Telegram"""
        order_id = notification.get("order_id", "N/A")
        amount = notification.get("amount", 0)
        product_name = notification.get("product_name", "Неизвестный товар")
        brand = notification.get("brand", "Неизвестный бренд")
        
        return f"""✅ ЗАКАЗ ВЫКУПЛЕН

🛒 Заказ #{order_id}
💰 Сумма: {amount:,} ₽
📦 Товар: {product_name}
🏷️ Бренд: {brand}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_order_cancellation_for_telegram(self, notification: Dict[str, Any]) -> str:
        """Форматирование уведомления об отмене для Telegram"""
        order_id = notification.get("order_id", "N/A")
        amount = notification.get("amount", 0)
        product_name = notification.get("product_name", "Неизвестный товар")
        brand = notification.get("brand", "Неизвестный бренд")
        
        return f"""❌ ЗАКАЗ ОТМЕНЕН

🛒 Заказ #{order_id}
💰 Сумма: {amount:,} ₽
📦 Товар: {product_name}
🏷️ Бренд: {brand}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_order_return_for_telegram(self, notification: Dict[str, Any]) -> str:
        """Форматирование уведомления о возврате для Telegram"""
        order_id = notification.get("order_id", "N/A")
        amount = notification.get("amount", 0)
        product_name = notification.get("product_name", "Неизвестный товар")
        brand = notification.get("brand", "Неизвестный бренд")
        
        return f"""🔄 ЗАКАЗ ВОЗВРАЩЕН

🛒 Заказ #{order_id}
💰 Сумма: {amount:,} ₽
📦 Товар: {product_name}
🏷️ Бренд: {brand}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_negative_review_for_telegram(self, notification: Dict[str, Any]) -> str:
        """Форматирование уведомления о негативном отзыве для Telegram"""
        review_id = notification.get("review_id", "N/A")
        rating = notification.get("rating", 0)
        text = notification.get("text", "")
        product_name = notification.get("product_name", "Неизвестный товар")
        order_id = notification.get("order_id")
        
        order_info = f"Заказ: #{order_id}" if order_id else "Заказ: неизвестен"
        
        return f"""😞 НЕГАТИВНЫЙ ОТЗЫВ

⭐ Оценка: {rating}/5
📝 Текст: {text}
📦 Товар: {product_name}
🛒 {order_info}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    async def _send_webhook_notification(
        self, 
        user_id: int, 
        notification: Dict[str, Any], 
        telegram_text: str, 
        bot_webhook_url: str
    ) -> Dict[str, Any]:
        """Отправка webhook уведомления"""
        notification_type = notification.get("type")
        
        # Используем существующий WebhookSender
        if notification_type == "new_order":
            return await self.webhook_sender.send_new_order_notification(
                user_id, notification, bot_webhook_url
            )
        elif notification_type == "critical_stocks":
            return await self.webhook_sender.send_critical_stocks_notification(
                user_id, notification, bot_webhook_url
            )
        else:
            # Для новых типов уведомлений используем общий метод
            return await self._send_generic_webhook_notification(
                user_id, notification, telegram_text, bot_webhook_url
            )
    
    async def _send_generic_webhook_notification(
        self, 
        user_id: int, 
        notification: Dict[str, Any], 
        telegram_text: str, 
        bot_webhook_url: str
    ) -> Dict[str, Any]:
        """Отправка общих webhook уведомлений"""
        payload = {
            "type": notification.get("type"),
            "user_id": user_id,
            "data": notification,
            "telegram_text": telegram_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return await self.webhook_sender._send_notification(payload, bot_webhook_url)
    
    def _save_notification_to_history(
        self, 
        user_id: int, 
        notification: Dict[str, Any], 
        result: Dict[str, Any]
    ):
        """Сохранение уведомления в историю"""
        try:
            notification_data = {
                "id": f"notif_{notification['type']}_{notification.get('order_id', notification.get('review_id', notification.get('nm_id', 'unknown')))}",
                "user_id": user_id,
                "notification_type": notification["type"],
                "priority": notification.get("priority", "MEDIUM"),
                "title": notification.get("title", ""),
                "content": notification.get("content", ""),
                "sent_at": datetime.now(timezone.utc),
                "status": "delivered" if result.get("success") else "failed"
            }
            
            self.history_crud.create_notification(self.db, notification_data)
            
        except Exception as e:
            logger.error(f"Error saving notification to history: {e}")
    
    def _settings_to_dict(self, user_settings) -> Dict[str, Any]:
        """Преобразование настроек в словарь"""
        return {
            "notifications_enabled": user_settings.notifications_enabled,
            "new_orders_enabled": user_settings.new_orders_enabled,
            "order_buyouts_enabled": user_settings.order_buyouts_enabled,
            "order_cancellations_enabled": user_settings.order_cancellations_enabled,
            "order_returns_enabled": user_settings.order_returns_enabled,
            "negative_reviews_enabled": user_settings.negative_reviews_enabled,
            "critical_stocks_enabled": user_settings.critical_stocks_enabled,
            "grouping_enabled": user_settings.grouping_enabled,
            "max_group_size": user_settings.max_group_size,
            "group_timeout": user_settings.group_timeout
        }
    
    async def send_test_notification(
        self, 
        user_id: int, 
        notification_type: str, 
        test_data: Dict[str, Any],
        bot_webhook_url: str
    ) -> Dict[str, Any]:
        """
        Отправка тестового уведомления
        
        Args:
            user_id: ID пользователя
            notification_type: Тип уведомления
            test_data: Тестовые данные
            bot_webhook_url: URL webhook бота
            
        Returns:
            Результат отправки уведомления
        """
        try:
            # Создаем тестовое уведомление
            test_notification = self._create_test_notification(
                notification_type, 
                test_data
            )
            
            # Форматируем для Telegram
            formatted_message = self._format_notification_for_telegram(test_notification)
            
            # Отправляем через webhook
            result = await self._send_webhook_notification(
                user_id=user_id,
                notification=test_notification,
                telegram_text=formatted_message,
                bot_webhook_url=bot_webhook_url
            )
            
            return {
                "success": result.get("success", False),
                "message": "Test notification sent successfully" if result.get("success") else "Failed to send test notification",
                "notification_sent": result.get("success", False),
                "error": result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            return {
                "success": False,
                "message": f"Error sending test notification: {str(e)}",
                "notification_sent": False,
                "error": str(e)
            }
    
    def _create_test_notification(self, notification_type: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание тестового уведомления"""
        if notification_type == "new_order":
            return {
                "type": "new_order",
                "order_id": test_data.get("order_id", "TEST_12345"),
                "amount": test_data.get("amount", 1500),
                "product_name": test_data.get("product_name", "Тестовый товар"),
                "brand": test_data.get("brand", "Тестовый бренд"),
                "content": "Тестовое уведомление о новом заказе"
            }
        elif notification_type == "order_buyout":
            return {
                "type": "order_buyout",
                "order_id": test_data.get("order_id", "TEST_12345"),
                "amount": test_data.get("amount", 1500),
                "product_name": test_data.get("product_name", "Тестовый товар"),
                "brand": test_data.get("brand", "Тестовый бренд"),
                "content": "Тестовое уведомление о выкупе заказа"
            }
        elif notification_type == "order_cancellation":
            return {
                "type": "order_cancellation",
                "order_id": test_data.get("order_id", "TEST_12345"),
                "amount": test_data.get("amount", 1500),
                "product_name": test_data.get("product_name", "Тестовый товар"),
                "brand": test_data.get("brand", "Тестовый бренд"),
                "content": "Тестовое уведомление об отмене заказа"
            }
        elif notification_type == "order_return":
            return {
                "type": "order_return",
                "order_id": test_data.get("order_id", "TEST_12345"),
                "amount": test_data.get("amount", 1500),
                "product_name": test_data.get("product_name", "Тестовый товар"),
                "brand": test_data.get("brand", "Тестовый бренд"),
                "content": "Тестовое уведомление о возврате заказа"
            }
        elif notification_type == "negative_review":
            return {
                "type": "negative_review",
                "review_id": test_data.get("review_id", "TEST_REVIEW_123"),
                "rating": test_data.get("rating", 2),
                "product_name": test_data.get("product_name", "Тестовый товар"),
                "comment": test_data.get("comment", "Тестовый комментарий"),
                "content": "Тестовое уведомление о негативном отзыве"
            }
        elif notification_type == "critical_stocks":
            products = test_data.get("products", [
                {"nm_id": "TEST_12345", "name": "Тестовый товар 1", "stock": 2},
                {"nm_id": "TEST_67890", "name": "Тестовый товар 2", "stock": 1}
            ])
            return {
                "type": "critical_stocks",
                "products": products,
                "content": "Тестовое уведомление о критичных остатках"
            }
        else:
            return {
                "type": notification_type,
                "content": f"Тестовое уведомление типа {notification_type}"
            }
