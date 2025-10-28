"""
Агрегатор продаж - агрегация заказов из WBOrder в daily_sales_analytics
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, datetime, timedelta
from typing import Dict, Any, List
import logging

from app.features.wb_api.models import WBOrder
from .models import DailySalesAnalytics
from .schemas import DailySalesAnalyticsCreate
from .crud import DailySalesAnalyticsCRUD

logger = logging.getLogger(__name__)


class DailySalesAggregator:
    """Агрегация данных о заказах для анализа остатков"""
    
    def __init__(self, db: Session):
        self.db = db
        self.crud = DailySalesAnalyticsCRUD()
    
    async def aggregate_orders_for_date(
        self, 
        cabinet_id: int, 
        target_date: date
    ) -> Dict[str, Any]:
        """
        Агрегирует заказы за указанную дату
        
        Логика:
        1. Получить все заказы за дату из WBOrder
        2. Группировать по (nm_id, warehouse_name, size)
        3. Подсчитать orders_count и quantity_ordered
        4. Записать/обновить в daily_sales_analytics
        
        Args:
            cabinet_id: ID кабинета
            target_date: Дата для агрегации
        
        Returns:
            Статистика обработки
        """
        try:
            logger.info(f"Starting aggregation for cabinet {cabinet_id}, date {target_date}")
            
            # Получаем все заказы за указанную дату
            next_date = target_date + timedelta(days=1)
            
            orders = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.order_date >= datetime.combine(target_date, datetime.min.time()),
                    WBOrder.order_date < datetime.combine(next_date, datetime.min.time())
                )
            ).all()
            
            if not orders:
                logger.info(f"No orders found for cabinet {cabinet_id} on {target_date}")
                return {
                    "status": "success",
                    "date": str(target_date),
                    "records_processed": 0,
                    "unique_positions": 0
                }
            
            # Группируем по (nm_id, warehouse_name, size)
            aggregated = {}
            
            for order in orders:
                # Получаем данные о товаре из заказа
                nm_id = order.nm_id
                # Используем warehouse_from как основной склад (откуда отправляется товар)
                warehouse_name = order.warehouse_from or "Неизвестный склад"
                
                # Размер товара
                size = order.size or "ONE SIZE"
                
                key = (nm_id, warehouse_name, size)
                
                if key not in aggregated:
                    aggregated[key] = {
                        "orders_count": 0,
                        "quantity_ordered": 0
                    }
                
                aggregated[key]["orders_count"] += 1
                # Количество единиц товара в заказе (в WBOrder всегда 1)
                quantity = order.quantity or 1
                aggregated[key]["quantity_ordered"] += quantity
            
            # Записываем агрегированные данные в БД
            records_created = 0
            for (nm_id, warehouse_name, size), stats in aggregated.items():
                analytics_data = DailySalesAnalyticsCreate(
                    cabinet_id=cabinet_id,
                    nm_id=nm_id,
                    warehouse_name=warehouse_name,
                    size=size,
                    date=target_date,
                    orders_count=stats["orders_count"],
                    quantity_ordered=stats["quantity_ordered"]
                )
                
                self.crud.create_or_update(self.db, analytics_data)
                records_created += 1
            
            logger.info(
                f"Aggregation completed: {records_created} positions, "
                f"{len(orders)} orders processed"
            )
            
            return {
                "status": "success",
                "date": str(target_date),
                "records_processed": len(orders),
                "unique_positions": records_created
            }
            
        except Exception as e:
            logger.error(f"Error aggregating orders for date {target_date}: {e}")
            return {
                "status": "error",
                "date": str(target_date),
                "error": str(e)
            }
    
    async def aggregate_last_n_days(
        self, 
        cabinet_id: int, 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Агрегирует заказы за последние N дней
        Используется для первичной загрузки или пересчета
        
        Args:
            cabinet_id: ID кабинета
            days: Количество дней для агрегации
        
        Returns:
            Статистика обработки
        """
        try:
            logger.info(f"Starting aggregation for last {days} days, cabinet {cabinet_id}")
            
            results = []
            total_records = 0
            total_positions = 0
            
            # Агрегируем каждый день отдельно
            for i in range(days):
                target_date = date.today() - timedelta(days=i+1)
                result = await self.aggregate_orders_for_date(cabinet_id, target_date)
                results.append(result)
                
                if result["status"] == "success":
                    total_records += result["records_processed"]
                    total_positions += result["unique_positions"]
            
            logger.info(
                f"Completed aggregation for {days} days: "
                f"{total_records} orders, {total_positions} positions"
            )
            
            return {
                "status": "success",
                "days_processed": days,
                "total_records": total_records,
                "total_positions": total_positions,
                "daily_results": results
            }
            
        except Exception as e:
            logger.error(f"Error aggregating last {days} days: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_rolling_stats(
        self,
        cabinet_id: int,
        nm_id: int,
        warehouse_name: str,
        size: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Получить статистику заказов за последние N часов
        
        Args:
            cabinet_id: ID кабинета
            nm_id: ID товара
            warehouse_name: Название склада
            size: Размер
            hours: Количество часов для анализа
        
        Returns:
            Статистика заказов
        """
        try:
            # Конвертируем часы в дни для запроса к daily_sales_analytics
            days = max(1, (hours + 23) // 24)  # Округляем вверх
            
            stats = self.crud.get_rolling_stats(
                db=self.db,
                cabinet_id=cabinet_id,
                nm_id=nm_id,
                warehouse_name=warehouse_name,
                size=size,
                days=days
            )
            
            # Корректируем среднее с учетом запрошенных часов
            if stats["avg_per_day"] > 0:
                stats["avg_per_hour"] = stats["avg_per_day"] / 24
                stats["avg_for_period"] = stats["avg_per_hour"] * hours
            else:
                stats["avg_per_hour"] = 0
                stats["avg_for_period"] = 0
            
            stats["period_hours"] = hours
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting rolling stats: {e}")
            return {
                "orders_count": 0,
                "quantity_ordered": 0,
                "period_hours": hours,
                "avg_per_day": 0,
                "error": str(e)
            }

