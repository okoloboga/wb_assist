"""
Notification Service - единый сервис для всех типов уведомлений S3
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from contextlib import asynccontextmanager

# Удалены неиспользуемые компоненты для упрощения
from .crud import (
    NotificationSettingsCRUD,
    NotificationHistoryCRUD,
    OrderStatusHistoryCRUD
)
from app.features.bot_api.formatter import BotMessageFormatter
from app.utils.timezone import TimezoneUtils
from app.features.wb_api.models import WBOrder, WBCabinet, WBReview, WBProduct, WBStock
from app.features.notifications.models import NotificationHistory
from .webhook_sender import WebhookSender

logger = logging.getLogger(__name__)


class NotificationService:
    """Единый сервис для управления всеми уведомлениями"""
    
    def __init__(self, db: Session):
        self.db = db
        self._sync_locks = {}  # {cabinet_id: asyncio.Lock} - блокировки синхронизации
        
        # Инициализируем только используемые компоненты
        self.message_formatter = BotMessageFormatter()
        
        # Инициализируем CRUD
        self.settings_crud = NotificationSettingsCRUD()
        self.history_crud = NotificationHistoryCRUD()
        self.order_crud = OrderStatusHistoryCRUD()
        
        # Инициализируем WebhookSender
        self.webhook_sender = WebhookSender()
        
        # Инициализируем EventDetector
        from .event_detector import EventDetector
        self.event_detector = EventDetector()
    
    @asynccontextmanager
    async def _get_sync_lock(self, cabinet_id: int):
        """Получить блокировку для синхронизации кабинета"""
        if cabinet_id not in self._sync_locks:
            self._sync_locks[cabinet_id] = asyncio.Lock()
        
        async with self._sync_locks[cabinet_id]:
            yield
    
    def _is_sync_in_progress(self, cabinet_id: int) -> bool:
        """Проверить, идет ли синхронизация кабинета"""
        try:
            if cabinet_id in self._sync_locks:
                return self._sync_locks[cabinet_id].locked()
            return False
        except Exception as e:
            logger.warning(f"Error checking sync status for cabinet {cabinet_id}: {e}")
            return False
    
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
            
            # 4. Отправляем уведомления через webhook
            for event in events_processed:
                try:
                    # Очищаем datetime объекты для JSON сериализации
                    clean_event = self._clean_datetime_objects(event)
                    
                    # Формируем текст уведомления
                    telegram_text = self._format_notification_for_telegram(clean_event)
                    
                    # Отправляем webhook уведомление
                    webhook_result = await self._send_webhook_notification(
                        user_id=user_id,
                        notification=clean_event,
                        telegram_text=telegram_text,
                        bot_webhook_url=""  # Будет получен из пользователя
                    )
                    
                    if webhook_result.get("success"):
                        notifications_sent += 1
                        logger.info(f"📢 Notification sent for user {user_id}: {event.get('type')}")
                        
                        # КРИТИЧНО: Сохраняем уведомление в историю для защиты от дублирования
                        self._save_notification_to_history(user_id, clean_event, webhook_result)
                    else:
                        logger.warning(f"❌ Failed to send notification for user {user_id}: {webhook_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"❌ Error sending notification for user {user_id}: {e}")
            
            return {
                "status": "success",
                "events_processed": len(events_processed),
                "notifications_sent": notifications_sent,
                "events": events_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing sync events for user {user_id}: {e}")
            # Отправляем уведомление об ошибке пользователю
            await self._send_error_notification(user_id, "sync_processing_error", str(e))
            return {"status": "error", "error": str(e)}
    
    def _clean_datetime_objects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Очистка datetime объектов для JSON сериализации"""
        import datetime
        
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, datetime.datetime):
                    # Конвертируем datetime в ISO строку
                    cleaned[key] = value.isoformat()
                elif isinstance(value, dict):
                    cleaned[key] = self._clean_datetime_objects(value)
                elif isinstance(value, list):
                    cleaned[key] = [self._clean_datetime_objects(item) if isinstance(item, dict) else item for item in value]
                else:
                    cleaned[key] = value
            return cleaned
        return data
    
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
            # Получаем ID предыдущих отзывов
            previous_review_ids = {review["review_id"] for review in previous_reviews}
            
            # Находим новые негативные отзывы (0-3 звезды)
            for review in current_reviews:
                if (review["review_id"] not in previous_review_ids and 
                    review.get("rating", 0) <= 3):
                    
                    event = {
                        "type": "negative_review",
                        "user_id": user_id,
                        "review_id": review["review_id"],
                        "rating": review.get("rating", 0),
                        "text": review.get("text", ""),
                        "product_name": f"Товар {review.get('nm_id', 'N/A')}",
                        "nm_id": review.get("nm_id"),
                        "user_name": review.get("user_name", ""),
                        "created_date": review.get("created_date"),
                        "detected_at": TimezoneUtils.now_msk()
                    }
                    events.append(event)
        
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
    
    # _send_notifications удален - используется webhook система
    
    def _format_notification_for_telegram(self, notification: Dict[str, Any]) -> str:
        """Универсальное форматирование уведомления для Telegram"""
        notification_type = notification.get("type")
        
        # Для всех типов заказов используем детальный формат
        if notification_type in ["new_order", "order_buyout", "order_cancellation", "order_return"]:
            return self.message_formatter.format_order_detail({"order": notification})
        elif notification_type == "critical_stocks":
            return self.message_formatter.format_critical_stocks_notification(notification)
        elif notification_type == "negative_review":
            return self._format_negative_review_notification(notification)
        else:
            # Универсальное форматирование для остальных типов
            return self._format_universal_notification(notification)
    
    def _format_negative_review_notification(self, notification: Dict[str, Any]) -> str:
        """Форматирование уведомления о негативном отзыве"""
        try:
            rating = notification.get("rating", 0)
            text = notification.get("text", "")
            product_name = notification.get("product_name", "Неизвестный товар")
            nm_id = notification.get("nm_id", "N/A")
            user_name = notification.get("user_name", "Аноним")
            
            message_text = (
                f"😞 **НЕГАТИВНЫЙ ОТЗЫВ**\n\n"
                f"⭐ Оценка: {rating}/5\n"
                f"📝 Текст: {text[:200]}{'...' if len(text) > 200 else ''}\n"
                f"📦 Товар: {product_name}\n"
                f"🆔 ID: {nm_id}\n"
                f"👤 От: {user_name}\n\n"
                f"💡 Рекомендуется ответить на отзыв"
            )
            
            return message_text
            
        except Exception as e:
            logger.error(f"Error formatting negative review notification: {e}")
            return "❌ Ошибка форматирования уведомления об отзыве"
    
    def _format_universal_notification(self, notification: Dict[str, Any]) -> str:
        """Универсальное форматирование уведомления в детальном формате"""
        notification_type = notification.get("type")
        
        # Специальная обработка для отзывов (оставляем как есть)
        if notification_type == "negative_review":
            rating = notification.get("rating", 0)
            text = notification.get("text", "")
            product_name = notification.get("product_name", "Неизвестный товар")
            order_id = notification.get("order_id", "N/A")
            order_info = f"Заказ: #{order_id}" if order_id != "N/A" else "Заказ: неизвестен"
            time_str = TimezoneUtils.format_time_only(TimezoneUtils.now_msk())
        
            return f"""😞 НЕГАТИВНЫЙ ОТЗЫВ

⭐ Оценка: {rating}/5
📝 Текст: {text}
📦 Товар: {product_name}
🛒 {order_info}

Время: {time_str}"""
        
        # Для всех типов заказов используем детальный формат
        return self._format_detailed_order_notification(notification)
    
    def _format_detailed_order_notification(self, notification: Dict[str, Any]) -> str:
        """Детальное форматирование уведомления о заказе (как в меню)"""
        notification_type = notification.get("type")
        
        # Определяем статус для заголовка
        status_map = {
            "new_order": "НОВЫЙ ЗАКАЗ",
            "order_buyout": "ЗАКАЗ ВЫКУПЛЕН", 
            "order_cancellation": "ЗАКАЗ ОТМЕНЕН",
            "order_return": "ЗАКАЗ ВОЗВРАЩЕН"
        }
        
        status = status_map.get(notification_type, "ЗАКАЗ")
        
        # Основная информация
        order_id = notification.get("order_id", notification.get("id", "N/A"))
        order_date = self._format_datetime(notification.get("date", notification.get("order_date", "")))
        brand = notification.get("brand", "Неизвестно")
        product_name = notification.get("product_name", notification.get("name", "Неизвестно"))
        nm_id = notification.get("nm_id", "N/A")
        supplier_article = notification.get("supplier_article", notification.get("article", ""))
        size = notification.get("size", "")
        barcode = notification.get("barcode", "")
        warehouse_from = notification.get("warehouse_from", "")
        warehouse_to = notification.get("warehouse_to", "")
        
        # Финансовая информация
        order_amount = notification.get("amount", notification.get("total_price", 0))
        spp_percent = notification.get("spp_percent", 0)
        customer_price = notification.get("customer_price", 0)
        # Логистика исключена из системы
        dimensions = notification.get("dimensions", "")
        volume_liters = notification.get("volume_liters", 0)
        warehouse_rate_per_liter = notification.get("warehouse_rate_per_liter", 0)
        warehouse_rate_extra = notification.get("warehouse_rate_extra", 0)
        
        # Рейтинги и отзывы
        rating = notification.get("rating", 0)
        reviews_count = notification.get("reviews_count", 0)
        
        # Статистика
        sales_periods = notification.get("sales_periods", {})
        
        # Остатки
        stocks = notification.get("stocks", {})
        stock_days = notification.get("stock_days", {})
        
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
        # Логистика исключена из системы
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
        
        return message
    
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
    
    # Дублирующиеся методы форматирования удалены - используется универсальный _format_universal_notification
    
    async def _send_error_notification(self, user_id: int, error_type: str, error_message: str):
        """Отправка уведомления об ошибке пользователю"""
        try:
            # Создаем событие ошибки
            error_event = {
                "type": "system_error",
                "user_id": user_id,
                "data": {
                    "type": error_type,
                    "message": error_message,
                    "timestamp": TimezoneUtils.now_msk().isoformat()
                },
                "priority": "HIGH"
            }
            
            # Сохраняем в историю уведомлений
            self.history_crud.create_notification(self.db, {
                "user_id": user_id,
                "notification_type": "system_error",
                "priority": "HIGH",
                "title": "Ошибка системы",
                "content": error_message,
                "sent_at": TimezoneUtils.now_msk(),
                "status": "pending"
            })
            
            logger.error(f"📢 Error notification sent to user {user_id}: {error_type} - {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    
    async def get_new_events(
        self, 
        user_id: int, 
        last_check: datetime
    ) -> List[Dict[str, Any]]:
        """Получение новых событий для пользователя с момента last_check"""
        try:
            events = []
            
            # Получаем кабинеты пользователя
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            cabinet_ids = cabinet_user_crud.get_user_cabinets(self.db, user_id)
            
            if not cabinet_ids:
                return events
            
            # Проверяем, не идет ли синхронизация для кабинетов пользователя
            sync_in_progress = False
            for cabinet_id in cabinet_ids:
                if self._is_sync_in_progress(cabinet_id):
                    logger.info(f"🔄 Синхронизация кабинета {cabinet_id} в процессе, пропускаем webhook для пользователя {user_id}")
                    sync_in_progress = True
                    break
            
            if sync_in_progress:
                return []  # Возвращаем пустой список, чтобы не мешать синхронизации
            
            # Получаем новые заказы
            new_orders = await self._get_new_orders(user_id, cabinet_ids, last_check)
            events.extend(new_orders)
            
            # Получаем новые негативные отзывы (0-3 звезды)
            new_reviews = await self._get_new_reviews(user_id, cabinet_ids, last_check)
            events.extend(new_reviews)
            
            # Получаем критические остатки
            critical_stocks = await self._get_critical_stocks(user_id, cabinet_ids, last_check)
            events.extend(critical_stocks)
            
            # Получаем изменения статусов заказов
            status_changes = await self._get_status_changes(user_id, cabinet_ids, last_check)
            events.extend(status_changes)
            
            # Получаем события завершения синхронизации
            sync_completed_events = await self._get_sync_completed_events(user_id, cabinet_ids, last_check)
            events.extend(sync_completed_events)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting new events for user {user_id}: {e}")
            return []
    
    async def _get_sync_completed_events(
        self, 
        user_id: int, 
        cabinet_ids: List[int], 
        last_check: datetime
    ) -> List[Dict[str, Any]]:
        """Получение событий завершения синхронизации"""
        try:
            events = []
            
            # Ищем события sync_completed в NotificationHistory для конкретного пользователя
            from app.features.notifications.models import NotificationHistory
            
            # Для sync_completed событий ищем за последние 24 часа, 
            # так как они создаются только при завершении синхронизации
            from datetime import timedelta
            sync_search_start = TimezoneUtils.now_msk() - timedelta(hours=24)
            
            sync_events = self.db.query(NotificationHistory).filter(
                NotificationHistory.notification_type == "sync_completed",
                NotificationHistory.user_id == user_id,
                NotificationHistory.created_at > sync_search_start
            ).all()
            
            logger.info(f"🔍 Found {len(sync_events)} sync_completed events for user {user_id}")
            
            for event in sync_events:
                try:
                    # Парсим content для получения cabinet_id
                    import json
                    content_data = json.loads(event.content) if event.content else {}
                    cabinet_id = content_data.get('cabinet_id')
                    
                    # Парсим content для получения is_first_sync
                    content_data = json.loads(event.content) if event.content else {}
                    is_first_sync = content_data.get('is_first_sync', False)
                    
                    events.append({
                        "type": "sync_completed",
                        "user_id": user_id,
                        "created_at": event.created_at.isoformat(),
                        "data": {
                            "cabinet_id": cabinet_id,
                            "message": "Синхронизация завершена успешно",
                            "timestamp": event.created_at.isoformat(),
                            "is_first_sync": is_first_sync
                        }
                    })
                    logger.info(f"📡 Found sync_completed event for cabinet {cabinet_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing sync_completed event {event.id}: {e}")
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting sync completed events: {e}")
            return []
    
    async def _get_new_orders(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение новых заказов с защитой от дублирования"""
        try:
            from sqlalchemy import desc, and_

            # Защита от первой синхронизации
            cabinets = self.db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
            if not cabinets:
                return []
            
            for cabinet in cabinets:
                if not cabinet.last_sync_at:
                    logger.info(f"Skipping order notifications for cabinet {cabinet.id} - first sync")
                    return []

            # Получаем уже отправленные уведомления за последние 24 часа
            sent_notifications = self.db.query(NotificationHistory).filter(
                and_(
                    NotificationHistory.user_id == user_id,
                    NotificationHistory.notification_type == "new_order",
                    NotificationHistory.sent_at > last_check - timedelta(hours=24)
                )
            ).all()
            
            # Извлекаем order_id из content (JSON строка)
            sent_order_ids = set()
            for n in sent_notifications:
                try:
                    import json
                    content_data = json.loads(n.content)
                    if "order_id" in content_data:
                        sent_order_ids.add(content_data["order_id"])
                except (json.JSONDecodeError, KeyError):
                    continue

            # Получаем новые заказы по created_at (время добавления в БД)
            # КРИТИЧНО: Используем created_at вместо order_date, чтобы ловить именно НОВЫЕ записи в БД
            orders = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id.in_(cabinet_ids),
                    WBOrder.created_at > last_check,  # Используем created_at - время добавления в БД
                    ~WBOrder.order_id.in_(sent_order_ids)  # Исключаем уже отправленные
                )
            ).all()
            
            events = []
            for order in orders:
                # Обогащаем данные заказа для форматтера
                product = self.db.query(WBProduct).filter(WBProduct.nm_id == order.nm_id).first()
                rating = (product.rating or 0.0) if product else 0.0
                reviews_cnt = (product.reviews_count or 0) if product else 0
                image_url = product.image_url if product and getattr(product, "image_url", None) else None
                
                # Логируем информацию об изображении для отладки
                if image_url:
                    logger.info(f"🖼️ Found image for order {order.order_id}: {image_url}")
                else:
                    logger.warning(f"⚠️ No image found for order {order.order_id}, product: {product}")
                # Быстрый точный расчёт из WBReview (перебивает продуктовый рейтинг, если есть отзывы)
                try:
                    avg_cnt = self.db.query(func.avg(WBReview.rating), func.count(WBReview.id)).filter(
                        WBReview.cabinet_id == order.cabinet_id,
                        WBReview.nm_id == order.nm_id,
                        WBReview.rating.isnot(None)
                    ).one()
                    avg_rating = avg_cnt[0] or 0.0
                    cnt_reviews = avg_cnt[1] or 0
                    if cnt_reviews > 0:
                        rating = round(float(avg_rating), 1)
                        reviews_cnt = int(cnt_reviews)
                except Exception:
                    pass
                order_data = {
                    "id": order.id,
                    "order_id": order.order_id,
                    "date": order.order_date.isoformat() if order.order_date else None,
                    "order_date": order.order_date.isoformat() if order.order_date else None,
                    "amount": order.total_price or 0,
                    "total_price": order.total_price or 0,
                    "product_name": order.name or "Неизвестно",
                    "name": order.name or "Неизвестно",
                    "brand": order.brand or "Неизвестно",
                    "nm_id": order.nm_id,
                    "article": order.article or "",
                    "supplier_article": order.article or "",
                    "size": order.size or "",
                    "barcode": order.barcode or "",
                    "warehouse_from": order.warehouse_from or "",
                    "warehouse_to": order.warehouse_to or "",
                    "spp_percent": order.spp_percent or 0.0,
                    "customer_price": order.customer_price or 0.0,
                    # Логистика исключена из системы
                    "dimensions": getattr(order, 'dimensions', ''),
                    "volume_liters": getattr(order, 'volume_liters', 0),
                    "warehouse_rate_per_liter": getattr(order, 'warehouse_rate_per_liter', 0),
                    "warehouse_rate_extra": getattr(order, 'warehouse_rate_extra', 0),
                    "rating": rating,
                    "reviews_count": reviews_cnt,
                    "sales_periods": {},
                    "stocks": {},
                    "stock_days": {},
                    "status": order.status,
                    "image_url": image_url,
                }
                telegram_text = self.message_formatter.format_order_detail({"order": order_data})

                events.append({
                    "type": "new_order",
                    "user_id": user_id,
                    "data": order_data,
                    "telegram_text": telegram_text,
                    "created_at": order.created_at or TimezoneUtils.now_msk(),
                    "priority": "MEDIUM"
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting new orders: {e}")
            return []
    
    async def _get_new_reviews(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение новых негативных отзывов (0-3 звезды) с защитой от дублирования"""
        try:
            
            # Проверяем, что это не первая синхронизация кабинета
            # Если last_sync_at не установлен или очень старый, пропускаем уведомления
            cabinets = self.db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
            for cabinet in cabinets:
                if not cabinet.last_sync_at:
                    logger.info(f"Skipping review notifications for cabinet {cabinet.id} - first sync")
                    return []
                
                # Проверяем, была ли синхронизация в последние 24 часа
                from datetime import timedelta
                time_diff = TimezoneUtils.now_msk() - cabinet.last_sync_at
                if time_diff > timedelta(hours=24):
                    logger.info(f"Skipping review notifications for cabinet {cabinet.id} - long break since last sync")
                    return []
            
            # Получаем уже отправленные уведомления о негативных отзывах за последние 24 часа
            from sqlalchemy import and_
            sent_notifications = self.db.query(NotificationHistory).filter(
                and_(
                    NotificationHistory.user_id == user_id,
                    NotificationHistory.notification_type == 'negative_review',
                    NotificationHistory.sent_at > last_check - timedelta(hours=24)
                )
            ).all()
            
            # Извлекаем review_id из content (JSON строка)
            sent_review_ids = set()
            for n in sent_notifications:
                try:
                    import json
                    content_data = json.loads(n.content)
                    if "review_id" in content_data:
                        sent_review_ids.add(content_data["review_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
            
            reviews = self.db.query(WBReview).filter(
                and_(
                    WBReview.cabinet_id.in_(cabinet_ids),
                    WBReview.created_date > last_check,  # Используем время создания отзыва, а не обновления
                    ~WBReview.review_id.in_(sent_review_ids)  # Исключаем уже отправленные
                )
            ).all()
            
            events = []
            for review in reviews:
                # Создаем события ТОЛЬКО для негативных отзывов (0-3 звезды)
                if review.rating and review.rating <= 3:
                    events.append({
                        "type": "negative_review",
                        "user_id": user_id,
                        "data": {
                            "review_id": review.review_id,
                            "rating": review.rating,
                            "text": review.text,
                            "product_name": f"Товар {review.nm_id}",  # Можно улучшить, получив название товара
                            "user_name": review.user_name,
                            "created_at": review.created_date.isoformat() if review.created_date else None
                        },
                        "created_at": review.created_date or TimezoneUtils.now_msk(),
                        "priority": "HIGH"
                    })
                # Положительные отзывы (4-5 звезд) игнорируем - уведомления не нужны
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting new reviews: {e}")
            return []
    
    async def _get_critical_stocks(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение критических остатков с защитой от межскладских переводов и дублирования"""
        try:
            from sqlalchemy import and_
            from datetime import timedelta
            
            # Проверяем, что это не первая синхронизация кабинета
            cabinets = self.db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
            for cabinet in cabinets:
                if not cabinet.last_sync_at:
                    logger.info(f"Skipping critical stocks notifications for cabinet {cabinet.id} - first sync")
                    return []
            
            # Получаем уже отправленные уведомления о критических остатках за последние 24 часа
            sent_notifications = self.db.query(NotificationHistory).filter(
                and_(
                    NotificationHistory.user_id == user_id,
                    NotificationHistory.notification_type == 'critical_stocks',
                    NotificationHistory.sent_at > last_check - timedelta(hours=24)
                )
            ).all()
            
            # Извлекаем nm_id из content (JSON строка)
            sent_nm_ids = set()
            for n in sent_notifications:
                try:
                    import json
                    content_data = json.loads(n.content)
                    if "nm_id" in content_data:
                        sent_nm_ids.add(content_data["nm_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
            
            critical_threshold = 2
            
            # Получаем предыдущее состояние остатков (до last_check)
            previous_stocks = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id.in_(cabinet_ids),
                    WBStock.updated_at <= last_check
                )
            ).all()
            
            # Получаем текущее состояние остатков (после last_check)
            current_stocks = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id.in_(cabinet_ids),
                    WBStock.updated_at > last_check
                )
            ).all()
            
            if not current_stocks:
                return []
            
            # Группируем остатки по товарам и размерам
            def group_stocks_by_product(stocks):
                grouped = {}
                for stock in stocks:
                    key = (stock.nm_id, stock.size or "")
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(stock)
                return grouped
            
            prev_grouped = group_stocks_by_product(previous_stocks)
            curr_grouped = group_stocks_by_product(current_stocks)
            
            # Находим товары с реальным уменьшением остатков
            critical_events = []
            for (nm_id, size), current_stock_list in curr_grouped.items():
                # Суммируем остатки по всем складам для текущего состояния
                current_total = sum(stock.quantity or 0 for stock in current_stock_list)
                
                # Получаем предыдущее состояние
                prev_stock_list = prev_grouped.get((nm_id, size), [])
                previous_total = sum(stock.quantity or 0 for stock in prev_stock_list)
                
                # Проверяем реальное уменьшение остатков и исключаем уже отправленные
                if (previous_total > critical_threshold and 
                    current_total <= critical_threshold and 
                    current_total < previous_total and
                    nm_id not in sent_nm_ids):  # Исключаем уже отправленные
                    
                    # Получаем информацию о товаре
                    product = self.db.query(WBProduct).filter(
                        WBProduct.nm_id == nm_id
                    ).first()
                    
                    critical_events.append({
                    "type": "critical_stocks",
                    "user_id": user_id,
                        "created_at": TimezoneUtils.now_msk(),
                    "data": {
                        "nm_id": nm_id,
                            "name": product.name if product else f"Товар {nm_id}",
                            "brand": product.brand if product else "",
                            "size": size,
                            "previous_quantity": previous_total,
                            "current_quantity": current_total,
                            "decreased_by": previous_total - current_total,
                            "detected_at": TimezoneUtils.now_msk()
                        }
                    })
            
            return critical_events
            
        except Exception as e:
            logger.error(f"Error getting critical stocks: {e}")
            return []
    
    async def _get_status_changes(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение изменений статусов заказов с защитой от дублирования"""
        try:
            from sqlalchemy import and_
            from datetime import timedelta
            
            # Получаем уже отправленные уведомления об изменениях статусов за последние 24 часа
            sent_notifications = self.db.query(NotificationHistory).filter(
                and_(
                    NotificationHistory.user_id == user_id,
                    NotificationHistory.notification_type.in_(['order_buyout', 'order_cancellation', 'order_return']),
                    NotificationHistory.sent_at > last_check - timedelta(hours=24)
                )
            ).all()
            
            # Извлекаем order_id из content (JSON строка)
            sent_order_ids = set()
            for n in sent_notifications:
                try:
                    import json
                    content_data = json.loads(n.content)
                    if "order_id" in content_data:
                        sent_order_ids.add(content_data["order_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # Получаем заказы с изменениями статуса
            orders = self.db.query(WBOrder).filter(
                WBOrder.cabinet_id.in_(cabinet_ids),
                WBOrder.updated_at > last_check,
                WBOrder.status.in_(['buyout', 'canceled', 'return']),
                ~WBOrder.order_id.in_(sent_order_ids)  # Исключаем уже отправленные
            ).all()
            
            events = []
            for order in orders:
                if order.status == 'buyout':
                    event_type = "order_buyout"
                    priority = "MEDIUM"
                elif order.status == 'canceled':
                    event_type = "order_cancellation"
                    priority = "HIGH"
                elif order.status == 'return':
                    event_type = "order_return"
                    priority = "HIGH"
                else:
                    continue
                
                # Получаем image_url из связанного товара
                image_url = None
                try:
                    product = self.db.query(WBProduct).filter(
                        and_(
                            WBProduct.cabinet_id == order.cabinet_id,
                            WBProduct.nm_id == order.nm_id
                        )
                    ).first()
                    if product:
                        image_url = product.image_url
                except Exception as e:
                    logger.error(f"Error getting image_url for order {order.order_id}: {e}")
                
                events.append({
                    "type": event_type,
                    "user_id": user_id,
                    "data": {
                        "order_id": order.order_id,
                        "id": order.order_id,  # Для совместимости с format_order_detail
                        "date": order.order_date.isoformat() if order.order_date else None,
                        "amount": order.total_price,
                        "product_name": order.name,
                        "brand": order.brand,
                        "nm_id": order.nm_id,
                        "article": order.article or "",
                        "supplier_article": order.article or "",
                        "size": order.size or "",
                        "barcode": order.barcode or "",
                        "warehouse_from": order.warehouse_from or "",
                        "warehouse_to": order.warehouse_to or "",
                        "spp_percent": order.spp_percent or 0.0,
                        "customer_price": order.customer_price or 0.0,
                        # Логистика исключена из системы
                        "image_url": image_url,  # Добавляем image_url
                        "status": order.status,
                        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                        "rating": 0,  # Получать из товара
                        "reviews_count": 0,  # Получать из товара
                        "sales_periods": {},  # Получать из статистики
                        "stocks": {},  # Получать из остатков
                        "stock_days": {}  # Получать из остатков
                    },
                    "created_at": order.updated_at or TimezoneUtils.now_msk(),
                    "priority": priority
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting status changes: {e}")
            return []

    def _save_notification_to_history(
        self, 
        user_id: int, 
        notification: Dict[str, Any], 
        result: Dict[str, Any]
    ):
        """Сохранение уведомления в историю для защиты от дублирования"""
        try:
            import json
            import uuid
            from datetime import datetime
            
            # Генерируем уникальный ID на основе типа и связанных данных
            notification_type = notification.get("type")
            
            # Определяем уникальный ключ в зависимости от типа
            if notification_type in ["new_order", "order_buyout", "order_cancellation", "order_return"]:
                unique_key = notification.get("order_id", notification.get("data", {}).get("order_id", "unknown"))
            elif notification_type == "negative_review":
                unique_key = notification.get("review_id", notification.get("data", {}).get("review_id", "unknown"))
            elif notification_type == "critical_stocks":
                unique_key = notification.get("nm_id", notification.get("data", {}).get("nm_id", "unknown"))
            else:
                unique_key = uuid.uuid4().hex[:8]
            
            # Добавляем timestamp для уникальности ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            notification_id = f"notif_{notification_type}_{unique_key}_{timestamp}"
            
            # Проверяем, существует ли уже такое уведомление
            existing = self.db.query(NotificationHistory).filter(
                NotificationHistory.id == notification_id
            ).first()
            
            if existing:
                logger.warning(f"⚠️ Notification {notification_id} already exists, skipping")
                return
            
            # Сохраняем данные в JSON формате для дальнейшей проверки дубликатов
            content_data = {
                "order_id": notification.get("order_id", notification.get("data", {}).get("order_id")),
                "review_id": notification.get("review_id", notification.get("data", {}).get("review_id")),
                "nm_id": notification.get("nm_id", notification.get("data", {}).get("nm_id")),
                "type": notification_type,
                "timestamp": TimezoneUtils.now_msk().isoformat()
            }
            
            notification_data = {
                "id": notification_id,
                "user_id": user_id,
                "notification_type": notification_type,
                "priority": notification.get("priority", "MEDIUM"),
                "title": f"Notification: {notification_type}",
                "content": json.dumps(content_data),  # Сохраняем как JSON
                "sent_at": TimezoneUtils.to_utc(TimezoneUtils.now_msk()),
                "status": "delivered" if result.get("success") else "failed"
            }
            
            self.history_crud.create_notification(self.db, notification_data)
            logger.info(f"💾 Saved notification to history: {notification_id}")
            
        except Exception as e:
            logger.error(f"Error saving notification to history: {e}")
            # Откатываем транзакцию при ошибке
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
    
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
        elif notification_type == "order_buyout":
            return {
                "type": "order_buyout",
                "order_id": test_data.get("order_id", "TEST_ORDER"),
                "product_name": test_data.get("product_name", "Тестовый товар"),
                "amount": test_data.get("amount", 1000),
                "content": "Тестовое уведомление о выкупе заказа"
            }
        elif notification_type == "order_return":
            return {
                "type": "order_return",
                "order_id": test_data.get("order_id", "TEST_ORDER"),
                "product_name": test_data.get("product_name", "Тестовый товар"),
                "amount": test_data.get("amount", 1000),
                "content": "Тестовое уведомление о возврате заказа"
            }
        else:
            return {
                "type": notification_type,
                "content": f"Тестовое уведомление типа {notification_type}"
            }
    
    async def process_sales_events(
        self,
        user_id: int,
        cabinet_id: int,
        current_sales: List[Dict[str, Any]],
        previous_sales: List[Dict[str, Any]],
        bot_webhook_url: str
    ) -> int:
        """Обработка событий продаж и возвратов"""
        try:
            # Получаем настройки пользователя
            settings = self.settings_crud.get_user_settings(self.db, user_id)
            if not settings or not settings.notifications_enabled:
                return 0
            
            # Обнаруживаем изменения в продажах
            sales_events = self.event_detector.detect_sales_changes(
                user_id, current_sales, previous_sales
            )
            
            if not sales_events:
                return 0
            
            # Фильтруем события по настройкам пользователя
            filtered_events = self._filter_sales_events_by_settings(sales_events, settings)
            
            if not filtered_events:
                return 0
            
            # Отправляем уведомления
            notifications_sent = 0
            for event in filtered_events:
                try:
                    # Генерируем уведомление
                    notification = self.notification_generator.generate_sales_notification(event)
                    
                    # Форматируем для Telegram
                    telegram_text = self._format_sales_notification_for_telegram(notification)
                    
                    # Webhook уведомления отправляются в реальном времени
                    notifications_sent += 1
                        
                    # Отслеживаем изменение
                    self.sales_monitor.track_sales_change(user_id, event)
                
                except Exception as e:
                    logger.error(f"Error processing sales event {event}: {e}")
            
            return notifications_sent
            
        except Exception as e:
            logger.error(f"Error processing sales events for user {user_id}: {e}")
            return 0
    
    def _filter_sales_events_by_settings(self, events: List[Dict[str, Any]], settings) -> List[Dict[str, Any]]:
        """Фильтрация событий продаж по настройкам пользователя"""
        filtered_events = []
        
        for event in events:
            event_type = event.get("type")
            
            # Проверяем настройки для каждого типа события
            if event_type == "new_buyout" and settings.order_buyouts_enabled:
                filtered_events.append(event)
            elif event_type == "new_return" and settings.order_returns_enabled:
                filtered_events.append(event)
            elif event_type == "sale_status_change" and settings.order_buyouts_enabled:
                filtered_events.append(event)
            elif event_type == "sale_cancellation_change" and settings.order_buyouts_enabled:
                filtered_events.append(event)
        
        return filtered_events
    
    def _format_sales_notification_for_telegram(self, notification: Dict[str, Any]) -> str:
        """Форматирование уведомления о продаже для Telegram"""
        notification_type = notification.get("type")
        
        # Используем fallback форматирование, так как BotMessageFormatter не имеет методов для продаж
        if notification_type == "new_buyout":
            return f"💰 {notification.get('title', 'Новый выкуп')}\n\n{notification.get('content', '')}"
        elif notification_type == "new_return":
            return f"🔄 {notification.get('title', 'Новый возврат')}\n\n{notification.get('content', '')}"
        elif notification_type == "sale_status_change":
            return f"📊 {notification.get('title', 'Изменение статуса')}\n\n{notification.get('content', '')}"
        elif notification_type == "sale_cancellation_change":
            return f"❌ {notification.get('title', 'Изменение отмены')}\n\n{notification.get('content', '')}"
        else:
            return f"📊 {notification.get('title', 'Уведомление о продаже')}\n\n{notification.get('content', '')}"
    
    async def _send_webhook_notification(
        self,
        user_id: int,
        notification: Dict[str, Any],
        telegram_text: str,
        bot_webhook_url: str
    ) -> Dict[str, Any]:
        """
        Отправка уведомления через webhook
        
        Args:
            user_id: ID пользователя
            notification: Данные уведомления
            telegram_text: Текст для Telegram
            bot_webhook_url: URL webhook бота
            
        Returns:
            Результат отправки
        """
        try:
            # Получаем пользователя для получения webhook URL и секрета
            from app.features.user.models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                logger.error(f"User {user_id} not found for webhook notification")
                return {"success": False, "error": "User not found"}
            
            # Используем webhook URL пользователя или переданный URL
            webhook_url = user.bot_webhook_url or bot_webhook_url
            webhook_secret = user.webhook_secret
            
            if not webhook_url:
                logger.warning(f"No webhook URL for user {user_id}")
                return {"success": False, "error": "No webhook URL configured"}
            
            # Подготавливаем данные для webhook
            # Если notification содержит data с полными данными заказа, используем их
            webhook_data = {
                "type": notification.get("type"),
                "data": notification.get("data", notification),  # Используем data если есть, иначе notification
                "user_id": user_id,
                "telegram_id": user.telegram_id,  # Добавляем telegram_id для бота
                "telegram_text": telegram_text
            }
            
            # Детальный лог webhook данных
            logger.info(f"📢 Webhook notification data for user {user_id}: {webhook_data}")
            logger.info(f"📢 Notification data keys: {list(notification.keys())}")
            if "data" in notification:
                logger.info(f"📢 Notification data.data keys: {list(notification['data'].keys())}")
            
            # Отправляем webhook
            success = await self.webhook_sender.send_notification(
                webhook_url=webhook_url,
                notification_data=webhook_data,
                webhook_secret=webhook_secret
            )
            
            if success:
                logger.info(f"Webhook notification sent successfully to user {user_id}")
                return {"success": True}
            else:
                logger.error(f"Failed to send webhook notification to user {user_id}")
                return {"success": False, "error": "Webhook delivery failed"}
                
        except Exception as e:
            logger.error(f"Error sending webhook notification to user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_sync_completion_notification(
        self,
        user_id: int,
        cabinet_id: int,
        is_first_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Отправка уведомления о завершении синхронизации через webhook
        
        Args:
            user_id: ID пользователя
            cabinet_id: ID кабинета
            is_first_sync: Является ли это первой синхронизацией
            
        Returns:
            Результат отправки
        """
        try:
            # Получаем пользователя
            from app.features.user.models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                logger.error(f"User {user_id} not found for sync completion notification")
                return {"success": False, "error": "User not found"}
            
            if not user.bot_webhook_url:
                logger.warning(f"No webhook URL configured for user {user_id}")
                return {"success": False, "error": "No webhook URL configured"}
            
            # Подготавливаем данные уведомления
            notification_data = {
                "type": "sync_completed",
                "cabinet_id": cabinet_id,
                "message": "Синхронизация завершена! Данные готовы к использованию.",
                "timestamp": TimezoneUtils.now_msk().isoformat(),
                "is_first_sync": is_first_sync
            }
            
            # Формируем текст для Telegram
            if is_first_sync:
                telegram_text = "🎉 Первая синхронизация завершена!"
            else:
                # Для последующих синхронизаций не отправляем общее сообщение
                # Отправляем только конкретные уведомления о событиях
                return {"success": True, "message": "Sync completed, no general notification sent"}
            
            # Отправляем webhook уведомление
            webhook_result = await self._send_webhook_notification(
                user_id=user_id,
                notification=notification_data,
                telegram_text=telegram_text,
                bot_webhook_url=user.bot_webhook_url
            )
            
            if webhook_result.get("success"):
                logger.info(f"✅ Sync completion webhook sent successfully to user {user_id}")
                return {"success": True, "webhook_result": webhook_result}
            else:
                logger.error(f"❌ Failed to send sync completion webhook to user {user_id}: {webhook_result}")
                return {"success": False, "error": webhook_result.get("error", "Webhook delivery failed")}
                
        except Exception as e:
            logger.error(f"Error sending sync completion notification to user {user_id}: {e}")
            return {"success": False, "error": str(e)}
