"""
Sales Monitor - отслеживание изменений в продажах и возвратах
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SalesMonitor:
    """Мониторинг изменений в продажах и возвратах"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_previous_sales_state(self, user_id: int) -> Dict[str, Any]:
        """Получение предыдущего состояния продаж из Redis"""
        try:
            key = f"notifications:sales_state:{user_id}"
            data = self.redis.get(key)
            
            if not data:
                return {}
            
            # Парсим JSON данные
            if isinstance(data, str):
                return json.loads(data)
            elif isinstance(data, dict):
                return data
            else:
                logger.warning(f"Unexpected data type for sales state: {type(data)}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting previous sales state for user {user_id}: {e}")
            return {}
    
    def save_current_sales_state(self, user_id: int, current_state: Dict[str, Any]):
        """Сохранение текущего состояния продаж в Redis"""
        try:
            key = f"notifications:sales_state:{user_id}"
            # Сохраняем как JSON строку
            self.redis.set(key, json.dumps(current_state, default=str))
            logger.debug(f"Saved sales state for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving sales state for user {user_id}: {e}")
    
    def compare_sales_states(
        self, 
        previous_state: Dict[str, Any], 
        current_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Сравнение состояний продаж и выявление изменений"""
        changes = []
        
        try:
            # Получаем множества ID продаж
            previous_sales = set(previous_state.get("sales", {}).keys())
            current_sales = set(current_state.get("sales", {}).keys())
            
            # Новые продажи (выкупы)
            new_buyouts = current_sales - previous_sales
            for sale_id in new_buyouts:
                sale_data = current_state["sales"][sale_id]
                if sale_data.get("type") == "buyout":
                    changes.append({
                        "type": "new_buyout",
                        "sale_id": sale_id,
                        "order_id": sale_data.get("order_id"),
                        "product_name": sale_data.get("product_name"),
                        "amount": sale_data.get("amount"),
                        "sale_date": sale_data.get("sale_date"),
                        "nm_id": sale_data.get("nm_id"),
                        "brand": sale_data.get("brand"),
                        "size": sale_data.get("size")
                    })
            
            # Новые возвраты
            new_returns = current_sales - previous_sales
            for sale_id in new_returns:
                sale_data = current_state["sales"][sale_id]
                if sale_data.get("type") == "return":
                    changes.append({
                        "type": "new_return",
                        "sale_id": sale_id,
                        "order_id": sale_data.get("order_id"),
                        "product_name": sale_data.get("product_name"),
                        "amount": sale_data.get("amount"),
                        "sale_date": sale_data.get("sale_date"),
                        "nm_id": sale_data.get("nm_id"),
                        "brand": sale_data.get("brand"),
                        "size": sale_data.get("size")
                    })
            
            # Изменения в существующих продажах
            common_sales = previous_sales & current_sales
            for sale_id in common_sales:
                prev_sale = previous_state["sales"][sale_id]
                curr_sale = current_state["sales"][sale_id]
                
                # Проверяем изменения статуса
                if prev_sale.get("status") != curr_sale.get("status"):
                    changes.append({
                        "type": "status_change",
                        "sale_id": sale_id,
                        "order_id": curr_sale.get("order_id"),
                        "product_name": curr_sale.get("product_name"),
                        "previous_status": prev_sale.get("status"),
                        "current_status": curr_sale.get("status"),
                        "amount": curr_sale.get("amount"),
                        "sale_date": curr_sale.get("sale_date")
                    })
                
                # Проверяем изменения в отмене
                if prev_sale.get("is_cancel") != curr_sale.get("is_cancel"):
                    changes.append({
                        "type": "cancellation_change",
                        "sale_id": sale_id,
                        "order_id": curr_sale.get("order_id"),
                        "product_name": curr_sale.get("product_name"),
                        "was_cancelled": prev_sale.get("is_cancel"),
                        "is_cancelled": curr_sale.get("is_cancel"),
                        "amount": curr_sale.get("amount"),
                        "sale_date": curr_sale.get("sale_date")
                    })
            
            logger.info(f"Detected {len(changes)} sales changes")
            return changes
            
        except Exception as e:
            logger.error(f"Error comparing sales states: {e}")
            return []
    
    def track_sales_change(self, user_id: int, change_data: Dict[str, Any]):
        """Отслеживание изменения в продаже"""
        try:
            key = f"notifications:sales_changes:{user_id}"
            
            # Добавляем временную метку
            change_data["detected_at"] = datetime.now(timezone.utc).isoformat()
            
            # Сохраняем в Redis список
            self.redis.lpush(key, json.dumps(change_data, default=str))
            
            # Ограничиваем размер списка (последние 100 изменений)
            self.redis.ltrim(key, 0, 99)
            
            logger.debug(f"Tracked sales change for user {user_id}: {change_data['type']}")
            
        except Exception as e:
            logger.error(f"Error tracking sales change for user {user_id}: {e}")
    
    def get_pending_sales_changes(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение ожидающих изменений в продажах"""
        try:
            key = f"notifications:sales_changes:{user_id}"
            changes_data = self.redis.lrange(key, 0, -1)
            
            changes = []
            for change_str in changes_data:
                try:
                    change = json.loads(change_str)
                    changes.append(change)
                except json.JSONDecodeError:
                    continue
            
            return changes
            
        except Exception as e:
            logger.error(f"Error getting pending sales changes for user {user_id}: {e}")
            return []
    
    def mark_sales_change_processed(self, user_id: int, change_id: str):
        """Отметка изменения как обработанного"""
        try:
            key = f"notifications:sales_changes:{user_id}"
            
            # Получаем все изменения
            changes_data = self.redis.lrange(key, 0, -1)
            
            # Удаляем обработанное изменение
            for i, change_str in enumerate(changes_data):
                try:
                    change = json.loads(change_str)
                    if change.get("sale_id") == change_id:
                        self.redis.lrem(key, 1, change_str)
                        break
                except json.JSONDecodeError:
                    continue
            
            logger.debug(f"Marked sales change {change_id} as processed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error marking sales change as processed: {e}")
    
    def clear_sales_changes(self, user_id: int):
        """Очистка всех изменений в продажах"""
        try:
            key = f"notifications:sales_changes:{user_id}"
            self.redis.delete(key)
            logger.debug(f"Cleared sales changes for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error clearing sales changes for user {user_id}: {e}")
