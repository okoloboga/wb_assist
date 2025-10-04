"""
Тесты защиты от зависания в реальном коде
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.features.bot_api.webhook import WebhookSender, NotificationQueue


class TestHangingProtection:
    """Тесты защиты от зависания"""

    @pytest.fixture
    def webhook_sender(self):
        """Фикстура для webhook sender"""
        return WebhookSender()

    @pytest.fixture
    def mock_redis(self):
        """Фикстура для мока Redis"""
        return AsyncMock()

    @pytest.fixture
    def notification_queue(self, mock_redis):
        """Фикстура для очереди уведомлений"""
        return NotificationQueue(mock_redis)

    @pytest.mark.asyncio
    async def test_process_notifications_max_processing_time(self, notification_queue, mock_redis):
        """Тест защиты от превышения максимального времени обработки"""
        # Мокаем brpop чтобы он всегда возвращал данные
        mock_redis.brpop.return_value = ("notifications:queue", '{"id": "test"}')
        
        # Мокаем _process_single_notification чтобы он работал медленно
        with patch.object(notification_queue, '_process_single_notification') as mock_process:
            async def slow_process(notification):
                await asyncio.sleep(2)  # Медленная обработка
                return {"success": True}
            
            mock_process.side_effect = slow_process
            
            # Запускаем с очень коротким max_processing_time
            result = await notification_queue.process_notifications(
                max_items=10, 
                timeout=1, 
                max_processing_time=3  # 3 секунды максимум
            )
            
            # Должен обработать только несколько элементов до таймаута
            assert result["processed"] < 10
            assert result["processed"] > 0

    @pytest.mark.asyncio
    async def test_process_notifications_single_notification_timeout(self, notification_queue, mock_redis):
        """Тест таймаута обработки одного уведомления"""
        mock_redis.brpop.return_value = ("notifications:queue", '{"id": "test"}')
        
        with patch.object(notification_queue, '_process_single_notification') as mock_process:
            async def very_slow_process(notification):
                await asyncio.sleep(10)  # Очень медленная обработка
                return {"success": True}
            
            mock_process.side_effect = very_slow_process
            
            result = await notification_queue.process_notifications(
                max_items=1, 
                timeout=1, 
                max_processing_time=30
            )
            
            # Должен обработать 1 элемент, но с ошибкой таймаута
            assert result["processed"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_webhook_sender_timeout_protection(self, webhook_sender):
        """Тест защиты от зависания в WebhookSender"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Мокаем очень медленный ответ
            async def slow_response():
                await asyncio.sleep(15)  # Медленнее чем timeout
                mock_response = AsyncMock()
                mock_response.status = 200
                return mock_response
            
            # Правильно мокаем async context manager
            mock_post.return_value.__aenter__ = slow_response
            
            result = await webhook_sender._send_notification(
                payload={"test": "data"},
                bot_webhook_url="http://test.com/webhook"
            )
            
            # Должен завершиться с ошибкой таймаута
            assert result["success"] is False
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_redis_brpop_timeout_protection(self, notification_queue, mock_redis):
        """Тест защиты от зависания brpop"""
        # Мокаем brpop чтобы он не возвращал результат (зависание)
        async def hanging_brpop(key, timeout):
            await asyncio.sleep(20)  # Долго не возвращает результат
            return None
        
        mock_redis.brpop.side_effect = hanging_brpop
        
        result = await notification_queue.process_notifications(
            max_items=1, 
            timeout=1, 
            max_processing_time=5
        )
        
        # Должен завершиться по таймауту
        assert result["processed"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_empty_result_handling(self, notification_queue, mock_redis):
        """Тест обработки пустых результатов от Redis"""
        # Мокаем brpop чтобы он возвращал пустой результат
        mock_redis.brpop.return_value = None
        
        result = await notification_queue.process_notifications(
            max_items=5, 
            timeout=1, 
            max_processing_time=10
        )
        
        # Должен корректно завершиться
        assert result["processed"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self, notification_queue, mock_redis):
        """Тест обработки некорректного JSON от Redis"""
        # Мокаем brpop чтобы он возвращал некорректный JSON
        mock_redis.brpop.return_value = ("notifications:queue", "invalid json")
        
        result = await notification_queue.process_notifications(
            max_items=1, 
            timeout=1, 
            max_processing_time=10
        )
        
        # Должен обработать с ошибкой
        assert result["processed"] == 1
        assert result["successful"] == 0
        assert result["failed"] == 1