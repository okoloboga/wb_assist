"""
Сервис уведомлений для модуля мониторинга цен.

Обеспечивает отправку уведомлений через различные каналы:
- Telegram Bot
- Email (SMTP)
- Webhook
- Консольный вывод (для отладки)
"""

import asyncio
import json
import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
from urllib.parse import urljoin
import aiohttp
import requests
from jinja2 import Template

from ..config.settings import NotificationConfig, get_settings
from .exceptions import NotificationError


logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Типы каналов уведомлений."""
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"


class NotificationPriority(Enum):
    """Приоритеты уведомлений."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(Enum):
    """Типы уведомлений."""
    PRICE_CHANGE = "price_change"
    PRICE_ALERT = "price_alert"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    SYSTEM_ERROR = "system_error"
    MONITORING_REPORT = "monitoring_report"
    MARKET_INSIGHT = "market_insight"


@dataclass
class NotificationMessage:
    """Сообщение для отправки уведомления."""
    
    title: str
    content: str
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[NotificationChannel] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'title': self.title,
            'content': self.content,
            'type': self.notification_type.value,
            'priority': self.priority.value,
            'channels': [ch.value for ch in self.channels],
            'metadata': self.metadata,
            'template_data': self.template_data,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class NotificationResult:
    """Результат отправки уведомления."""
    
    success: bool
    channel: NotificationChannel
    message_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'success': self.success,
            'channel': self.channel.value,
            'message_id': self.message_id,
            'error': self.error,
            'sent_at': self.sent_at.isoformat()
        }


class NotificationChannel_ABC(ABC):
    """Абстрактный базовый класс для каналов уведомлений."""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Отправить уведомление через канал."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Проверить доступность канала."""
        pass


