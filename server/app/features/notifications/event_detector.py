"""
Event Detector для системы уведомлений S3
Обнаружение событий в данных Wildberries
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from app.utils.timezone import TimezoneUtils


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
                    "nm_id": order.get("nm_id"),  # ← ДОБАВЛЕНО!
                    "size": order.get("size", ""),  # ← ДОБАВЛЕНО!
                    "article": order.get("article", ""),  # ← ДОБАВЛЕНО!
                    "barcode": order.get("barcode", ""),  # ← ДОБАВЛЕНО!
                    "warehouse_from": order.get("warehouse_from", ""),  # ← ДОБАВЛЕНО!
                    "warehouse_to": order.get("warehouse_to", ""),  # ← ДОБАВЛЕНО!
                    "total_price": order.get("total_price", 0),  # ← ДОБАВЛЕНО!
                    "spp_percent": order.get("spp_percent", 0),  # ← ДОБАВЛЕНО!
                    "customer_price": order.get("customer_price", 0),  # ← ДОБАВЛЕНО!
                    "discount_percent": order.get("discount_percent", 0),  # ← ДОБАВЛЕНО!
                    "order_date": order.get("order_date"),  # ← ДОБАВЛЕНО!
                    "detected_at": TimezoneUtils.now_msk()
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
        
        # Логирование для диагностики
        logger.info(f"🔍 [detect_status_changes] User {user_id}: current_orders={len(current_orders)}, previous_orders={len(previous_orders)}")
        
        # Создаем словарь предыдущих статусов
        previous_statuses = {
            order["order_id"]: order.get("status", "unknown") 
            for order in previous_orders
        }
        
        logger.info(f"🔍 [detect_status_changes] Previous statuses: {previous_statuses}")
        
        # Проверяем изменения статуса
        for order in current_orders:
            order_id = order["order_id"]
            current_status = order.get("status", "unknown")
            previous_status = previous_statuses.get(order_id)
            
            logger.info(f"🔍 [detect_status_changes] Order {order_id}: previous={previous_status}, current={current_status}")
            
            if previous_status and previous_status != current_status:
                event_type = self._get_status_change_event_type(previous_status, current_status)
                
                logger.info(f"🔍 [detect_status_changes] Status change detected: {previous_status} → {current_status}, event_type={event_type}")
                
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
                        "detected_at": TimezoneUtils.now_msk()
                    }
                    events.append(event)
                    logger.info(f"🔍 [detect_status_changes] Event created: {event}")
        
        logger.info(f"🔍 [detect_status_changes] Total events detected: {len(events)}")
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
                    "detected_at": TimezoneUtils.now_msk()
                }
                events.append(event)
        
        return events
    
    def _get_status_change_event_type(self, previous_status: str, current_status: str) -> str:
        """Определение типа события изменения статуса"""
        status_mapping = {
            ("active", "buyout"): "order_buyout",
            ("active", "canceled"): "order_cancellation", 
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
    
    def detect_sales_changes(
        self,
        user_id: int,
        current_sales: List[Dict[str, Any]],
        previous_sales: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Обнаружение изменений в продажах и возвратах"""
        events = []
        
        # Получаем ID существующих продаж
        previous_sale_ids = {sale["sale_id"] for sale in previous_sales}
        
        # Находим новые продажи
        for sale in current_sales:
            if sale["sale_id"] not in previous_sale_ids:
                event_type = "new_buyout" if sale["type"] == "buyout" else "new_return"
                event = {
                    "type": event_type,
                    "user_id": user_id,
                    "sale_id": sale["sale_id"],
                    "order_id": sale.get("order_id"),
                    "product_name": sale.get("product_name"),
                    "amount": sale.get("amount"),
                    "sale_date": sale.get("sale_date"),
                    "nm_id": sale.get("nm_id"),
                    "brand": sale.get("brand"),
                    "size": sale.get("size"),
                    "detected_at": TimezoneUtils.now_msk().isoformat()
                }
                events.append(event)
        
        # Находим изменения в существующих продажах
        current_sale_dict = {sale["sale_id"]: sale for sale in current_sales}
        previous_sale_dict = {sale["sale_id"]: sale for sale in previous_sales}
        
        for sale_id in current_sale_dict:
            if sale_id in previous_sale_dict:
                current_sale = current_sale_dict[sale_id]
                previous_sale = previous_sale_dict[sale_id]
                
                # Проверяем изменения статуса
                if current_sale.get("status") != previous_sale.get("status"):
                    event = {
                        "type": "sale_status_change",
                        "user_id": user_id,
                        "sale_id": sale_id,
                        "order_id": current_sale.get("order_id"),
                        "product_name": current_sale.get("product_name"),
                        "previous_status": previous_sale.get("status"),
                        "current_status": current_sale.get("status"),
                        "amount": current_sale.get("amount"),
                        "sale_date": current_sale.get("sale_date"),
                        "detected_at": TimezoneUtils.now_msk().isoformat()
                    }
                    events.append(event)
                
                # Проверяем изменения в отмене
                if current_sale.get("is_cancel") != previous_sale.get("is_cancel"):
                    event = {
                        "type": "sale_cancellation_change",
                        "user_id": user_id,
                        "sale_id": sale_id,
                        "order_id": current_sale.get("order_id"),
                        "product_name": current_sale.get("product_name"),
                        "was_cancelled": previous_sale.get("is_cancel"),
                        "is_cancelled": current_sale.get("is_cancel"),
                        "amount": current_sale.get("amount"),
                        "sale_date": current_sale.get("sale_date"),
                        "detected_at": TimezoneUtils.now_msk().isoformat()
                    }
                    events.append(event)
        
        return events
