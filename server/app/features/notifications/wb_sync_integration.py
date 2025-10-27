"""
Интеграция NotificationService с WBSyncService
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from .notification_service import NotificationService
from ..wb_api.models import WBCabinet, WBOrder, WBReview, WBStock

logger = logging.getLogger(__name__)


class WBSyncNotificationIntegration:
    """Интеграция NotificationService с WBSyncService"""
    
    def __init__(self, db: Session, notification_service: NotificationService = None):
        self.db = db
        self.notification_service = notification_service or NotificationService(db)
    
    async def process_sync_notifications(
        self,
        cabinet: WBCabinet,
        current_orders: List[Dict[str, Any]] = None,
        previous_orders: List[Dict[str, Any]] = None,
        current_reviews: List[Dict[str, Any]] = None,
        previous_reviews: List[Dict[str, Any]] = None,
        current_stocks: List[Dict[str, Any]] = None,
        previous_stocks: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Обработка уведомлений после синхронизации данных для ВСЕХ пользователей кабинета"""
        try:
            # Получаем ВСЕХ пользователей кабинета
            from app.features.user.models import User
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
            
            if not user_ids:
                logger.warning(f"No users found for cabinet {cabinet.id}")
                return {"status": "error", "error": "No users found"}
            
            logger.info(f"🔔 Processing notifications for {len(user_ids)} users of cabinet {cabinet.id}")
            
            # Обрабатываем уведомления для КАЖДОГО пользователя
            total_notifications_sent = 0
            results = []
            
            for user_id in user_ids:
                try:
                    # Получаем данные пользователя
                    user = self.db.query(User).filter(User.id == user_id).first()
                    if not user:
                        logger.warning(f"User {user_id} not found, skipping")
                        continue
                    
                    logger.info(f"🔔 Processing notifications for user {user_id} (telegram_id: {user.telegram_id})")
                    
                    # Обрабатываем события через NotificationService для каждого пользователя
                    result = await self.notification_service.process_sync_events(
                        user_id=user.id,
                        cabinet_id=cabinet.id,
                        current_orders=current_orders or [],
                        previous_orders=previous_orders or [],
                        current_reviews=current_reviews or [],
                        previous_reviews=previous_reviews or [],
                        current_stocks=current_stocks or [],
                        previous_stocks=previous_stocks or []
                    )
                    
                    notifications_sent = result.get('notifications_sent', 0)
                    total_notifications_sent += notifications_sent
                    
                    results.append({
                        "user_id": user_id,
                        "telegram_id": user.telegram_id,
                        "notifications_sent": notifications_sent,
                        "status": result.get('status', 'unknown')
                    })
                    
                    logger.info(f"✅ User {user_id}: {notifications_sent} notifications sent")
                    
                except Exception as user_error:
                    logger.error(f"❌ Error processing notifications for user {user_id}: {user_error}")
                    results.append({
                        "user_id": user_id,
                        "notifications_sent": 0,
                        "status": "error",
                        "error": str(user_error)
                    })
            
            logger.info(f"🎉 Total notifications sent: {total_notifications_sent} to {len(user_ids)} users of cabinet {cabinet.id}")
            
            return {
                "status": "success",
                "total_notifications_sent": total_notifications_sent,
                "users_processed": len(user_ids),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error processing sync notifications for cabinet {cabinet.id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def send_new_order_notification(
        self,
        cabinet: WBCabinet,
        order_data: Dict[str, Any],
        order: WBOrder
    ) -> Dict[str, Any]:
        """Отправка уведомления о новом заказе через NotificationService"""
        try:
            # Получаем webhook URL пользователя
            from app.features.user.models import User
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
            user = self.db.query(User).filter(User.id.in_(user_ids)).first() if user_ids else None
            if not user:
                logger.warning(f"User not found for cabinet {cabinet.id}")
                return {"status": "error", "error": "User not found"}
            
            bot_webhook_url = getattr(user, 'bot_webhook_url', None)
            if not bot_webhook_url:
                logger.warning(f"Bot webhook URL not found for user {user.id}")
                return {"status": "error", "error": "Bot webhook URL not found"}
            
            # Обрабатываем событие нового заказа
            result = await self.notification_service.process_sync_events(
                user_id=user.id,
                cabinet_id=cabinet.id,
                current_orders=[order_data],
                previous_orders=[],
                bot_webhook_url=bot_webhook_url
            )
            
            logger.info(f"New order notification sent for order {order_data.get('order_id', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending new order notification: {e}")
            return {"status": "error", "error": str(e)}
    
    async def send_critical_stocks_notification(
        self,
        cabinet: WBCabinet,
        stocks_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Отправка уведомления о критичных остатках через NotificationService"""
        try:
            # Получаем webhook URL пользователя
            from app.features.user.models import User
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
            user = self.db.query(User).filter(User.id.in_(user_ids)).first() if user_ids else None
            if not user:
                logger.warning(f"User not found for cabinet {cabinet.id}")
                return {"status": "error", "error": "User not found"}
            
            bot_webhook_url = getattr(user, 'bot_webhook_url', None)
            if not bot_webhook_url:
                logger.warning(f"Bot webhook URL not found for user {user.id}")
                return {"status": "error", "error": "Bot webhook URL not found"}
            
            # Обрабатываем событие критичных остатков
            result = await self.notification_service.process_sync_events(
                user_id=user.id,
                cabinet_id=cabinet.id,
                current_orders=[],
                previous_orders=[],
                current_stocks=stocks_data,
                previous_stocks=[],
                bot_webhook_url=bot_webhook_url
            )
            
            logger.info(f"Critical stocks notification sent for {len(stocks_data)} products")
            return result
            
        except Exception as e:
            logger.error(f"Error sending critical stocks notification: {e}")
            return {"status": "error", "error": str(e)}
    
    def create_notification_service_wrapper(self, original_method):
        """Создает обертку для замены существующего метода отправки уведомлений"""
        async def wrapper(cabinet, *args, **kwargs):
            try:
                # Определяем тип уведомления по количеству аргументов и их типам
                if len(args) >= 2 and isinstance(args[1], dict):
                    # Новый заказ: cabinet, order_data, order
                    order_data = args[1]
                    return await self.send_new_order_notification(cabinet, order_data, args[2] if len(args) > 2 else None)
                elif len(args) >= 1 and isinstance(args[0], list):
                    # Критичные остатки: cabinet, stocks_data
                    stocks_data = args[0]
                    return await self.send_critical_stocks_notification(cabinet, stocks_data)
                else:
                    # Вызываем оригинальный метод для обратной совместимости
                    return await original_method(cabinet, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in notification wrapper: {e}")
                # Fallback к оригинальному методу
                return await original_method(cabinet, *args, **kwargs)
        
        return wrapper
    
    async def process_sales_notifications(
        self,
        cabinet: WBCabinet,
        current_sales: List[Dict[str, Any]] = None,
        previous_sales: List[Dict[str, Any]] = None,
        bot_webhook_url: str = None
    ) -> Dict[str, Any]:
        """Обработка уведомлений о продажах и возвратах"""
        try:
            if not current_sales:
                current_sales = []
            if not previous_sales:
                previous_sales = []
            
            # Получаем webhook URL
            if not bot_webhook_url:
                from app.core.config import settings
                bot_webhook_url = settings.BOT_WEBHOOK_URL
            
            # Обрабатываем события продаж
            notifications_sent = await self.notification_service.process_sales_events(
                # user_id берём из владельцев/пользователей кабинета
                user_id=user_ids[0] if user_ids else None,
                cabinet_id=cabinet.id,
                current_sales=current_sales,
                previous_sales=previous_sales,
                bot_webhook_url=bot_webhook_url
            )
            
            logger.info(f"Sales notifications processed for cabinet {cabinet.id}: {notifications_sent} sent")
            
            return {
                "status": "success",
                "notifications_sent": notifications_sent,
                "sales_processed": len(current_sales)
            }
            
        except Exception as e:
            logger.error(f"Error processing sales notifications for cabinet {cabinet.id}: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "notifications_sent": 0
            }
    
    async def send_new_buyout_notification(
        self,
        cabinet: WBCabinet,
        buyout_data: Dict[str, Any],
        bot_webhook_url: str = None
    ) -> Dict[str, Any]:
        """Отправка уведомления о новом выкупе"""
        try:
            if not bot_webhook_url:
                from app.core.config import settings
                bot_webhook_url = settings.BOT_WEBHOOK_URL
            
            # Создаем событие выкупа
            event = {
                "type": "new_buyout",
                "user_id": (user_ids[0] if user_ids else None),
                "sale_id": buyout_data.get("sale_id"),
                "order_id": buyout_data.get("order_id"),
                "product_name": buyout_data.get("product_name"),
                "amount": buyout_data.get("amount"),
                "sale_date": buyout_data.get("sale_date"),
                "nm_id": buyout_data.get("nm_id"),
                "brand": buyout_data.get("brand"),
                "size": buyout_data.get("size")
            }
            
            # Генерируем уведомление
            notification = self.notification_service.notification_generator.generate_sales_notification(event)
            
            # Форматируем для Telegram
            telegram_text = self.notification_service._format_sales_notification_for_telegram(notification)
            
            # Отправляем webhook
            result = await self.notification_service._send_webhook_notification(
                (user_ids[0] if user_ids else None), notification, telegram_text, bot_webhook_url
            )
            
            if result.get("success"):
                logger.info(f"Buyout notification sent for cabinet {cabinet.id}, sale {buyout_data.get('sale_id')}")
                return {"status": "success", "notification_sent": True}
            else:
                logger.warning(f"Failed to send buyout notification: {result.get('error')}")
                return {"status": "error", "notification_sent": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Error sending buyout notification for cabinet {cabinet.id}: {e}")
            return {"status": "error", "notification_sent": False, "error": str(e)}
    
    async def send_new_return_notification(
        self,
        cabinet: WBCabinet,
        return_data: Dict[str, Any],
        bot_webhook_url: str = None
    ) -> Dict[str, Any]:
        """Отправка уведомления о новом возврате"""
        try:
            if not bot_webhook_url:
                from app.core.config import settings
                bot_webhook_url = settings.BOT_WEBHOOK_URL
            
            # Создаем событие возврата
            event = {
                "type": "new_return",
                "user_id": (user_ids[0] if user_ids else None),
                "sale_id": return_data.get("sale_id"),
                "order_id": return_data.get("order_id"),
                "product_name": return_data.get("product_name"),
                "amount": return_data.get("amount"),
                "sale_date": return_data.get("sale_date"),
                "nm_id": return_data.get("nm_id"),
                "brand": return_data.get("brand"),
                "size": return_data.get("size")
            }
            
            # Генерируем уведомление
            notification = self.notification_service.notification_generator.generate_sales_notification(event)
            
            # Форматируем для Telegram
            telegram_text = self.notification_service._format_sales_notification_for_telegram(notification)
            
            # Отправляем webhook
            result = await self.notification_service._send_webhook_notification(
                (user_ids[0] if user_ids else None), notification, telegram_text, bot_webhook_url
            )
            
            if result.get("success"):
                logger.info(f"Return notification sent for cabinet {cabinet.id}, sale {return_data.get('sale_id')}")
                return {"status": "success", "notification_sent": True}
            else:
                logger.warning(f"Failed to send return notification: {result.get('error')}")
                return {"status": "error", "notification_sent": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Error sending return notification for cabinet {cabinet.id}: {e}")
            return {"status": "error", "notification_sent": False, "error": str(e)}
