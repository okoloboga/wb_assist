"""
Webhook система для отправки уведомлений боту
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class WebhookSender:
    """Отправка webhook уведомлений боту"""
    
    def __init__(self, max_retries: int = 5, timeout: int = 10):
        self.max_retries = max_retries
        self.timeout = timeout

    async def send_new_order_notification(
        self, 
        telegram_id: int, 
        order_data: Dict[str, Any], 
        bot_webhook_url: str
    ) -> Dict[str, Any]:
        """Отправка уведомления о новом заказе"""
        payload = self._format_notification_payload("new_order", telegram_id, order_data)
        return await self._send_notification(payload, bot_webhook_url)

    async def send_critical_stocks_notification(
        self, 
        telegram_id: int, 
        stocks_data: Dict[str, Any], 
        bot_webhook_url: str
    ) -> Dict[str, Any]:
        """Отправка уведомления о критичных остатках"""
        payload = self._format_notification_payload("critical_stocks", telegram_id, stocks_data)
        return await self._send_notification(payload, bot_webhook_url)

    async def _send_notification(self, payload: Dict[str, Any], bot_webhook_url: str) -> Dict[str, Any]:
        """Отправка уведомления с retry логикой"""
        if not self._validate_webhook_url(bot_webhook_url):
            return {
                "success": False,
                "attempts": 0,
                "status": "failed",
                "error": "Invalid webhook URL"
            }

        for attempt in range(1, self.max_retries + 1):
            try:
                # Дополнительная защита от зависания
                async with asyncio.timeout(self.timeout + 5):  # Дополнительные 5 секунд
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                        async with session.post(bot_webhook_url, json=payload) as response:
                            if response.status == 200:
                                return {
                                    "success": True,
                                    "attempts": attempt,
                                    "status": "delivered"
                                }
                            else:
                                logger.warning(f"Webhook returned status {response.status} on attempt {attempt}")
                                
            except asyncio.TimeoutError:
                logger.error(f"Webhook attempt {attempt} timed out")
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    return {
                        "success": False,
                        "attempts": attempt,
                        "status": "failed",
                        "error": "Request timeout"
                    }
            except Exception as e:
                logger.error(f"Webhook attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    return {
                        "success": False,
                        "attempts": attempt,
                        "status": "failed",
                        "error": str(e)
                    }

        return {
            "success": False,
            "attempts": self.max_retries,
            "status": "failed",
            "error": "Max retries exceeded"
        }

    def _format_notification_payload(
        self, 
        notification_type: str, 
        telegram_id: int, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Форматирование payload для уведомления"""
        from .formatter import BotMessageFormatter
        
        formatter = BotMessageFormatter()
        
        if notification_type == "new_order":
            telegram_text = formatter.format_new_order_notification(data)
        elif notification_type == "critical_stocks":
            telegram_text = formatter.format_critical_stocks_notification(data)
        else:
            telegram_text = "Уведомление"
        
        return {
            "type": notification_type,
            "telegram_id": telegram_id,
            "data": data,
            "telegram_text": telegram_text,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_retry_delay(self, attempt: int) -> int:
        """Расчет задержки между попытками (экспоненциальная)"""
        return min(2 ** (attempt - 1), 16)

    def _validate_webhook_url(self, url: str) -> bool:
        """Валидация webhook URL"""
        if not url:
            return False
        return url.startswith(("http://", "https://"))


class NotificationQueue:
    """Очередь уведомлений"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = "notifications:queue"

    async def add_notification(
        self, 
        notification_type: str, 
        telegram_id: int, 
        data: Dict[str, Any], 
        priority: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """Добавление уведомления в очередь"""
        try:
            notification = {
                "id": f"notif_{int(datetime.now().timestamp() * 1000)}",
                "type": notification_type,
                "telegram_id": telegram_id,
                "data": data,
                "priority": priority,
                "created_at": datetime.now().isoformat()
            }
            
            serialized = self._serialize_notification(notification)
            await self.redis.lpush(self.queue_key, serialized)
            
            return {
                "success": True,
                "notification_id": notification["id"]
            }
            
        except Exception as e:
            logger.error(f"Ошибка добавления уведомления в очередь: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def process_notifications(self, max_items: int = 100, timeout: int = 1, max_processing_time: int = 30) -> Dict[str, Any]:
        """Обработка уведомлений из очереди"""
        processed = 0
        successful = 0
        failed = 0
        start_time = asyncio.get_event_loop().time()
        
        try:
            while processed < max_items:
                # Проверяем общий таймаут обработки
                if asyncio.get_event_loop().time() - start_time > max_processing_time:
                    logger.warning(f"Превышен максимальный таймаут обработки ({max_processing_time}с)")
                    break
                
                try:
                    result = await asyncio.wait_for(
                        self.redis.brpop(self.queue_key, timeout=timeout),
                        timeout=timeout + 1  # Дополнительная защита
                    )
                except asyncio.TimeoutError:
                    # Нормальное завершение - нет элементов в очереди
                    break
                
                if not result or not result[1]:
                    # Дополнительная проверка на пустой результат
                    break
                
                _, notification_json = result
                notification = self._deserialize_notification(notification_json)
                
                try:
                    # Ограничиваем время обработки одного уведомления
                    await asyncio.wait_for(
                        self._process_single_notification(notification),
                        timeout=5
                    )
                    successful += 1
                except asyncio.TimeoutError:
                    logger.error(f"Таймаут обработки уведомления {notification.get('id')}")
                    failed += 1
                except Exception as e:
                    logger.error(f"Ошибка обработки уведомления {notification.get('id')}: {e}")
                    failed += 1
                
                processed += 1
                
        except Exception as e:
            logger.error(f"Ошибка обработки очереди уведомлений: {e}")
        
        return {
            "processed": processed,
            "successful": successful,
            "failed": failed
        }

    async def _process_single_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка одного уведомления"""
        # Заглушка - в реальности здесь будет отправка через WebhookSender
        return {"success": True}

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Получение статистики очереди"""
        try:
            queue_size = await self.redis.llen(self.queue_key)
            
            # Получаем статистику из Redis hash
            stats = await self.redis.hgetall("notification_stats")
            
            total_processed = int(stats.get("total_processed", 0))
            total_successful = int(stats.get("total_successful", 0))
            total_failed = int(stats.get("total_failed", 0))
            
            success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 0
            
            return {
                "queue_size": queue_size,
                "total_processed": total_processed,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "success_rate": success_rate
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики очереди: {e}")
            return {
                "queue_size": 0,
                "total_processed": 0,
                "total_successful": 0,
                "total_failed": 0,
                "success_rate": 0.0
            }

    async def clear_queue(self) -> Dict[str, Any]:
        """Очистка очереди"""
        try:
            deleted_count = await self.redis.delete(self.queue_key)
            return {
                "success": True,
                "deleted_count": deleted_count
            }
        except Exception as e:
            logger.error(f"Ошибка очистки очереди: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_priority_score(self, priority: str) -> int:
        """Получение числового приоритета"""
        priority_scores = {
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3
        }
        return priority_scores.get(priority, 4)

    def _serialize_notification(self, notification: Dict[str, Any]) -> str:
        """Сериализация уведомления"""
        return json.dumps(notification, ensure_ascii=False)

    def _deserialize_notification(self, notification_json: str) -> Dict[str, Any]:
        """Десериализация уведомления"""
        return json.loads(notification_json)