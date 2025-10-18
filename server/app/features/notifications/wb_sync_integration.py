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
        """Обработка уведомлений после синхронизации данных"""
        try:
            # Получаем webhook URL пользователя
            from app.features.user.models import User
            user = self.db.query(User).filter(User.id == cabinet.user_id).first()
            if not user:
                logger.warning(f"User not found for cabinet {cabinet.id}")
                return {"status": "error", "error": "User not found"}
            
            bot_webhook_url = getattr(user, 'bot_webhook_url', None)
            if not bot_webhook_url:
                logger.warning(f"Bot webhook URL not found for user {user.id}")
                return {"status": "error", "error": "Bot webhook URL not found"}
            
            # Обрабатываем события через NotificationService
            result = await self.notification_service.process_sync_events(
                user_id=user.id,
                cabinet_id=cabinet.id,
                current_orders=current_orders or [],
                previous_orders=previous_orders or [],
                current_reviews=current_reviews or [],
                previous_reviews=previous_reviews or [],
                current_stocks=current_stocks or [],
                previous_stocks=previous_stocks or [],
                bot_webhook_url=bot_webhook_url
            )
            
            logger.info(f"NotificationService processed {result.get('notifications_sent', 0)} notifications for cabinet {cabinet.id}")
            return result
            
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
            user = self.db.query(User).filter(User.id == cabinet.user_id).first()
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
            user = self.db.query(User).filter(User.id == cabinet.user_id).first()
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
