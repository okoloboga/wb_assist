"""
Сервис уведомлений для динамических алертов по остаткам
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, List
import logging
import os
import httpx

from app.features.wb_api.models import WBProduct
from app.features.notifications.models import NotificationSettings
from app.utils.timezone import TimezoneUtils
from .stock_analyzer import DynamicStockAnalyzer
from .crud import StockAlertHistoryCRUD
from .schemas import StockAlertHistoryCreate

logger = logging.getLogger(__name__)


class StockAlertNotificationService:
    """Сервис динамических уведомлений об остатках"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analyzer = DynamicStockAnalyzer(db)
        self.alert_crud = StockAlertHistoryCRUD()
        self.cooldown_hours = int(os.getenv("STOCK_ALERT_COOLDOWN_HOURS", "24"))
    
    async def check_and_send_alerts(
        self,
        cabinet_id: int,
        user_id: int,
        bot_webhook_url: str
    ) -> Dict[str, Any]:
        """
        Проверяет остатки и отправляет уведомления
        
        Логика:
        1. Получить список рисковых позиций через analyzer
        2. Отфильтровать позиции, по которым недавно было уведомление (cooldown)
        3. Для каждой позиции:
           - Получить информацию о товаре
           - Сформировать текст уведомления
           - Отправить через webhook
           - Записать в stock_alert_history
        
        Args:
            cabinet_id: ID кабинета
            user_id: ID пользователя
            bot_webhook_url: URL webhook бота
        
        Returns:
            Статистика отправки уведомлений
        """
        try:
            logger.info(f"Checking stock alerts for cabinet {cabinet_id}, user {user_id}")
            
            # Проверяем настройки пользователя
            user_settings = self.db.query(NotificationSettings).filter(
                NotificationSettings.user_id == user_id
            ).first()
            
            if not user_settings or not user_settings.critical_stocks_enabled:
                logger.info(f"Stock alerts disabled for user {user_id}")
                return {
                    "status": "disabled",
                    "alerts_sent": 0,
                    "alerts_skipped": 0,
                    "positions_analyzed": 0
                }
            
            # Получаем период перспективы из настроек пользователя (по умолчанию 3 дня)
            perspective_days = getattr(user_settings, 'stock_analysis_days', 3)
            
            # Получаем рисковые позиции с учетом периода перспективы пользователя
            # Фильтрация по perspective_days уже происходит внутри analyze_stock_positions
            at_risk_positions = await self.analyzer.analyze_stock_positions(cabinet_id, perspective_days=perspective_days)
            
            if not at_risk_positions:
                logger.info(f"No at-risk positions found for cabinet {cabinet_id} (уже отфильтровано по perspective_days={perspective_days})")
                return {
                    "status": "success",
                    "alerts_sent": 0,
                    "alerts_skipped": 0,
                    "positions_analyzed": 0
                }
            
            logger.info(f"Получено {len(at_risk_positions)} позиций для уведомлений (уже отфильтровано по perspective_days={perspective_days})")
            
            alerts_sent = 0
            alerts_skipped = 0
            
            # Обрабатываем каждую позицию
            for position in at_risk_positions:
                try:
                    # Проверяем, нужно ли отправлять уведомление
                    if not await self.should_send_alert(
                        cabinet_id=cabinet_id,
                        nm_id=position["nm_id"],
                        warehouse_name=position["warehouse_name"],
                        size=position["size"]
                    ):
                        alerts_skipped += 1
                        logger.info(
                            f"Skipping alert for nm_id={position['nm_id']} "
                            f"(cooldown active)"
                        )
                        continue
                    
                    # Формируем уведомление с учетом периода перспективы
                    notification_data = self._format_notification_data(position, perspective_days=perspective_days)
                    
                    # Отправляем через webhook
                    if bot_webhook_url:
                        await self.send_webhook_notification(
                            user_id=user_id,
                            webhook_url=bot_webhook_url,
                            notification_data=notification_data
                        )
                    
                    # Сохраняем в историю
                    await self.save_alert_history(cabinet_id, user_id, position)
                    
                    alerts_sent += 1
                    logger.info(
                        f"Sent alert for nm_id={position['nm_id']}, "
                        f"warehouse={position['warehouse_name']}, size={position['size']}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing alert for position: {e}")
                    continue
            
            logger.info(
                f"Stock alerts completed: {alerts_sent} sent, "
                f"{alerts_skipped} skipped, {len(at_risk_positions)} analyzed"
            )
            
            return {
                "status": "success",
                "alerts_sent": alerts_sent,
                "alerts_skipped": alerts_skipped,
                "positions_analyzed": len(at_risk_positions)
            }
            
        except Exception as e:
            logger.error(f"Error in check_and_send_alerts: {e}")
            return {
                "status": "error",
                "error": str(e),
                "alerts_sent": 0,
                "alerts_skipped": 0,
                "positions_analyzed": 0
            }
    
    async def should_send_alert(
        self,
        cabinet_id: int,
        nm_id: int,
        warehouse_name: str,
        size: str
    ) -> bool:
        """
        Проверяет, нужно ли отправлять уведомление
        
        Проверки:
        1. Не было уведомления за последние cooldown_hours
        2. Пользователь включил уведомления (проверяется в check_and_send_alerts)
        3. Остаток действительно меньше заказов за период
        
        Args:
            cabinet_id: ID кабинета
            nm_id: ID товара
            warehouse_name: Название склада
            size: Размер
        
        Returns:
            True если нужно отправить, False если нет
        """
        try:
            # Проверяем историю уведомлений (cooldown)
            recent_alert = self.alert_crud.get_recent_alert(
                db=self.db,
                cabinet_id=cabinet_id,
                nm_id=nm_id,
                warehouse_name=warehouse_name,
                size=size,
                hours=self.cooldown_hours
            )
            
            if recent_alert:
                logger.debug(
                    f"Recent alert found for nm_id={nm_id}, skipping (cooldown)"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if should send alert: {e}")
            return False
    
    def _format_notification_data(self, position: Dict[str, Any], perspective_days: int = 3) -> Dict[str, Any]:
        """
        Форматирование данных уведомления
        
        Args:
            position: Данные позиции из analyzer
            perspective_days: Период перспективы для фильтрации (по умолчанию 3 дня)
        
        Returns:
            Данные для webhook
        """
        orders_last_30_days = position.get('orders_last_24h', 0)  # Название поля для совместимости, но содержит данные за 30 дней
        
        telegram_text = f"""⚠️ КРИТИЧЕСКИЕ ОСТАТКИ

👗 {position['name']} ({position['brand']})
🆔 {position['nm_id']}
📦 {position['warehouse_name']}
📏 Размер: {position['size']}

📊 Аналитика за 30 дн.:
• Заказов: {orders_last_30_days} шт.
• Текущий остаток: {position['current_stock']} шт.
• Прогноз: {int(round(position['days_remaining']))} дн."""
        
        return {
            "type": "dynamic_stock_alert",
            "created_at": TimezoneUtils.format_for_user(TimezoneUtils.now_msk()),
            "data": {
                "nm_id": position["nm_id"],
                "name": position["name"],
                "brand": position["brand"],
                "image_url": position.get("image_url"),
                "warehouse_name": position["warehouse_name"],
                "size": position["size"],
                "current_stock": position["current_stock"],
                "orders_last_24h": position["orders_last_24h"],
                "days_remaining": position["days_remaining"],
                "avg_orders_per_day": position["orders_last_24h"],  # Approximation
                "detected_at": TimezoneUtils.format_for_user(TimezoneUtils.now_msk())
            },
            "telegram_text": telegram_text
        }
    
    async def send_webhook_notification(
        self,
        user_id: int,
        webhook_url: str,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Отправка уведомления через webhook
        
        Args:
            user_id: ID пользователя
            webhook_url: URL webhook
            notification_data: Данные уведомления
        
        Returns:
            Результат отправки
        """
        try:
            # Добавляем user_id к данным
            payload = {
                **notification_data,
                "user_id": user_id
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            
            logger.info(f"Webhook sent successfully to {webhook_url}")
            return {"status": "success"}
            
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return {"status": "error", "error": str(e)}
    
    async def save_alert_history(
        self,
        cabinet_id: int,
        user_id: int,
        position_data: Dict[str, Any]
    ) -> None:
        """
        Сохранение истории отправленного уведомления
        
        Args:
            cabinet_id: ID кабинета
            user_id: ID пользователя
            position_data: Данные позиции
        """
        try:
            alert_data = StockAlertHistoryCreate(
                cabinet_id=cabinet_id,
                user_id=user_id,
                nm_id=position_data["nm_id"],
                warehouse_name=position_data["warehouse_name"],
                size=position_data["size"],
                alert_type="dynamic_stock",
                orders_last_24h=position_data["orders_last_24h"],
                current_stock=position_data["current_stock"],
                days_remaining=position_data["days_remaining"]
            )
            
            self.alert_crud.create(self.db, alert_data)
            logger.info(f"Alert history saved for nm_id={position_data['nm_id']}")
            
        except Exception as e:
            logger.error(f"Error saving alert history: {e}")

