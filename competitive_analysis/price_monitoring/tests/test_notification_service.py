"""
Тесты для сервиса уведомлений.

Проверяет функциональность NotificationService и всех каналов уведомлений.
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

from ..core.notification_service import (
    NotificationService,
    NotificationMessage,
    NotificationResult,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
    TelegramChannel,
    EmailChannel,
    WebhookChannel,
    ConsoleChannel,
    MessageTemplates,
    get_notification_service,
    reset_notification_service
)
from ..config.settings import NotificationConfig


class TestNotificationMessage:
    """Тесты для NotificationMessage."""
    
    def test_notification_message_creation(self):
        """Тест создания сообщения уведомления."""
        message = NotificationMessage(
            title="Test Title",
            content="Test Content",
            notification_type=NotificationType.PRICE_CHANGE,
            priority=NotificationPriority.HIGH
        )
        
        assert message.title == "Test Title"
        assert message.content == "Test Content"
        assert message.notification_type == NotificationType.PRICE_CHANGE
        assert message.priority == NotificationPriority.HIGH
        assert isinstance(message.created_at, datetime)
    
    def test_notification_message_to_dict(self):
        """Тест преобразования сообщения в словарь."""
        message = NotificationMessage(
            title="Test Title",
            content="Test Content",
            notification_type=NotificationType.PRICE_CHANGE,
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.TELEGRAM],
            metadata={"key": "value"}
        )
        
        result = message.to_dict()
        
        assert result['title'] == "Test Title"
        assert result['content'] == "Test Content"
        assert result['type'] == "price_change"
        assert result['priority'] == "high"
        assert result['channels'] == ["telegram"]
        assert result['metadata'] == {"key": "value"}
        assert 'created_at' in result


class TestNotificationResult:
    """Тесты для NotificationResult."""
    
    def test_notification_result_creation(self):
        """Тест создания результата уведомления."""
        result = NotificationResult(
            success=True,
            channel=NotificationChannel.TELEGRAM,
            message_id="test_id",
            error=None
        )
        
        assert result.success is True
        assert result.channel == NotificationChannel.TELEGRAM
        assert result.message_id == "test_id"
        assert result.error is None
        assert isinstance(result.sent_at, datetime)
    
    def test_notification_result_to_dict(self):
        """Тест преобразования результата в словарь."""
        result = NotificationResult(
            success=False,
            channel=NotificationChannel.EMAIL,
            error="Test error"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['success'] is False
        assert result_dict['channel'] == "email"
        assert result_dict['error'] == "Test error"
        assert 'sent_at' in result_dict


class TestTelegramChannel:
    """Тесты для Telegram канала."""
    
    @pytest.fixture
    def telegram_config(self):
        """Конфигурация для Telegram."""
        return NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="test_token",
            telegram_chat_ids=["123456789"]
        )
    
    @pytest.fixture
    def telegram_channel(self, telegram_config):
        """Экземпляр Telegram канала."""
        return TelegramChannel(telegram_config)
    
    def test_telegram_channel_availability(self, telegram_channel):
        """Тест проверки доступности Telegram канала."""
        assert telegram_channel.is_available() is True
    
    def test_telegram_channel_unavailable_when_disabled(self):
        """Тест недоступности канала когда он отключен."""
        config = NotificationConfig(telegram_enabled=False)
        channel = TelegramChannel(config)
        assert channel.is_available() is False
    
    def test_telegram_channel_unavailable_without_token(self):
        """Тест недоступности канала без токена."""
        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="",
            telegram_chat_ids=["123"]
        )
        channel = TelegramChannel(config)
        assert channel.is_available() is False
    
    @pytest.mark.asyncio
    async def test_telegram_send_success(self, telegram_channel):
        """Тест успешной отправки через Telegram."""
        message = NotificationMessage(
            title="Test",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'result': {'message_id': 123}
            })
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await telegram_channel.send(message)
            
            assert result.success is True
            assert result.channel == NotificationChannel.TELEGRAM
            assert result.message_id == "123"
    
    @pytest.mark.asyncio
    async def test_telegram_send_unavailable(self):
        """Тест отправки через недоступный Telegram канал."""
        config = NotificationConfig(telegram_enabled=False)
        channel = TelegramChannel(config)
        
        message = NotificationMessage(
            title="Test",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        result = await channel.send(message)
        
        assert result.success is False
        assert result.channel == NotificationChannel.TELEGRAM
        assert "not configured" in result.error
    
    def test_telegram_format_message(self, telegram_channel):
        """Тест форматирования сообщения для Telegram."""
        message = NotificationMessage(
            title="Test Title",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE,
            priority=NotificationPriority.HIGH
        )
        
        formatted = telegram_channel._format_message(message)
        
        assert "Test Title" in formatted
        assert "Test content" in formatted
        assert "⚠️" in formatted  # High priority emoji
        assert "💰" in formatted  # Price change emoji


class TestEmailChannel:
    """Тесты для Email канала."""
    
    @pytest.fixture
    def email_config(self):
        """Конфигурация для Email."""
        return NotificationConfig(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
    
    @pytest.fixture
    def email_channel(self, email_config):
        """Экземпляр Email канала."""
        return EmailChannel(email_config)
    
    def test_email_channel_availability(self, email_channel):
        """Тест проверки доступности Email канала."""
        assert email_channel.is_available() is True
    
    def test_email_channel_unavailable_when_disabled(self):
        """Тест недоступности канала когда он отключен."""
        config = NotificationConfig(email_enabled=False)
        channel = EmailChannel(config)
        assert channel.is_available() is False
    
    @pytest.mark.asyncio
    async def test_email_send_success(self, email_channel):
        """Тест успешной отправки Email."""
        message = NotificationMessage(
            title="Test",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await email_channel.send(message)
            
            assert result.success is True
            assert result.channel == NotificationChannel.EMAIL
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_send_unavailable(self):
        """Тест отправки через недоступный Email канал."""
        config = NotificationConfig(email_enabled=False)
        channel = EmailChannel(config)
        
        message = NotificationMessage(
            title="Test",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        result = await channel.send(message)
        
        assert result.success is False
        assert result.channel == NotificationChannel.EMAIL
        assert "not configured" in result.error
    
    def test_email_format_html_message(self, email_channel):
        """Тест форматирования HTML сообщения."""
        message = NotificationMessage(
            title="Test Title",
            content="Test content\nSecond line",
            notification_type=NotificationType.PRICE_CHANGE,
            priority=NotificationPriority.HIGH
        )
        
        html = email_channel._format_html_message(message)
        
        assert "Test Title" in html
        assert "Test content<br>Second line" in html
        assert "priority-high" in html
        assert "#ffc107" in html  # High priority color
    
    def test_email_format_text_message(self, email_channel):
        """Тест форматирования текстового сообщения."""
        message = NotificationMessage(
            title="Test Title",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE,
            priority=NotificationPriority.HIGH
        )
        
        text = email_channel._format_text_message(message)
        
        assert "Test Title" in text
        assert "Test content" in text
        assert "Приоритет: High" in text
        assert "Тип: Price Change" in text


class TestWebhookChannel:
    """Тесты для Webhook канала."""
    
    @pytest.fixture
    def webhook_config(self):
        """Конфигурация для Webhook."""
        return NotificationConfig(
            webhook_enabled=True,
            webhook_url="https://example.com/webhook",
            webhook_headers={"Authorization": "Bearer token"}
        )
    
    @pytest.fixture
    def webhook_channel(self, webhook_config):
        """Экземпляр Webhook канала."""
        return WebhookChannel(webhook_config)
    
    def test_webhook_channel_availability(self, webhook_channel):
        """Тест проверки доступности Webhook канала."""
        assert webhook_channel.is_available() is True
    
    def test_webhook_channel_unavailable_when_disabled(self):
        """Тест недоступности канала когда он отключен."""
        config = NotificationConfig(webhook_enabled=False)
        channel = WebhookChannel(config)
        assert channel.is_available() is False
    
    @pytest.mark.asyncio
    async def test_webhook_send_success(self, webhook_channel):
        """Тест успешной отправки через Webhook."""
        message = NotificationMessage(
            title="Test",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await webhook_channel.send(message)
            
            assert result.success is True
            assert result.channel == NotificationChannel.WEBHOOK
    
    @pytest.mark.asyncio
    async def test_webhook_send_error(self, webhook_channel):
        """Тест ошибки отправки через Webhook."""
        message = NotificationMessage(
            title="Test",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await webhook_channel.send(message)
            
            assert result.success is False
            assert result.channel == NotificationChannel.WEBHOOK
            assert "HTTP 500" in result.error


class TestConsoleChannel:
    """Тесты для Console канала."""
    
    @pytest.fixture
    def console_channel(self):
        """Экземпляр Console канала."""
        config = NotificationConfig()
        return ConsoleChannel(config)
    
    def test_console_channel_availability(self, console_channel):
        """Тест проверки доступности Console канала."""
        assert console_channel.is_available() is True
    
    @pytest.mark.asyncio
    async def test_console_send_success(self, console_channel, capsys):
        """Тест успешной отправки в консоль."""
        message = NotificationMessage(
            title="Test Title",
            content="Test content",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        result = await console_channel.send(message)
        
        assert result.success is True
        assert result.channel == NotificationChannel.CONSOLE
        
        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "Test content" in captured.out


class TestMessageTemplates:
    """Тесты для шаблонов сообщений."""
    
    @pytest.fixture
    def templates(self):
        """Экземпляр MessageTemplates."""
        return MessageTemplates()
    
    def test_create_price_change_message(self, templates):
        """Тест создания сообщения об изменении цены."""
        message = templates.create_price_change_message(
            product_name="Test Product",
            old_price=100.0,
            new_price=120.0,
            change_percent=20.0,
            competitor_name="Test Competitor"
        )
        
        assert message.title == "Изменение цены: Test Product"
        assert "Test Product" in message.content
        assert "100.00" in message.content
        assert "120.00" in message.content
        assert "+20.0%" in message.content
        assert "Test Competitor" in message.content
        assert message.notification_type == NotificationType.PRICE_CHANGE
        assert message.priority == NotificationPriority.CRITICAL  # 20% change
    
    def test_create_price_change_message_priority(self, templates):
        """Тест определения приоритета для изменения цены."""
        # Критическое изменение (>= 20%)
        message_critical = templates.create_price_change_message(
            "Product", 100.0, 125.0, 25.0
        )
        assert message_critical.priority == NotificationPriority.CRITICAL
        
        # Высокий приоритет (>= 10%)
        message_high = templates.create_price_change_message(
            "Product", 100.0, 115.0, 15.0
        )
        assert message_high.priority == NotificationPriority.HIGH
        
        # Обычный приоритет (< 10%)
        message_normal = templates.create_price_change_message(
            "Product", 100.0, 105.0, 5.0
        )
        assert message_normal.priority == NotificationPriority.NORMAL
    
    def test_create_competitor_analysis_message(self, templates):
        """Тест создания сообщения анализа конкурентов."""
        analysis_data = {
            'competitors_count': 5,
            'average_price': 150.0,
            'min_price': 120.0,
            'max_price': 180.0,
            'market_position': 'средняя',
            'recommendations': 'Снизить цену на 10%'
        }
        
        message = templates.create_competitor_analysis_message(
            "Test Product",
            analysis_data
        )
        
        assert message.title == "Анализ конкурентов: Test Product"
        assert "Test Product" in message.content
        assert "5" in message.content  # competitors_count
        assert "150.00" in message.content  # average_price
        assert "средняя" in message.content  # market_position
        assert "Снизить цену" in message.content  # recommendations
        assert message.notification_type == NotificationType.COMPETITOR_ANALYSIS
        assert message.priority == NotificationPriority.NORMAL
    
    def test_create_system_error_message(self, templates):
        """Тест создания сообщения системной ошибки."""
        error_details = {
            'timestamp': '2024-01-01 12:00:00',
            'component': 'price_monitor',
            'traceback': 'Traceback (most recent call last):\n  File "test.py", line 1, in <module>\n    raise Exception("Test error")\nException: Test error'
        }
        
        message = templates.create_system_error_message(
            "Test error occurred",
            error_details
        )
        
        assert message.title == "Системная ошибка"
        assert "Test error occurred" in message.content
        assert "2024-01-01 12:00:00" in message.content
        assert "price_monitor" in message.content
        assert "Traceback" in message.content
        assert message.notification_type == NotificationType.SYSTEM_ERROR
        assert message.priority == NotificationPriority.CRITICAL


class TestNotificationService:
    """Тесты для основного сервиса уведомлений."""
    
    @pytest.fixture
    def notification_config(self):
        """Конфигурация уведомлений для тестов."""
        return NotificationConfig(
            enabled=True,
            telegram_enabled=True,
            telegram_bot_token="test_token",
            telegram_chat_ids=["123456789"],
            email_enabled=False,
            webhook_enabled=False,
            batch_notifications=True,
            notification_cooldown_minutes=60
        )
    
    @pytest.fixture
    def notification_service(self, notification_config):
        """Экземпляр NotificationService."""
        return NotificationService(notification_config)
    
    def test_notification_service_initialization(self, notification_service):
        """Тест инициализации сервиса уведомлений."""
        assert notification_service.config.enabled is True
        assert len(notification_service.channels) == 4  # All channel types
        assert isinstance(notification_service.message_templates, MessageTemplates)
    
    def test_get_default_channels(self, notification_service):
        """Тест получения каналов по умолчанию."""
        channels = notification_service._get_default_channels()
        assert NotificationChannel.TELEGRAM in channels
        assert NotificationChannel.EMAIL not in channels  # Disabled
        assert NotificationChannel.WEBHOOK not in channels  # Disabled
    
    def test_is_in_cooldown(self, notification_service):
        """Тест проверки cooldown."""
        message = NotificationMessage(
            title="Test",
            content="Test",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        # Первый раз - не в cooldown
        assert notification_service._is_in_cooldown(message) is False
        
        # Обновляем кэш
        notification_service._update_cache(message)
        
        # Теперь в cooldown
        assert notification_service._is_in_cooldown(message) is True
    
    def test_update_cache(self, notification_service):
        """Тест обновления кэша."""
        message = NotificationMessage(
            title="Test",
            content="Test",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        initial_cache_size = len(notification_service._notification_cache)
        notification_service._update_cache(message)
        
        assert len(notification_service._notification_cache) == initial_cache_size + 1
    
    @pytest.mark.asyncio
    async def test_send_notification_disabled(self):
        """Тест отправки уведомления когда сервис отключен."""
        config = NotificationConfig(enabled=False)
        service = NotificationService(config)
        
        message = NotificationMessage(
            title="Test",
            content="Test",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        results = await service.send_notification(message)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_send_notification_in_cooldown(self, notification_service):
        """Тест отправки уведомления в cooldown."""
        message = NotificationMessage(
            title="Test",
            content="Test",
            notification_type=NotificationType.PRICE_CHANGE
        )
        
        # Добавляем в кэш
        notification_service._update_cache(message)
        
        results = await service.send_notification(message)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_send_price_change_notification(self, notification_service):
        """Тест отправки уведомления об изменении цены."""
        with patch.object(notification_service, 'send_notification', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = [NotificationResult(
                success=True,
                channel=NotificationChannel.TELEGRAM
            )]
            
            results = await notification_service.send_price_change_notification(
                product_name="Test Product",
                old_price=100.0,
                new_price=120.0,
                change_percent=20.0
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]
            
            assert message.notification_type == NotificationType.PRICE_CHANGE
            assert "Test Product" in message.title
    
    @pytest.mark.asyncio
    async def test_send_competitor_analysis_notification(self, notification_service):
        """Тест отправки уведомления анализа конкурентов."""
        with patch.object(notification_service, 'send_notification', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = [NotificationResult(
                success=True,
                channel=NotificationChannel.TELEGRAM
            )]
            
            analysis_data = {'competitors_count': 5}
            
            results = await notification_service.send_competitor_analysis_notification(
                product_name="Test Product",
                analysis_data=analysis_data
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]
            
            assert message.notification_type == NotificationType.COMPETITOR_ANALYSIS
            assert "Test Product" in message.title
    
    @pytest.mark.asyncio
    async def test_send_system_error_notification(self, notification_service):
        """Тест отправки уведомления системной ошибки."""
        with patch.object(notification_service, 'send_notification', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = [NotificationResult(
                success=True,
                channel=NotificationChannel.TELEGRAM
            )]
            
            results = await notification_service.send_system_error_notification(
                error_message="Test error",
                error_details={'component': 'test'}
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]
            
            assert message.notification_type == NotificationType.SYSTEM_ERROR
            assert message.priority == NotificationPriority.CRITICAL


class TestGlobalNotificationService:
    """Тесты для глобального экземпляра сервиса."""
    
    def test_get_notification_service(self):
        """Тест получения глобального экземпляра."""
        reset_notification_service()  # Сброс перед тестом
        
        service1 = get_notification_service()
        service2 = get_notification_service()
        
        assert service1 is service2  # Должен быть один экземпляр
        assert isinstance(service1, NotificationService)
    
    def test_reset_notification_service(self):
        """Тест сброса глобального экземпляра."""
        service1 = get_notification_service()
        reset_notification_service()
        service2 = get_notification_service()
        
        assert service1 is not service2  # Должны быть разные экземпляры
    
    def test_get_notification_service_with_config(self):
        """Тест получения сервиса с кастомной конфигурацией."""
        reset_notification_service()
        
        config = NotificationConfig(enabled=False)
        service = get_notification_service(config)
        
        assert service.config.enabled is False


@pytest.mark.asyncio
async def test_integration_notification_flow():
    """Интеграционный тест полного потока уведомлений."""
    config = NotificationConfig(
        enabled=True,
        telegram_enabled=False,  # Отключаем для теста
        email_enabled=False,
        webhook_enabled=False
    )
    
    service = NotificationService(config)
    
    message = NotificationMessage(
        title="Integration Test",
        content="Test content",
        notification_type=NotificationType.PRICE_CHANGE,
        channels=[NotificationChannel.CONSOLE]  # Используем консоль
    )
    
    results = await service.send_notification(message)
    
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].channel == NotificationChannel.CONSOLE


if __name__ == "__main__":
    pytest.main([__file__])