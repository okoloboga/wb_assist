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
from .sales_monitor import SalesMonitor
from .notification_generator import NotificationGenerator
from .crud import (
    NotificationSettingsCRUD,
    NotificationHistoryCRUD,
    OrderStatusHistoryCRUD
)
# Webhook интеграция удалена - используется только polling
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
        self.sales_monitor = SalesMonitor(redis_client)
        self.notification_generator = NotificationGenerator()
        # Webhook sender удален - используется только polling
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
        # bot_webhook_url удален - используется только polling
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
        
        # detect_negative_reviews удален - используется только polling система
        
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
    
    # _send_notifications удален - используется только polling система
    
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
    
    # _send_webhook_notification удален - используется только polling система
    
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
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting new events for user {user_id}: {e}")
            return []
    
    async def _get_new_orders(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение новых заказов"""
        try:
            from sqlalchemy import desc
            from sqlalchemy import func
            from app.features.wb_api.models import WBOrder, WBCabinet, WBSyncLog, WBReview

            # Защита от первой синхронизации
            cabinets = self.db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
            if not cabinets:
                return []
            for cabinet in cabinets:
                if not cabinet.last_sync_at:
                    logger.info(f"Skipping order notifications for cabinet {cabinet.id} - first sync")
                    return []

            # Предыдущая завершенная синхронизация
            prev_sync_at_by_cab: Dict[int, datetime] = {}
            for cab in cabinets:
                # Ищем любую предыдущую синхронизацию (не обязательно completed)
                prev_sync = (
                    self.db.query(WBSyncLog)
                    .filter(WBSyncLog.cabinet_id == cab.id)
                    .order_by(desc(WBSyncLog.started_at))
                    .offset(1)
                    .first()
                )
                if not prev_sync:
                    # Если нет логов синхронизации, используем last_sync_at кабинета
                    if cab.last_sync_at:
                        prev_sync_at_by_cab[cab.id] = cab.last_sync_at
                        logger.info(f"Using cabinet last_sync_at for cabinet {cab.id}: {cab.last_sync_at}")
                    else:
                        logger.info(f"Skipping order notifications for cabinet {cab.id} - no sync history")
                        return []
                else:
                    prev_sync_at_by_cab[cab.id] = prev_sync.completed_at or prev_sync.started_at
                    logger.info(f"Using previous sync for cabinet {cab.id}: {prev_sync_at_by_cab[cab.id]}")

            # Кандидаты по последнему окну polling
            orders = self.db.query(WBOrder).filter(
                WBOrder.cabinet_id.in_(cabinet_ids),
                WBOrder.created_at > last_check
            ).all()

            # Фильтр по предыдущей синхронизации
            orders = [
                o for o in orders
                if o.created_at and prev_sync_at_by_cab.get(o.cabinet_id) and o.created_at > prev_sync_at_by_cab[o.cabinet_id]
            ]
            
            events = []
            from app.features.wb_api.models import WBProduct
            for order in orders:
                # Обогащаем данные заказа для форматтера
                product = self.db.query(WBProduct).filter(WBProduct.nm_id == order.nm_id).first()
                rating = (product.rating or 0.0) if product else 0.0
                reviews_cnt = (product.reviews_count or 0) if product else 0
                image_url = product.image_url if product and getattr(product, "image_url", None) else None
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
                    "amount": order.total_price or 0,
                    "product_name": order.name or "Неизвестно",
                    "brand": order.brand or "Неизвестно",
                    "nm_id": order.nm_id,
                    "supplier_article": order.article or "",
                    "size": order.size or "",
                    "barcode": order.barcode or "",
                    "warehouse_from": order.warehouse_from or "",
                    "warehouse_to": order.warehouse_to or "",
                    "spp_percent": order.spp_percent or 0.0,
                    "customer_price": order.customer_price or 0.0,
                    "logistics_amount": order.logistics_amount or 0.0,
                    "rating": rating,
                    "reviews_count": reviews_cnt,
                    "sales_periods": {},
                    "status": order.status,
                    "image_url": image_url,
                }
                telegram_text = self.message_formatter.format_order_detail({"order": order_data})

                events.append({
                    "type": "new_order",
                    "user_id": user_id,
                    "data": order_data,
                    "telegram_text": telegram_text,
                    "created_at": order.created_at or datetime.now(timezone.utc),
                    "priority": "MEDIUM"
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting new orders: {e}")
            return []
    
    async def _get_new_reviews(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение новых негативных отзывов (0-3 звезды)"""
        try:
            from app.features.wb_api.models import WBReview, WBCabinet
            
            # Проверяем, что это не первая синхронизация кабинета
            # Если last_sync_at не установлен или очень старый, пропускаем уведомления
            cabinets = self.db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
            for cabinet in cabinets:
                if not cabinet.last_sync_at:
                    logger.info(f"Skipping review notifications for cabinet {cabinet.id} - first sync")
                    return []
                
                # Проверяем, была ли синхронизация в последние 24 часа
                from datetime import timedelta
                time_diff = datetime.now(timezone.utc) - cabinet.last_sync_at
                if time_diff > timedelta(hours=24):
                    logger.info(f"Skipping review notifications for cabinet {cabinet.id} - long break since last sync")
                    return []
            
            reviews = self.db.query(WBReview).filter(
                WBReview.cabinet_id.in_(cabinet_ids),
                WBReview.created_date > last_check  # Используем время создания отзыва, а не обновления
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
                        "created_at": review.created_date or datetime.now(timezone.utc),
                        "priority": "HIGH"
                    })
                # Положительные отзывы (4-5 звезд) игнорируем - уведомления не нужны
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting new reviews: {e}")
            return []
    
    async def _get_critical_stocks(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение критических остатков по факту перехода через порог (<=2 с >2 ранее)."""
        try:
            from app.features.wb_api.models import WBStock, WBCabinet, WBProduct
            from sqlalchemy import and_
            
            # Проверяем, что это не первая синхронизация кабинета
            cabinets = self.db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
            for cabinet in cabinets:
                if not cabinet.last_sync_at:
                    logger.info(f"Skipping critical stocks notifications for cabinet {cabinet.id} - first sync")
                    return []
                # Убираем проверку на долгий перерыв - это может блокировать важные уведомления
            
            critical_threshold = 2
            
            # Текущие обновления после last_check (кандидаты)
            current_rows = (
                self.db.query(WBStock)
                .filter(
                    WBStock.cabinet_id.in_(cabinet_ids),
                    WBStock.updated_at > last_check
                )
                .all()
            )
            if not current_rows:
                return []
            
            # Подготовка нормализации размера
            def _norm_size(s: str) -> str:
                return (s or "").strip().upper()

            # Агрегируем суммарные количества по всем складам для текущего снимка
            current_sum_map: Dict[tuple, int] = {}
            key_pairs = set()
            for r in current_rows:
                key = (r.nm_id, _norm_size(r.size))
                key_pairs.add(key)
                current_sum_map[key] = current_sum_map.get(key, 0) + (r.quantity or 0)

            # Снимок предыдущих значений для этих nm_id до/на момент last_check и агрегация
            prev_rows = (
                self.db.query(WBStock)
                .filter(
                    WBStock.cabinet_id.in_(cabinet_ids),
                    WBStock.updated_at <= last_check,
                    WBStock.nm_id.in_({k[0] for k in key_pairs})
                )
                .all()
            )
            prev_sum_map: Dict[tuple, int] = {}
            for r in prev_rows:
                key = (r.nm_id, _norm_size(r.size))
                prev_sum_map[key] = prev_sum_map.get(key, 0) + (r.quantity or 0)

            # Детект перехода через порог ТОЛЬКО при реальном снижении с >2 до <=2
            per_nm: Dict[int, Dict[str, Any]] = {}
            for (nm, sz), cur_total in current_sum_map.items():
                if cur_total <= 0:
                    continue  # нули сейчас не сигналим
                prev_total = prev_sum_map.get((nm, sz))
                # Требуем наличие прошлого значения и реальное снижение
                if prev_total is None:
                    continue
                if prev_total > critical_threshold and cur_total <= critical_threshold and cur_total < prev_total:
                    if nm not in per_nm:
                        per_nm[nm] = {"nm_id": nm, "stocks": {}, "critical_sizes": [], "zero_sizes": []}
                    per_nm[nm]["stocks"][sz] = cur_total
                    per_nm[nm]["critical_sizes"].append(sz)
            
            if not per_nm:
                return []
            
            # Подтягиваем названия из WBProduct
            products = {p.nm_id: p for p in self.db.query(WBProduct).filter(WBProduct.nm_id.in_(list(per_nm.keys()))).all()}
            events = []
            for nm_id, info in per_nm.items():
                prod = products.get(nm_id)
                name = None
                if prod and getattr(prod, "name", None):
                    name = prod.name
                if not name:
                    name = f"Товар {nm_id}"
                events.append({
                    "type": "critical_stocks",
                    "user_id": user_id,
                    "data": {
                        "nm_id": nm_id,
                        "name": name,
                        "stocks": info["stocks"],
                        "critical_sizes": info["critical_sizes"],
                        "zero_sizes": info["zero_sizes"],
                    },
                    "created_at": datetime.now(timezone.utc),
                    "priority": "HIGH"
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting critical stocks: {e}")
            return []
    
    async def _get_status_changes(self, user_id: int, cabinet_ids: List[int], last_check: datetime) -> List[Dict[str, Any]]:
        """Получение изменений статусов заказов"""
        try:
            from app.features.wb_api.models import WBOrder
            
            # Получаем заказы с изменениями статуса
            orders = self.db.query(WBOrder).filter(
                WBOrder.cabinet_id.in_(cabinet_ids),
                WBOrder.updated_at > last_check,
                WBOrder.status.in_(['buyout', 'canceled', 'return'])
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
                
                events.append({
                    "type": event_type,
                    "user_id": user_id,
                    "data": {
                        "order_id": order.order_id,
                        "amount": order.total_price,
                        "product_name": order.name,
                        "brand": order.brand,
                        "status": order.status,
                        "updated_at": order.updated_at.isoformat() if order.updated_at else None
                    },
                    "created_at": order.updated_at or datetime.now(timezone.utc),
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
                    
                    # Webhook удален - уведомления отправляются через polling
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