class TelegramChannel(NotificationChannel_ABC):
    """Канал уведомлений через Telegram Bot."""
    
    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.bot_token = config.telegram_bot_token
        self.chat_ids = config.telegram_chat_ids
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def is_available(self) -> bool:
        """Проверить доступность Telegram канала."""
        return (
            self.config.telegram_enabled and 
            bool(self.bot_token) and 
            bool(self.chat_ids)
        )
    
    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Отправить уведомление в Telegram."""
        if not self.is_available():
            return NotificationResult(
                success=False,
                channel=NotificationChannel.TELEGRAM,
                error="Telegram channel not configured or disabled"
            )
        
        try:
            # Форматируем сообщение для Telegram
            text = self._format_message(message)
            
            # Отправляем во все чаты
            results = []
            async with aiohttp.ClientSession() as session:
                for chat_id in self.chat_ids:
                    result = await self._send_to_chat(session, chat_id, text, message)
                    results.append(result)
            
            # Возвращаем результат (успешно если хотя бы одно сообщение отправлено)
            success = any(r.success for r in results)
            errors = [r.error for r in results if r.error]
            
            return NotificationResult(
                success=success,
                channel=NotificationChannel.TELEGRAM,
                message_id=f"telegram_{datetime.now().timestamp()}",
                error="; ".join(errors) if errors else None
            )
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}")
            return NotificationResult(
                success=False,
                channel=NotificationChannel.TELEGRAM,
                error=str(e)
            )
    
    async def _send_to_chat(self, session: aiohttp.ClientSession, chat_id: str, 
                           text: str, message: NotificationMessage) -> NotificationResult:
        """Отправить сообщение в конкретный чат."""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return NotificationResult(
                        success=True,
                        channel=NotificationChannel.TELEGRAM,
                        message_id=str(result.get('result', {}).get('message_id'))
                    )
                else:
                    error_text = await response.text()
                    return NotificationResult(
                        success=False,
                        channel=NotificationChannel.TELEGRAM,
                        error=f"HTTP {response.status}: {error_text}"
                    )
                    
        except Exception as e:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.TELEGRAM,
                error=str(e)
            )
    
    def _format_message(self, message: NotificationMessage) -> str:
        """Форматировать сообщение для Telegram."""
        priority_emoji = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.NORMAL: "📢",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.CRITICAL: "🚨"
        }
        
        type_emoji = {
            NotificationType.PRICE_CHANGE: "💰",
            NotificationType.PRICE_ALERT: "🔔",
            NotificationType.COMPETITOR_ANALYSIS: "📊",
            NotificationType.SYSTEM_ERROR: "❌",
            NotificationType.MONITORING_REPORT: "📈",
            NotificationType.MARKET_INSIGHT: "💡"
        }
        
        emoji = f"{priority_emoji.get(message.priority, '📢')} {type_emoji.get(message.notification_type, '📢')}"
        
        text = f"{emoji} <b>{message.title}</b>\n\n"
        text += f"{message.content}\n\n"
        text += f"<i>Время: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}</i>"
        
        return text


class EmailChannel(NotificationChannel_ABC):
    """Канал уведомлений через Email."""
    
    def is_available(self) -> bool:
        """Проверить доступность Email канала."""
        return (
            self.config.email_enabled and
            bool(self.config.email_from) and
            bool(self.config.email_password) and
            bool(self.config.email_to)
        )
    
    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Отправить уведомление по Email."""
        if not self.is_available():
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error="Email channel not configured or disabled"
            )
        
        try:
            # Создаем сообщение
            msg = MimeMultipart('alternative')
            msg['Subject'] = f"[{message.priority.value.upper()}] {message.title}"
            msg['From'] = self.config.email_from
            msg['To'] = ', '.join(self.config.email_to)
            
            # HTML версия
            html_content = self._format_html_message(message)
            html_part = MimeText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Текстовая версия
            text_content = self._format_text_message(message)
            text_part = MimeText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Отправляем
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email_from, self.config.email_password)
                server.send_message(msg)
            
            return NotificationResult(
                success=True,
                channel=NotificationChannel.EMAIL,
                message_id=f"email_{datetime.now().timestamp()}"
            )
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error=str(e)
            )
    
    def _format_html_message(self, message: NotificationMessage) -> str:
        """Форматировать HTML сообщение."""
        template = Template("""
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
                .content { margin: 20px 0; }
                .footer { font-size: 12px; color: #666; margin-top: 20px; }
                .priority-{{ priority }} { border-left: 4px solid {{ priority_color }}; padding-left: 10px; }
            </style>
        </head>
        <body>
            <div class="header priority-{{ priority }}">
                <h2>{{ title }}</h2>
                <p><strong>Тип:</strong> {{ type_name }} | <strong>Приоритет:</strong> {{ priority_name }}</p>
            </div>
            <div class="content">
                {{ content | safe }}
            </div>
            <div class="footer">
                <p>Отправлено: {{ created_at }}</p>
            </div>
        </body>
        </html>
        """)
        
        priority_colors = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.NORMAL: "#007bff",
            NotificationPriority.HIGH: "#ffc107",
            NotificationPriority.CRITICAL: "#dc3545"
        }
        
        return template.render(
            title=message.title,
            content=message.content.replace('\n', '<br>'),
            priority=message.priority.value,
            priority_name=message.priority.value.title(),
            priority_color=priority_colors.get(message.priority, "#007bff"),
            type_name=message.notification_type.value.replace('_', ' ').title(),
            created_at=message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def _format_text_message(self, message: NotificationMessage) -> str:
        """Форматировать текстовое сообщение."""
        text = f"{message.title}\n"
        text += "=" * len(message.title) + "\n\n"
        text += f"Тип: {message.notification_type.value.replace('_', ' ').title()}\n"
        text += f"Приоритет: {message.priority.value.title()}\n\n"
        text += f"{message.content}\n\n"
        text += f"Отправлено: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        return text


class WebhookChannel(NotificationChannel_ABC):
    """Канал уведомлений через Webhook."""
    
    def is_available(self) -> bool:
        """Проверить доступность Webhook канала."""
        return self.config.webhook_enabled and bool(self.config.webhook_url)
    
    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Отправить уведомление через Webhook."""
        if not self.is_available():
            return NotificationResult(
                success=False,
                channel=NotificationChannel.WEBHOOK,
                error="Webhook channel not configured or disabled"
            )
        
        try:
            payload = {
                'notification': message.to_dict(),
                'timestamp': datetime.now().isoformat(),
                'source': 'price_monitoring_system'
            }
            
            headers = {
                'Content-Type': 'application/json',
                **self.config.webhook_headers
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status < 400:
                        return NotificationResult(
                            success=True,
                            channel=NotificationChannel.WEBHOOK,
                            message_id=f"webhook_{datetime.now().timestamp()}"
                        )
                    else:
                        error_text = await response.text()
                        return NotificationResult(
                            success=False,
                            channel=NotificationChannel.WEBHOOK,
                            error=f"HTTP {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")
            return NotificationResult(
                success=False,
                channel=NotificationChannel.WEBHOOK,
                error=str(e)
            )


class ConsoleChannel(NotificationChannel_ABC):
    """Канал уведомлений в консоль (для отладки)."""
    
    def is_available(self) -> bool:
        """Консольный канал всегда доступен."""
        return True
    
    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Вывести уведомление в консоль."""
        try:
            print(f"\n{'='*60}")
            print(f"NOTIFICATION: {message.title}")
            print(f"Type: {message.notification_type.value}")
            print(f"Priority: {message.priority.value}")
            print(f"Time: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            print(message.content)
            print(f"{'='*60}\n")
            
            return NotificationResult(
                success=True,
                channel=NotificationChannel.CONSOLE,
                message_id=f"console_{datetime.now().timestamp()}"
            )
            
        except Exception as e:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.CONSOLE,
                error=str(e)
            )


class NotificationService:
    """Основной сервис уведомлений."""
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        """Инициализация сервиса уведомлений."""
        self.config = config or get_settings().notification
        self.logger = logging.getLogger(__name__)
        
        # Инициализируем каналы
        self.channels: Dict[NotificationChannel, NotificationChannel_ABC] = {
            NotificationChannel.TELEGRAM: TelegramChannel(self.config),
            NotificationChannel.EMAIL: EmailChannel(self.config),
            NotificationChannel.WEBHOOK: WebhookChannel(self.config),
            NotificationChannel.CONSOLE: ConsoleChannel(self.config)
        }
        
        # Кэш для предотвращения спама
        self._notification_cache: Dict[str, datetime] = {}
        
        # Шаблоны сообщений
        self.message_templates = MessageTemplates()
    
    async def send_notification(
        self, 
        message: NotificationMessage,
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[NotificationResult]:
        """
        Отправить уведомление через указанные каналы.
        
        Args:
            message: Сообщение для отправки
            channels: Список каналов (если не указан, используются каналы из сообщения)
            
        Returns:
            Список результатов отправки
        """
        if not self.config.enabled:
            self.logger.info("Notifications are disabled")
            return []
        
        # Определяем каналы для отправки
        target_channels = channels or message.channels
        if not target_channels:
            target_channels = self._get_default_channels()
        
        # Проверяем cooldown
        if self._is_in_cooldown(message):
            self.logger.info(f"Notification in cooldown: {message.title}")
            return []
        
        # Отправляем через все доступные каналы
        results = []
        for channel_type in target_channels:
            channel = self.channels.get(channel_type)
            if channel and channel.is_available():
                try:
                    result = await channel.send(message)
                    results.append(result)
                    
                    if result.success:
                        self.logger.info(f"Notification sent via {channel_type.value}: {message.title}")
                    else:
                        self.logger.error(f"Failed to send via {channel_type.value}: {result.error}")
                        
                except Exception as e:
                    self.logger.error(f"Error sending via {channel_type.value}: {e}")
                    results.append(NotificationResult(
                        success=False,
                        channel=channel_type,
                        error=str(e)
                    ))
            else:
                self.logger.warning(f"Channel {channel_type.value} not available")
        
        # Обновляем кэш
        self._update_cache(message)
        
        return results
    
    def _get_default_channels(self) -> List[NotificationChannel]:
        """Получить список каналов по умолчанию."""
        channels = []
        if self.config.telegram_enabled:
            channels.append(NotificationChannel.TELEGRAM)
        if self.config.email_enabled:
            channels.append(NotificationChannel.EMAIL)
        if self.config.webhook_enabled:
            channels.append(NotificationChannel.WEBHOOK)
        
        # Если ничего не настроено, используем консоль
        if not channels:
            channels.append(NotificationChannel.CONSOLE)
            
        return channels
    
    def _is_in_cooldown(self, message: NotificationMessage) -> bool:
        """Проверить, находится ли уведомление в периоде cooldown."""
        if not self.config.batch_notifications:
            return False
        
        cache_key = f"{message.notification_type.value}_{hash(message.title)}"
        last_sent = self._notification_cache.get(cache_key)
        
        if last_sent:
            cooldown_period = timedelta(minutes=self.config.notification_cooldown_minutes)
            return datetime.now() - last_sent < cooldown_period
        
        return False
    
    def _update_cache(self, message: NotificationMessage) -> None:
        """Обновить кэш уведомлений."""
        cache_key = f"{message.notification_type.value}_{hash(message.title)}"
        self._notification_cache[cache_key] = datetime.now()
        
        # Очищаем старые записи
        cutoff_time = datetime.now() - timedelta(hours=24)
        self._notification_cache = {
            k: v for k, v in self._notification_cache.items() 
            if v > cutoff_time
        }
    
    async def send_price_change_notification(
        self,
        product_name: str,
        old_price: float,
        new_price: float,
        change_percent: float,
        competitor_name: str = "",
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[NotificationResult]:
        """Отправить уведомление об изменении цены."""
        message = self.message_templates.create_price_change_message(
            product_name=product_name,
            old_price=old_price,
            new_price=new_price,
            change_percent=change_percent,
            competitor_name=competitor_name
        )
        
        return await self.send_notification(message, channels)
    
    async def send_competitor_analysis_notification(
        self,
        product_name: str,
        analysis_data: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[NotificationResult]:
        """Отправить уведомление о результатах анализа конкурентов."""
        message = self.message_templates.create_competitor_analysis_message(
            product_name=product_name,
            analysis_data=analysis_data
        )
        
        return await self.send_notification(message, channels)
    
    async def send_system_error_notification(
        self,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[NotificationResult]:
        """Отправить уведомление о системной ошибке."""
        message = self.message_templates.create_system_error_message(
            error_message=error_message,
            error_details=error_details or {}
        )
        
        return await self.send_notification(message, channels)


class MessageTemplates:
    """Шаблоны сообщений для различных типов уведомлений."""
    
    def create_price_change_message(
        self,
        product_name: str,
        old_price: float,
        new_price: float,
        change_percent: float,
        competitor_name: str = ""
    ) -> NotificationMessage:
        """Создать сообщение об изменении цены."""
        change_direction = "увеличилась" if new_price > old_price else "уменьшилась"
        change_emoji = "📈" if new_price > old_price else "📉"
        
        title = f"Изменение цены: {product_name}"
        
        content = f"{change_emoji} Цена товара '{product_name}' {change_direction}\n\n"
        content += f"Старая цена: {old_price:.2f} ₽\n"
        content += f"Новая цена: {new_price:.2f} ₽\n"
        content += f"Изменение: {change_percent:+.1f}%\n"
        
        if competitor_name:
            content += f"Конкурент: {competitor_name}\n"
        
        # Определяем приоритет по размеру изменения
        if abs(change_percent) >= 20:
            priority = NotificationPriority.CRITICAL
        elif abs(change_percent) >= 10:
            priority = NotificationPriority.HIGH
        else:
            priority = NotificationPriority.NORMAL
        
        return NotificationMessage(
            title=title,
            content=content,
            notification_type=NotificationType.PRICE_CHANGE,
            priority=priority,
            template_data={
                'product_name': product_name,
                'old_price': old_price,
                'new_price': new_price,
                'change_percent': change_percent,
                'competitor_name': competitor_name
            }
        )
    
    def create_competitor_analysis_message(
        self,
        product_name: str,
        analysis_data: Dict[str, Any]
    ) -> NotificationMessage:
        """Создать сообщение о результатах анализа конкурентов."""
        title = f"Анализ конкурентов: {product_name}"
        
        content = f"📊 Завершен анализ конкурентов для товара '{product_name}'\n\n"
        
        if 'competitors_count' in analysis_data:
            content += f"Найдено конкурентов: {analysis_data['competitors_count']}\n"
        
        if 'average_price' in analysis_data:
            content += f"Средняя цена: {analysis_data['average_price']:.2f} ₽\n"
        
        if 'min_price' in analysis_data:
            content += f"Минимальная цена: {analysis_data['min_price']:.2f} ₽\n"
        
        if 'max_price' in analysis_data:
            content += f"Максимальная цена: {analysis_data['max_price']:.2f} ₽\n"
        
        if 'market_position' in analysis_data:
            content += f"Позиция на рынке: {analysis_data['market_position']}\n"
        
        if 'recommendations' in analysis_data:
            content += f"\n💡 Рекомендации:\n{analysis_data['recommendations']}"
        
        return NotificationMessage(
            title=title,
            content=content,
            notification_type=NotificationType.COMPETITOR_ANALYSIS,
            priority=NotificationPriority.NORMAL,
            template_data=analysis_data
        )
    
    def create_system_error_message(
        self,
        error_message: str,
        error_details: Dict[str, Any]
    ) -> NotificationMessage:
        """Создать сообщение о системной ошибке."""
        title = "Системная ошибка"
        
        content = f"❌ Произошла ошибка в системе мониторинга цен\n\n"
        content += f"Ошибка: {error_message}\n"
        
        if 'timestamp' in error_details:
            content += f"Время: {error_details['timestamp']}\n"
        
        if 'component' in error_details:
            content += f"Компонент: {error_details['component']}\n"
        
        if 'traceback' in error_details:
            content += f"\nДетали:\n{error_details['traceback'][:500]}..."
        
        return NotificationMessage(
            title=title,
            content=content,
            notification_type=NotificationType.SYSTEM_ERROR,
            priority=NotificationPriority.CRITICAL,
            template_data=error_details
        )


# Глобальный экземпляр сервиса
_notification_service: Optional[NotificationService] = None


def get_notification_service(config: Optional[NotificationConfig] = None) -> NotificationService:
    """Получить глобальный экземпляр сервиса уведомлений."""
    global _notification_service
    
    if _notification_service is None:
        _notification_service = NotificationService(config)
    
    return _notification_service


def reset_notification_service() -> None:
    """Сбросить глобальный экземпляр сервиса."""
    global _notification_service
    _notification_service = None