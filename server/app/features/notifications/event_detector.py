"""
Event Detector для системы уведомлений S3
Обнаружение событий в данных Wildberries
"""

from typing import List, Dict, Any
from datetime import datetime, timezone


class EventDetector:
    """Детектор событий для системы уведомлений"""
    
    def detect_new_orders(
        self, 
        user_id: int, 
        current_orders: List[Dict[str, Any]], 
        previous_orders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Обнаружение новых заказов"""
        events = []
        
        # Получаем ID существующих заказов
        previous_order_ids = {order["order_id"] for order in previous_orders}
        
        # Находим новые заказы
        for order in current_orders:
            if order["order_id"] not in previous_order_ids:
                event = {
                    "type": "new_order",
                    "user_id": user_id,
                    "order_id": order["order_id"],
                    "amount": order.get("amount", 0),
                    "status": order.get("status", "unknown"),
                    "product_name": order.get("product_name", ""),
                    "brand": order.get("brand", ""),
                    "detected_at": datetime.now(timezone.utc)
                }
                events.append(event)
        
        return events
    
    def detect_status_changes(
        self, 
        user_id: int, 
        current_orders: List[Dict[str, Any]], 
        previous_orders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Обнаружение изменений статуса заказов"""
        events = []
        
        # Создаем словарь предыдущих статусов
        previous_statuses = {
            order["order_id"]: order.get("status", "unknown") 
            for order in previous_orders
        }
        
        # Проверяем изменения статуса
        for order in current_orders:
            order_id = order["order_id"]
            current_status = order.get("status", "unknown")
            previous_status = previous_statuses.get(order_id)
            
            if previous_status and previous_status != current_status:
                event_type = self._get_status_change_event_type(previous_status, current_status)
                
                if event_type:  # Только для значимых изменений
                    event = {
                        "type": event_type,
                        "user_id": user_id,
                        "order_id": order_id,
                        "previous_status": previous_status,
                        "current_status": current_status,
                        "amount": order.get("amount", 0),
                        "product_name": order.get("product_name", ""),
                        "brand": order.get("brand", ""),
                        "detected_at": datetime.now(timezone.utc)
                    }
                    events.append(event)
        
        return events
    
    def detect_negative_reviews(
        self, 
        user_id: int, 
        current_reviews: List[Dict[str, Any]], 
        previous_reviews: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Обнаружение негативных отзывов"""
        events = []
        
        # Получаем ID существующих отзывов
        previous_review_ids = {review["id"] for review in previous_reviews}
        
        # Находим новые негативные отзывы (оценка 1-3)
        for review in current_reviews:
            if (review["id"] not in previous_review_ids and 
                review.get("rating", 5) <= 3):
                
                event = {
                    "type": "negative_review",
                    "user_id": user_id,
                    "review_id": review["id"],
                    "rating": review.get("rating", 0),
                    "text": review.get("text", ""),
                    "product_name": review.get("product_name", ""),
                    "order_id": review.get("order_id"),
                    "detected_at": datetime.now(timezone.utc)
                }
                events.append(event)
        
        return events
    
    def detect_critical_stocks(
        self, 
        user_id: int, 
        current_stocks: List[Dict[str, Any]], 
        previous_stocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Обнаружение критичных остатков"""
        events = []
        
        # Создаем словарь предыдущих остатков
        previous_stock_levels = {
            stock["nm_id"]: stock.get("stocks", {}) 
            for stock in previous_stocks
        }
        
        # Проверяем текущие остатки
        for stock in current_stocks:
            nm_id = stock["nm_id"]
            current_stocks_data = stock.get("stocks", {})
            previous_stocks_data = previous_stock_levels.get(nm_id, {})
            
            # Проверяем, стал ли товар критичным
            if self._is_critical_stock(current_stocks_data, previous_stocks_data):
                event = {
                    "type": "critical_stocks",
                    "user_id": user_id,
                    "nm_id": nm_id,
                    "name": stock.get("name", ""),
                    "brand": stock.get("brand", ""),
                    "stocks": current_stocks_data,
                    "critical_sizes": self._get_critical_sizes(current_stocks_data),
                    "zero_sizes": self._get_zero_sizes(current_stocks_data),
                    "detected_at": datetime.now(timezone.utc)
                }
                events.append(event)
        
        return events
    
    def _get_status_change_event_type(self, previous_status: str, current_status: str) -> str:
        """Определение типа события изменения статуса"""
        status_mapping = {
            ("active", "buyout"): "order_buyout",
            ("active", "cancelled"): "order_cancellation", 
            ("buyout", "return"): "order_return",
            ("active", "return"): "order_return"
        }
        
        return status_mapping.get((previous_status, current_status), "")
    
    def _is_critical_stock(self, current_stocks: Dict[str, int], previous_stocks: Dict[str, int]) -> bool:
        """Проверка, стал ли товар критичным"""
        # Товар критичен, если есть размеры с остатком <= 2
        critical_threshold = 2
        
        for size, quantity in current_stocks.items():
            if quantity <= critical_threshold:
                # Проверяем, что раньше было больше
                previous_quantity = previous_stocks.get(size, 0)
                if previous_quantity > critical_threshold:
                    return True
        
        return False
    
    def _get_critical_sizes(self, stocks: Dict[str, int]) -> List[str]:
        """Получение критичных размеров (остаток <= 2)"""
        critical_threshold = 2
        return [size for size, quantity in stocks.items() if quantity <= critical_threshold]
    
    def _get_zero_sizes(self, stocks: Dict[str, int]) -> List[str]:
        """Получение размеров с нулевым остатком"""
        return [size for size, quantity in stocks.items() if quantity == 0]
