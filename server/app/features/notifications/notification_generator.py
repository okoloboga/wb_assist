"""
Notification Generator для системы уведомлений S3
Генерация уведомлений на основе событий
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.utils.timezone import TimezoneUtils


class NotificationGenerator:
    """Генератор уведомлений на основе событий"""
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """Форматировать валюту с пробелами вместо запятых"""
        return f"{amount:,.0f}₽".replace(",", " ")
    
    def generate_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Генерация уведомления на основе события и настроек пользователя"""
        # Проверяем, включены ли уведомления вообще
        if not user_settings.get("notifications_enabled", True):
            return None
        
        # Проверяем, включен ли конкретный тип уведомления
        event_type = event_data.get("type")
        if not self._is_notification_type_enabled(event_type, user_settings):
            return None
        
        # Генерируем уведомление в зависимости от типа события
        if event_type == "negative_review":
            return self._generate_negative_review_notification(event_data, user_settings)
        elif event_type == "critical_stocks":
            return self._generate_critical_stocks_notification(event_data, user_settings)
        # Для заказов (new_order, order_buyout, order_cancellation, order_return) 
        # используется детальный формат в NotificationService
        
        return None
    
    def _is_notification_type_enabled(self, event_type: str, user_settings: Dict[str, Any]) -> bool:
        """Проверка, включен ли тип уведомления"""
        type_mapping = {
            "new_order": "new_orders_enabled",
            "order_buyout": "order_buyouts_enabled",
            "order_cancellation": "order_cancellations_enabled",
            "order_return": "order_returns_enabled",
            "negative_review": "negative_reviews_enabled",
            "critical_stocks": "critical_stocks_enabled"
        }
        
        setting_key = type_mapping.get(event_type)
        if not setting_key:
            return False
        
        return user_settings.get(setting_key, True)
    
    
    def _generate_negative_review_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о негативном отзыве"""
        review_id = event_data.get("review_id", "N/A")
        rating = event_data.get("rating", 0)
        text = event_data.get("text", "")
        product_name = event_data.get("product_name", "Неизвестный товар")
        order_id = event_data.get("order_id")
        
        title = f"😞 Негативный отзыв #{review_id}"
        content = self._format_negative_review_content(review_id, rating, text, product_name, order_id)
        
        return {
            "type": "negative_review",
            "user_id": event_data.get("user_id"),
            "review_id": review_id,
            "rating": rating,
            "title": title,
            "content": content,
            "priority": "CRITICAL",
            "grouping_enabled": user_settings.get("grouping_enabled", True),
            "max_group_size": user_settings.get("max_group_size", 5),
            "group_timeout": user_settings.get("group_timeout", 300),
            "generated_at": TimezoneUtils.format_for_user(TimezoneUtils.now_msk())
        }
    
    def _generate_critical_stocks_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о критичных остатках"""
        nm_id = event_data.get("nm_id", "N/A")
        # Надежный fallback для названия товара
        name = (
            event_data.get("name")
            or event_data.get("product_name")
            or event_data.get("title")
            or f"Товар {nm_id}"
        )
        critical_sizes = event_data.get("critical_sizes", [])
        zero_sizes = event_data.get("zero_sizes", [])
        
        title = f"⚠️ Критичные остатки #{nm_id}"
        content = self._format_critical_stocks_content(nm_id, name, critical_sizes, zero_sizes)
        
        return {
            "type": "critical_stocks",
            "user_id": event_data.get("user_id"),
            "nm_id": nm_id,
            "title": title,
            "content": content,
            "priority": "HIGH",
            "grouping_enabled": user_settings.get("grouping_enabled", True),
            "max_group_size": user_settings.get("max_group_size", 5),
            "group_timeout": user_settings.get("group_timeout", 300),
            "generated_at": TimezoneUtils.format_for_user(TimezoneUtils.now_msk())
        }
    
    
    def _format_negative_review_content(self, review_id: int, rating: int, text: str, product_name: str, order_id: Optional[int]) -> str:
        """Форматирование контента уведомления о негативном отзыве"""
        order_info = f"Заказ: #{order_id}" if order_id else "Заказ: неизвестен"
        
        return f"""😞 НЕГАТИВНЫЙ ОТЗЫВ

📦 Товар: {product_name}
⭐ Рейтинг: {rating}/5
💬 Текст: "{text[:100]}{'...' if len(text) > 100 else ''}"
👤 Автор: {review_id}
🆔 ID отзыва: {review_id}

⚠️ Рекомендуется ответить на отзыв или связаться с покупателем"""
    
    def _format_critical_stocks_content(self, nm_id: int, name: str, critical_sizes: list, zero_sizes: list) -> str:
        """Форматирование контента уведомления о критичных остатках"""
        critical_info = f"Критичные размеры: {', '.join(critical_sizes)}" if critical_sizes else "Нет критичных размеров"
        zero_info = f"Нулевые размеры: {', '.join(zero_sizes)}" if zero_sizes else "Нет нулевых размеров"
        
        return f"""⚠️ КРИТИЧНЫЕ ОСТАТКИ

📦 {name}
🆔 {nm_id}
📊 Остатки: {critical_info}
⚠️ Критично: {zero_info}"""
    
    def generate_sales_notification(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о продаже/возврате"""
        notification_type = event["type"]
        
        if notification_type == "new_buyout":
            return self._generate_new_buyout_notification(event)
        elif notification_type == "new_return":
            return self._generate_new_return_notification(event)
        elif notification_type == "sale_status_change":
            return self._generate_sale_status_change_notification(event)
        elif notification_type == "sale_cancellation_change":
            return self._generate_sale_cancellation_change_notification(event)
        else:
            return self._generate_unknown_sales_notification(event)
    
    def _generate_new_buyout_notification(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о новом выкупе"""
        return {
            "type": "new_buyout",
            "title": f"💰 Выкуп #{event.get('order_id', 'N/A')}",
            "content": self._format_new_buyout_content(
                event.get("order_id"),
                event.get("amount"),
                event.get("product_name"),
                event.get("brand"),
                event.get("size")
            ),
            "priority": "HIGH",
            "data": event
        }
    
    def _generate_new_return_notification(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о новом возврате"""
        return {
            "type": "new_return",
            "title": f"🔄 Возврат #{event.get('order_id', 'N/A')}",
            "content": self._format_new_return_content(
                event.get("order_id"),
                event.get("amount"),
                event.get("product_name"),
                event.get("brand"),
                event.get("size")
            ),
            "priority": "HIGH",
            "data": event
        }
    
    def _generate_sale_status_change_notification(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления об изменении статуса продажи"""
        return {
            "type": "sale_status_change",
            "title": f"📊 Статус изменен #{event.get('order_id', 'N/A')}",
            "content": self._format_sale_status_change_content(
                event.get("order_id"),
                event.get("product_name"),
                event.get("previous_status"),
                event.get("current_status"),
                event.get("amount")
            ),
            "priority": "MEDIUM",
            "data": event
        }
    
    def _generate_sale_cancellation_change_notification(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления об изменении отмены продажи"""
        return {
            "type": "sale_cancellation_change",
            "title": f"❌ Отмена изменена #{event.get('order_id', 'N/A')}",
            "content": self._format_sale_cancellation_change_content(
                event.get("order_id"),
                event.get("product_name"),
                event.get("was_cancelled"),
                event.get("is_cancelled"),
                event.get("amount")
            ),
            "priority": "MEDIUM",
            "data": event
        }
    
    def _generate_unknown_sales_notification(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о неизвестном событии продажи"""
        return {
            "type": "unknown_sales_event",
            "title": "❓ Неизвестное событие продажи",
            "content": f"Обнаружено неизвестное событие: {event.get('type', 'unknown')}",
            "priority": "LOW",
            "data": event
        }
    
    def _format_new_buyout_content(self, order_id: str, amount: float, product_name: str, brand: str, size: str) -> str:
        """Форматирование контента уведомления о новом выкупе"""
        return f"""💰 Новый выкуп #{order_id}

💵 Сумма: {self.format_currency(amount)}
📦 Товар: {product_name}
🏷️ Бренд: {brand}
📏 Размер: {size}

Время: {TimezoneUtils.format_time_only(TimezoneUtils.now_msk())}"""
    
    def _format_new_return_content(self, order_id: str, amount: float, product_name: str, brand: str, size: str) -> str:
        """Форматирование контента уведомления о новом возврате"""
        return f"""🔄 Новый возврат #{order_id}

💵 Сумма: {self.format_currency(amount)}
📦 Товар: {product_name}
🏷️ Бренд: {brand}
📏 Размер: {size}

Время: {TimezoneUtils.format_time_only(TimezoneUtils.now_msk())}"""
    
    def _format_sale_status_change_content(self, order_id: str, product_name: str, previous_status: str, current_status: str, amount: float) -> str:
        """Форматирование контента уведомления об изменении статуса продажи"""
        return f"""📊 Статус изменен #{order_id}

📦 Товар: {product_name}
💵 Сумма: {self.format_currency(amount)}
🔄 {previous_status} -> {current_status}

Время: {TimezoneUtils.format_time_only(TimezoneUtils.now_msk())}"""
    
    def _format_sale_cancellation_change_content(self, order_id: str, product_name: str, was_cancelled: bool, is_cancelled: bool, amount: float) -> str:
        """Форматирование контента уведомления об изменении отмены продажи"""
        status_change = "отменена" if is_cancelled else "восстановлена"
        return f"""❌ Продажа {status_change} #{order_id}

📦 Товар: {product_name}
💵 Сумма: {self.format_currency(amount)}
🔄 Статус: {'Отменена' if is_cancelled else 'Активна'}

Время: {TimezoneUtils.format_time_only(TimezoneUtils.now_msk())}"""
