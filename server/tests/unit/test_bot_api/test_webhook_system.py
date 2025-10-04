"""
Unit тесты для webhook системы Bot API
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from app.features.bot_api.webhook import WebhookSender, NotificationQueue


class TestWebhookSender:
    """Тесты для отправки webhook уведомлений"""

    @pytest.fixture
    def webhook_sender(self):
        """Фикстура для webhook sender"""
        return WebhookSender()

    @pytest.fixture
    def sample_new_order_data(self):
        """Фикстура для данных нового заказа"""
        return {
            "order_id": 154,
            "date": "2025-10-03T12:48:00",
            "amount": 1410,
            "product_name": "Шифоновая блузка (S)",
            "brand": "SLAVALOOK BRAND",
            "warehouse_from": "Электросталь",
            "warehouse_to": "ЦФО/Москва",
            "today_stats": {
                "count": 19,
                "amount": 26790
            },
            "stocks": {
                "S": 13,
                "M": 1,
                "L": 0,
                "XL": 0
            }
        }

    @pytest.fixture
    def sample_critical_stocks_data(self):
        """Фикстура для данных критичных остатков"""
        return {
            "products": [
                {
                    "nm_id": 270591287,
                    "name": "Шифоновая блузка",
                    "brand": "SLAVALOOK BRAND",
                    "stocks": {"S": 13, "M": 1, "L": 0, "XL": 0},
                    "critical_sizes": ["M"],
                    "zero_sizes": ["L", "XL"],
                    "days_left": {"M": 0}
                }
            ]
        }

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_send_new_order_notification_success(self, webhook_sender, sample_new_order_data):
        """Тест успешной отправки уведомления о новом заказе"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await webhook_sender.send_new_order_notification(
                telegram_id=123456789,
                order_data=sample_new_order_data,
                bot_webhook_url="http://bot:8000/webhook"
            )
            
            assert result["success"] is True
            assert result["attempts"] == 1
            assert result["status"] == "delivered"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_send_critical_stocks_notification_success(self, webhook_sender, sample_critical_stocks_data):
        """Тест успешной отправки уведомления о критичных остатках"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await webhook_sender.send_critical_stocks_notification(
                telegram_id=123456789,
                stocks_data=sample_critical_stocks_data,
                bot_webhook_url="http://bot:8000/webhook"
            )
            
            assert result["success"] is True
            assert result["attempts"] == 1
            assert result["status"] == "delivered"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_retry_logic(self, webhook_sender, sample_new_order_data):
        """Тест логики повторных попыток отправки"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Первые 3 попытки неудачные, 4-я успешная
            mock_responses = [
                AsyncMock(status=500),  # 1-я попытка
                AsyncMock(status=503),  # 2-я попытка
                AsyncMock(status=500),  # 3-я попытка
                AsyncMock(status=200, json=AsyncMock(return_value={"success": True}))  # 4-я попытка
            ]
            mock_post.return_value.__aenter__.side_effect = mock_responses
            
            result = await webhook_sender.send_new_order_notification(
                telegram_id=123456789,
                order_data=sample_new_order_data,
                bot_webhook_url="http://bot:8000/webhook"
            )
            
            assert result["success"] is True
            assert result["attempts"] == 4
            assert result["status"] == "delivered"
            assert mock_post.call_count == 4

    @pytest.mark.asyncio
    async def test_send_notification_max_retries_exceeded(self, webhook_sender, sample_new_order_data):
        """Тест превышения максимального количества попыток"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Все попытки неудачные
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await webhook_sender.send_new_order_notification(
                telegram_id=123456789,
                order_data=sample_new_order_data,
                bot_webhook_url="http://bot:8000/webhook"
            )
            
            assert result["success"] is False
            assert result["attempts"] == 5
            assert result["status"] == "failed"
            assert mock_post.call_count == 5

    @pytest.mark.asyncio
    async def test_send_notification_timeout_handling(self, webhook_sender, sample_new_order_data):
        """Тест обработки таймаута"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Timeout")
            
            result = await webhook_sender.send_new_order_notification(
                telegram_id=123456789,
                order_data=sample_new_order_data,
                bot_webhook_url="http://bot:8000/webhook"
            )
            
            assert result["success"] is False
            assert result["attempts"] == 1
            assert result["status"] == "failed"
            assert "Timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_send_notification_invalid_url(self, webhook_sender, sample_new_order_data):
        """Тест обработки неверного URL"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Invalid URL")
            
            result = await webhook_sender.send_new_order_notification(
                telegram_id=123456789,
                order_data=sample_new_order_data,
                bot_webhook_url="invalid_url"
            )
            
            assert result["success"] is False
            assert result["attempts"] == 1
            assert result["status"] == "failed"
            assert "Invalid URL" in result["error"]

    @pytest.mark.asyncio
    async def test_send_notification_network_error(self, webhook_sender, sample_new_order_data):
        """Тест обработки сетевой ошибки"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = await webhook_sender.send_new_order_notification(
                telegram_id=123456789,
                order_data=sample_new_order_data,
                bot_webhook_url="http://bot:8000/webhook"
            )
            
            assert result["success"] is False
            assert result["attempts"] == 1
            assert result["status"] == "failed"
            assert "Network error" in result["error"]

    def test_format_notification_payload_new_order(self, webhook_sender, sample_new_order_data):
        """Тест форматирования payload для нового заказа"""
        payload = webhook_sender._format_notification_payload(
            notification_type="new_order",
            telegram_id=123456789,
            data=sample_new_order_data
        )
        
        assert payload["type"] == "new_order"
        assert payload["telegram_id"] == 123456789
        assert "data" in payload
        assert "telegram_text" in payload
        assert payload["data"]["order_id"] == 154
        assert "🎉 НОВЫЙ ЗАКАЗ!" in payload["telegram_text"]

    def test_format_notification_payload_critical_stocks(self, webhook_sender, sample_critical_stocks_data):
        """Тест форматирования payload для критичных остатков"""
        payload = webhook_sender._format_notification_payload(
            notification_type="critical_stocks",
            telegram_id=123456789,
            data=sample_critical_stocks_data
        )
        
        assert payload["type"] == "critical_stocks"
        assert payload["telegram_id"] == 123456789
        assert "data" in payload
        assert "telegram_text" in payload
        assert len(payload["data"]["products"]) == 1
        assert "⚠️ КРИТИЧНЫЕ ОСТАТКИ!" in payload["telegram_text"]

    def test_calculate_retry_delay(self, webhook_sender):
        """Тест расчета задержки между попытками"""
        assert webhook_sender._calculate_retry_delay(1) == 1
        assert webhook_sender._calculate_retry_delay(2) == 2
        assert webhook_sender._calculate_retry_delay(3) == 4
        assert webhook_sender._calculate_retry_delay(4) == 8
        assert webhook_sender._calculate_retry_delay(5) == 16

    def test_validate_webhook_url(self, webhook_sender):
        """Тест валидации webhook URL"""
        assert webhook_sender._validate_webhook_url("http://bot:8000/webhook") is True
        assert webhook_sender._validate_webhook_url("https://bot.example.com/webhook") is True
        assert webhook_sender._validate_webhook_url("invalid_url") is False
        assert webhook_sender._validate_webhook_url("") is False
        assert webhook_sender._validate_webhook_url(None) is False


