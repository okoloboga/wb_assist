"""
Notification Generator для системы уведомлений S3
Генерация уведомлений на основе событий
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional


class NotificationGenerator:
    """Генератор уведомлений на основе событий"""
    
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
        if event_type == "new_order":
            return self._generate_new_order_notification(event_data, user_settings)
        elif event_type == "order_buyout":
            return self._generate_order_buyout_notification(event_data, user_settings)
        elif event_type == "order_cancellation":
            return self._generate_order_cancellation_notification(event_data, user_settings)
        elif event_type == "order_return":
            return self._generate_order_return_notification(event_data, user_settings)
        elif event_type == "negative_review":
            return self._generate_negative_review_notification(event_data, user_settings)
        elif event_type == "critical_stocks":
            return self._generate_critical_stocks_notification(event_data, user_settings)
        
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
    
    def _generate_new_order_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о новом заказе"""
        order_id = event_data.get("order_id", "N/A")
        amount = event_data.get("amount", 0)
        product_name = event_data.get("product_name", "Неизвестный товар")
        brand = event_data.get("brand", "Неизвестный бренд")
        
        title = f"🛒 Новый заказ #{order_id}"
        content = self._format_new_order_content(order_id, amount, product_name, brand)
        
        return {
            "type": "new_order",
            "user_id": event_data.get("user_id"),
            "order_id": order_id,
            "amount": amount,
            "title": title,
            "content": content,
            "priority": "HIGH",
            "grouping_enabled": user_settings.get("grouping_enabled", True),
            "max_group_size": user_settings.get("max_group_size", 5),
            "group_timeout": user_settings.get("group_timeout", 300),
            "generated_at": datetime.now(timezone.utc)
        }
    
    def _generate_order_buyout_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о выкупе заказа"""
        order_id = event_data.get("order_id", "N/A")
        amount = event_data.get("amount", 0)
        product_name = event_data.get("product_name", "Неизвестный товар")
        brand = event_data.get("brand", "Неизвестный бренд")
        
        title = f"✅ Заказ #{order_id} выкуплен"
        content = self._format_order_buyout_content(order_id, amount, product_name, brand)
        
        return {
            "type": "order_buyout",
            "user_id": event_data.get("user_id"),
            "order_id": order_id,
            "amount": amount,
            "title": title,
            "content": content,
            "priority": "HIGH",
            "grouping_enabled": user_settings.get("grouping_enabled", True),
            "max_group_size": user_settings.get("max_group_size", 5),
            "group_timeout": user_settings.get("group_timeout", 300),
            "generated_at": datetime.now(timezone.utc)
        }
    
    def _generate_order_cancellation_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления об отмене заказа"""
        order_id = event_data.get("order_id", "N/A")
        amount = event_data.get("amount", 0)
        product_name = event_data.get("product_name", "Неизвестный товар")
        brand = event_data.get("brand", "Неизвестный бренд")
        
        title = f"❌ Заказ #{order_id} отменен"
        content = self._format_order_cancellation_content(order_id, amount, product_name, brand)
        
        return {
            "type": "order_cancellation",
            "user_id": event_data.get("user_id"),
            "order_id": order_id,
            "amount": amount,
            "title": title,
            "content": content,
            "priority": "HIGH",
            "grouping_enabled": user_settings.get("grouping_enabled", True),
            "max_group_size": user_settings.get("max_group_size", 5),
            "group_timeout": user_settings.get("group_timeout", 300),
            "generated_at": datetime.now(timezone.utc)
        }
    
    def _generate_order_return_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о возврате заказа"""
        order_id = event_data.get("order_id", "N/A")
        amount = event_data.get("amount", 0)
        product_name = event_data.get("product_name", "Неизвестный товар")
        brand = event_data.get("brand", "Неизвестный бренд")
        
        title = f"🔄 Заказ #{order_id} возвращен"
        content = self._format_order_return_content(order_id, amount, product_name, brand)
        
        return {
            "type": "order_return",
            "user_id": event_data.get("user_id"),
            "order_id": order_id,
            "amount": amount,
            "title": title,
            "content": content,
            "priority": "HIGH",
            "grouping_enabled": user_settings.get("grouping_enabled", True),
            "max_group_size": user_settings.get("max_group_size", 5),
            "group_timeout": user_settings.get("group_timeout", 300),
            "generated_at": datetime.now(timezone.utc)
        }
    
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
            "generated_at": datetime.now(timezone.utc)
        }
    
    def _generate_critical_stocks_notification(self, event_data: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация уведомления о критичных остатках"""
        nm_id = event_data.get("nm_id", "N/A")
        name = event_data.get("name", "Неизвестный товар")
        brand = event_data.get("brand", "Неизвестный бренд")
        critical_sizes = event_data.get("critical_sizes", [])
        zero_sizes = event_data.get("zero_sizes", [])
        
        title = f"⚠️ Критичные остатки #{nm_id}"
        content = self._format_critical_stocks_content(nm_id, name, brand, critical_sizes, zero_sizes)
        
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
            "generated_at": datetime.now(timezone.utc)
        }
    
    def _format_new_order_content(self, order_id: int, amount: int, product_name: str, brand: str) -> str:
        """Форматирование контента уведомления о новом заказе"""
        return f"""🛒 Новый заказ #{order_id}

💰 Сумма: {amount:,} ₽
📦 Товар: {product_name}
🏷️ Бренд: {brand}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_order_buyout_content(self, order_id: int, amount: int, product_name: str, brand: str) -> str:
        """Форматирование контента уведомления о выкупе заказа"""
        return f"""✅ Заказ #{order_id} выкуплен

💰 Сумма: {amount:,} ₽
📦 Товар: {product_name}
🏷️ Бренд: {brand}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_order_cancellation_content(self, order_id: int, amount: int, product_name: str, brand: str) -> str:
        """Форматирование контента уведомления об отмене заказа"""
        return f"""❌ Заказ #{order_id} отменен

💰 Сумма: {amount:,} ₽
📦 Товар: {product_name}
🏷️ Бренд: {brand}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_order_return_content(self, order_id: int, amount: int, product_name: str, brand: str) -> str:
        """Форматирование контента уведомления о возврате заказа"""
        return f"""🔄 Заказ #{order_id} возвращен

💰 Сумма: {amount:,} ₽
📦 Товар: {product_name}
🏷️ Бренд: {brand}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_negative_review_content(self, review_id: int, rating: int, text: str, product_name: str, order_id: Optional[int]) -> str:
        """Форматирование контента уведомления о негативном отзыве"""
        order_info = f"Заказ: #{order_id}" if order_id else "Заказ: неизвестен"
        
        return f"""😞 Негативный отзыв #{review_id}

⭐ Оценка: {rating}/5
📝 Текст: {text}
📦 Товар: {product_name}
🛒 {order_info}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
    
    def _format_critical_stocks_content(self, nm_id: int, name: str, brand: str, critical_sizes: list, zero_sizes: list) -> str:
        """Форматирование контента уведомления о критичных остатках"""
        critical_info = f"Критичные размеры: {', '.join(critical_sizes)}" if critical_sizes else "Нет критичных размеров"
        zero_info = f"Нулевые размеры: {', '.join(zero_sizes)}" if zero_sizes else "Нет нулевых размеров"
        
        return f"""⚠️ Критичные остатки #{nm_id}

📦 Товар: {name}
🏷️ Бренд: {brand}
🔴 {critical_info}
⚫ {zero_info}

Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"""
