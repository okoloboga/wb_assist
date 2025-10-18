"""
Status Change Monitor для системы уведомлений S3
Отслеживание изменений статуса заказов
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class StatusChangeMonitor:
    """Монитор изменений статуса заказов"""
    
    def track_order_changes(
        self, 
        user_id: int, 
        orders: List[Dict[str, Any]], 
        redis_client
    ) -> List[Dict[str, Any]]:
        """Отслеживание изменений заказов"""
        # Получаем предыдущее состояние
        previous_state = self.get_previous_state(user_id, redis_client)
        
        # Сравниваем состояния
        changes = self.compare_order_states(previous_state, orders)
        
        # Сохраняем текущее состояние
        current_state = {str(order["order_id"]): order.get("status", "unknown") for order in orders}
        self.save_current_state(user_id, current_state, redis_client)
        
        return changes
    
    def get_previous_state(self, user_id: int, redis_client) -> Dict[str, str]:
        """Получение предыдущего состояния заказов"""
        try:
            state_data = redis_client.get(f"notifications:order_status:{user_id}")
            if state_data:
                # Если данные приходят как строка, парсим JSON
                if isinstance(state_data, str):
                    return json.loads(state_data)
                # Если данные уже словарь, возвращаем как есть
                elif isinstance(state_data, dict):
                    return state_data
        except Exception:
            pass
        
        return {}
    
    def save_current_state(
        self, 
        user_id: int, 
        state: Dict[str, str], 
        redis_client
    ) -> bool:
        """Сохранение текущего состояния заказов"""
        try:
            redis_client.set(
                f"notifications:order_status:{user_id}",
                json.dumps(state),
                ex=3600  # TTL 1 час
            )
            return True
        except Exception:
            return False
    
    def compare_order_states(
        self, 
        previous_state: Dict[str, str], 
        current_orders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Сравнение состояний заказов"""
        changes = []
        
        # Создаем словарь текущих статусов
        current_state = {}
        for order in current_orders:
            order_id = str(order["order_id"])
            current_status = order.get("status", "unknown")
            current_state[order_id] = current_status
            
            # Проверяем изменения
            previous_status = previous_state.get(order_id)
            
            if previous_status != current_status:
                change = {
                    "order_id": order["order_id"],
                    "previous_status": previous_status,
                    "current_status": current_status,
                    "amount": order.get("amount", 0),
                    "product_name": order.get("product_name", ""),
                    "brand": order.get("brand", ""),
                    "detected_at": datetime.now(timezone.utc)
                }
                changes.append(change)
        
        return changes
    
    def detect_buyout_changes(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Обнаружение выкупов заказов"""
        return [
            change for change in changes
            if (change.get("previous_status") == "active" and 
                change.get("current_status") == "buyout")
        ]
    
    def detect_cancellation_changes(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Обнаружение отмен заказов"""
        return [
            change for change in changes
            if (change.get("previous_status") == "active" and 
                change.get("current_status") == "cancelled")
        ]
    
    def detect_return_changes(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Обнаружение возвратов заказов"""
        return [
            change for change in changes
            if (change.get("previous_status") == "buyout" and 
                change.get("current_status") == "return")
        ]
    
    def get_status_change_events(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Получение событий изменений статуса"""
        events = []
        
        # Выкупы
        buyout_changes = self.detect_buyout_changes(changes)
        for change in buyout_changes:
            event = {
                "type": "order_buyout",
                "user_id": change.get("user_id"),
                "order_id": change["order_id"],
                "previous_status": change["previous_status"],
                "current_status": change["current_status"],
                "amount": change.get("amount", 0),
                "product_name": change.get("product_name", ""),
                "brand": change.get("brand", ""),
                "detected_at": change.get("detected_at", datetime.now(timezone.utc))
            }
            events.append(event)
        
        # Отмены
        cancellation_changes = self.detect_cancellation_changes(changes)
        for change in cancellation_changes:
            event = {
                "type": "order_cancellation",
                "user_id": change.get("user_id"),
                "order_id": change["order_id"],
                "previous_status": change["previous_status"],
                "current_status": change["current_status"],
                "amount": change.get("amount", 0),
                "product_name": change.get("product_name", ""),
                "brand": change.get("brand", ""),
                "detected_at": change.get("detected_at", datetime.now(timezone.utc))
            }
            events.append(event)
        
        # Возвраты
        return_changes = self.detect_return_changes(changes)
        for change in return_changes:
            event = {
                "type": "order_return",
                "user_id": change.get("user_id"),
                "order_id": change["order_id"],
                "previous_status": change["previous_status"],
                "current_status": change["current_status"],
                "amount": change.get("amount", 0),
                "product_name": change.get("product_name", ""),
                "brand": change.get("brand", ""),
                "detected_at": change.get("detected_at", datetime.now(timezone.utc))
            }
            events.append(event)
        
        return events