class TestNotificationQueue:
    """Тесты для очереди уведомлений"""

    @pytest.fixture
    def mock_redis(self):
        """Фикстура для мока Redis"""
        return AsyncMock()

    @pytest.fixture
    def notification_queue(self, mock_redis):
        """Фикстура для очереди уведомлений"""
        return NotificationQueue(mock_redis)

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_add_notification_success(self, notification_queue, mock_redis):
        """Тест успешного добавления уведомления в очередь"""
        mock_redis.lpush.return_value = 1
        
        result = await notification_queue.add_notification(
            notification_type="new_order",
            telegram_id=123456789,
            data={"test": "data"},
            priority="HIGH"
        )
        
        assert result["success"] is True
        assert "notification_id" in result
        mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_add_notification_redis_error(self, notification_queue, mock_redis):
        """Тест обработки ошибки Redis при добавлении уведомления"""
        mock_redis.lpush.side_effect = Exception("Redis connection failed")
        
        result = await notification_queue.add_notification(
            notification_type="new_order",
            telegram_id=123456789,
            data={"test": "data"},
            priority="HIGH"
        )
        
        assert result["success"] is False
        assert "Redis connection failed" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_process_notifications_success(self, notification_queue, mock_redis):
        """Тест успешной обработки уведомлений из очереди"""
        mock_notification = {
            "id": "notif_123",
            "type": "new_order",
            "telegram_id": 123456789,
            "data": {"test": "data"},
            "priority": "HIGH",
            "created_at": "2025-01-28T14:30:15"
        }
        
        # Мокаем brpop с таймаутом 1 секунда
        mock_redis.brpop.return_value = ("notifications:queue", json.dumps(mock_notification))
        
        with patch.object(notification_queue, '_process_single_notification') as mock_process:
            mock_process.return_value = {"success": True}
            
            # Ограничиваем время выполнения теста
            result = await notification_queue.process_notifications(max_items=1, timeout=1, max_processing_time=5)
            
            assert result["processed"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_process_notifications_empty_queue(self, notification_queue, mock_redis):
        """Тест обработки пустой очереди"""
        mock_redis.brpop.return_value = None
        
        result = await notification_queue.process_notifications(max_items=1, timeout=1, max_processing_time=5)
        
        assert result["processed"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_process_notifications_processing_error(self, notification_queue, mock_redis):
        """Тест обработки ошибки при обработке уведомления"""
        mock_notification = {
            "id": "notif_123",
            "type": "new_order",
            "telegram_id": 123456789,
            "data": {"test": "data"},
            "priority": "HIGH",
            "created_at": "2025-01-28T14:30:15"
        }
        
        mock_redis.brpop.return_value = ("notifications:queue", json.dumps(mock_notification))
        
        with patch.object(notification_queue, '_process_single_notification') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            result = await notification_queue.process_notifications(max_items=1, timeout=1, max_processing_time=5)
            
            assert result["processed"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 1

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_get_queue_stats_success(self, notification_queue, mock_redis):
        """Тест получения статистики очереди"""
        mock_redis.llen.return_value = 5
        mock_redis.hgetall.return_value = {
            "total_processed": "100",
            "total_successful": "95",
            "total_failed": "5"
        }
        
        result = await notification_queue.get_queue_stats()
        
        assert result["queue_size"] == 5
        assert result["total_processed"] == 100
        assert result["total_successful"] == 95
        assert result["total_failed"] == 5
        assert result["success_rate"] == 95.0

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_clear_queue_success(self, notification_queue, mock_redis):
        """Тест очистки очереди"""
        mock_redis.delete.return_value = 1
        
        result = await notification_queue.clear_queue()
        
        assert result["success"] is True
        assert result["deleted_count"] == 1
        mock_redis.delete.assert_called_once_with("notifications:queue")

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_clear_queue_redis_error(self, notification_queue, mock_redis):
        """Тест обработки ошибки Redis при очистке очереди"""
        mock_redis.delete.side_effect = Exception("Redis connection failed")
        
        result = await notification_queue.clear_queue()
        
        assert result["success"] is False
        assert "Redis connection failed" in result["error"]

    def test_priority_ordering(self, notification_queue):
        """Тест приоритизации уведомлений"""
        assert notification_queue._get_priority_score("HIGH") == 1
        assert notification_queue._get_priority_score("MEDIUM") == 2
        assert notification_queue._get_priority_score("LOW") == 3
        assert notification_queue._get_priority_score("UNKNOWN") == 4

    def test_notification_serialization(self, notification_queue):
        """Тест сериализации уведомления"""
        notification_data = {
            "type": "new_order",
            "telegram_id": 123456789,
            "data": {"test": "data"},
            "priority": "HIGH"
        }
        
        serialized = notification_queue._serialize_notification(notification_data)
        deserialized = notification_queue._deserialize_notification(serialized)
        
        assert deserialized["type"] == "new_order"
        assert deserialized["telegram_id"] == 123456789
        assert deserialized["data"]["test"] == "data"
        assert deserialized["priority"] == "HIGH"