"""
Webhook Sender для отправки уведомлений боту
"""
import asyncio
import aiohttp
import hashlib
import hmac
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WebhookSender:
    """Отправитель webhook уведомлений боту"""
    
    def __init__(self):
        self.timeout = 10  # Таймаут для webhook запросов
        self.max_retries = 3  # Максимальное количество попыток
        self.retry_delays = [1, 2, 4]  # Задержки между попытками (секунды)
    
    async def send_notification(
        self, 
        webhook_url: str, 
        notification_data: Dict[str, Any],
        webhook_secret: Optional[str] = None
    ) -> bool:
        """
        Отправка уведомления на webhook URL
        
        Args:
            webhook_url: URL бота для получения webhook
            notification_data: Данные уведомления
            webhook_secret: Секрет для подписи (опционально)
        
        Returns:
            bool: True если успешно отправлено, False если ошибка
        """
        try:
            # Добавляем timestamp
            payload = {
                **notification_data,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # Временно отключаем генерацию подписи для тестирования
            # TODO: Включить генерацию подписи после настройки секретов
            signature = None
            logger.info(f"Webhook signature generation disabled for {webhook_url}")
            
            # Отправляем с retry логикой
            return await self._send_with_retry(webhook_url, payload, signature)
            
        except Exception as e:
            logger.error(f"Error sending webhook to {webhook_url}: {e}")
            return False
    
    async def send_batch_notifications(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Отправка множественных уведомлений
        
        Args:
            notifications: Список уведомлений с webhook_url и данными
        
        Returns:
            Dict с результатами отправки
        """
        results = {
            "total": len(notifications),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        # Отправляем все уведомления параллельно
        tasks = []
        for notification in notifications:
            task = self._send_single_notification(notification)
            tasks.append(task)
        
        # Ждем завершения всех задач
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({
                    "index": i,
                    "error": str(result)
                })
            elif result:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "index": i,
                    "error": "Unknown error"
                })
        
        logger.info(f"Batch webhook results: {results['success']}/{results['total']} successful")
        return results
    
    async def _send_single_notification(self, notification: Dict[str, Any]) -> bool:
        """Отправка одного уведомления"""
        try:
            webhook_url = notification.get("webhook_url")
            notification_data = notification.get("data", {})
            webhook_secret = notification.get("webhook_secret")
            
            if not webhook_url:
                logger.error("No webhook_url in notification")
                return False
            
            return await self.send_notification(webhook_url, notification_data, webhook_secret)
            
        except Exception as e:
            logger.error(f"Error in _send_single_notification: {e}")
            return False
    
    async def _send_with_retry(
        self, 
        webhook_url: str, 
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> bool:
        """Отправка с retry логикой"""
        
        # Подготавливаем заголовки
        headers = {"Content-Type": "application/json"}
        if signature:
            headers["X-Webhook-Signature"] = signature
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    response = await session.post(
                        webhook_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        headers=headers
                    )
                    
                    if response.status == 200:
                        logger.info(f"Webhook sent successfully to {webhook_url}")
                        return True
                    else:
                        logger.warning(f"Webhook failed with status {response.status}: {await response.text()}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Webhook timeout (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.warning(f"Webhook error (attempt {attempt + 1}/{self.max_retries}): {e}")
            
            # Если не последняя попытка, ждем перед retry
            if attempt < self.max_retries - 1:
                delay = self.retry_delays[attempt] if attempt < len(self.retry_delays) else self.retry_delays[-1]
                logger.info(f"Retrying webhook in {delay} seconds...")
                await asyncio.sleep(delay)
        
        logger.error(f"Webhook failed after {self.max_retries} attempts to {webhook_url}")
        return False
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Генерация HMAC подписи для webhook"""
        try:
            # Создаем строку для подписи (без signature поля)
            payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            
            # Генерируем HMAC SHA256
            signature = hmac.new(
                secret.encode('utf-8'),
                payload_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return f"sha256={signature}"
            
        except Exception as e:
            logger.error(f"Error generating webhook signature: {e}")
            return ""
    
    def verify_signature(self, payload: Dict[str, Any], signature: str, secret: str) -> bool:
        """Проверка подписи webhook"""
        try:
            if not signature.startswith("sha256="):
                return False
            
            # Убираем "sha256=" префикс
            received_signature = signature[7:]
            
            # Генерируем ожидаемую подпись
            expected_signature = self._generate_signature(payload, secret)[7:]
            
            # Сравниваем подписи безопасно
            return hmac.compare_digest(received_signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
