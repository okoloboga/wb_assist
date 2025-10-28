"""
CRUD операции для системы динамических уведомлений по остаткам
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from .models import DailySalesAnalytics, StockAlertHistory
from .schemas import DailySalesAnalyticsCreate, StockAlertHistoryCreate

logger = logging.getLogger(__name__)


class DailySalesAnalyticsCRUD:
    """CRUD операции для daily_sales_analytics"""
    
    @staticmethod
    def create_or_update(
        db: Session, 
        analytics_data: DailySalesAnalyticsCreate
    ) -> DailySalesAnalytics:
        """Создать или обновить запись аналитики"""
        existing = db.query(DailySalesAnalytics).filter(
            and_(
                DailySalesAnalytics.cabinet_id == analytics_data.cabinet_id,
                DailySalesAnalytics.nm_id == analytics_data.nm_id,
                DailySalesAnalytics.warehouse_name == analytics_data.warehouse_name,
                DailySalesAnalytics.size == analytics_data.size,
                DailySalesAnalytics.date == analytics_data.date
            )
        ).first()
        
        if existing:
            existing.orders_count = analytics_data.orders_count
            existing.quantity_ordered = analytics_data.quantity_ordered
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_analytics = DailySalesAnalytics(**analytics_data.model_dump())
            db.add(new_analytics)
            db.commit()
            db.refresh(new_analytics)
            return new_analytics
    
    @staticmethod
    def get_by_date_range(
        db: Session,
        cabinet_id: int,
        date_from: date,
        date_to: date,
        nm_id: Optional[int] = None
    ) -> List[DailySalesAnalytics]:
        """Получить аналитику за период"""
        query = db.query(DailySalesAnalytics).filter(
            and_(
                DailySalesAnalytics.cabinet_id == cabinet_id,
                DailySalesAnalytics.date >= date_from,
                DailySalesAnalytics.date <= date_to
            )
        )
        
        if nm_id:
            query = query.filter(DailySalesAnalytics.nm_id == nm_id)
        
        return query.all()
    
    @staticmethod
    def get_rolling_stats(
        db: Session,
        cabinet_id: int,
        nm_id: int,
        warehouse_name: str,
        size: str,
        days: int = 1
    ) -> Dict[str, Any]:
        """Получить статистику за последние N дней"""
        date_from = date.today() - timedelta(days=days)
        
        records = db.query(DailySalesAnalytics).filter(
            and_(
                DailySalesAnalytics.cabinet_id == cabinet_id,
                DailySalesAnalytics.nm_id == nm_id,
                DailySalesAnalytics.warehouse_name == warehouse_name,
                DailySalesAnalytics.size == size,
                DailySalesAnalytics.date >= date_from
            )
        ).all()
        
        total_orders = sum(r.orders_count for r in records)
        total_quantity = sum(r.quantity_ordered for r in records)
        
        return {
            "orders_count": total_orders,
            "quantity_ordered": total_quantity,
            "period_days": days,
            "avg_per_day": total_quantity / days if days > 0 else 0
        }
    
    @staticmethod
    def delete_old_records(db: Session, days_to_keep: int = 30) -> int:
        """Удалить старые записи"""
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        deleted_count = db.query(DailySalesAnalytics).filter(
            DailySalesAnalytics.date < cutoff_date
        ).delete()
        
        db.commit()
        logger.info(f"Deleted {deleted_count} old analytics records")
        return deleted_count


class StockAlertHistoryCRUD:
    """CRUD операции для stock_alert_history"""
    
    @staticmethod
    def create(
        db: Session,
        alert_data: StockAlertHistoryCreate
    ) -> StockAlertHistory:
        """Создать запись истории уведомления"""
        new_alert = StockAlertHistory(**alert_data.model_dump())
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        return new_alert
    
    @staticmethod
    def get_recent_alert(
        db: Session,
        cabinet_id: int,
        nm_id: int,
        warehouse_name: str,
        size: str,
        hours: int = 24
    ) -> Optional[StockAlertHistory]:
        """Получить последнее уведомление за N часов"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return db.query(StockAlertHistory).filter(
            and_(
                StockAlertHistory.cabinet_id == cabinet_id,
                StockAlertHistory.nm_id == nm_id,
                StockAlertHistory.warehouse_name == warehouse_name,
                StockAlertHistory.size == size,
                StockAlertHistory.notification_sent_at >= cutoff_time
            )
        ).order_by(desc(StockAlertHistory.notification_sent_at)).first()
    
    @staticmethod
    def get_history(
        db: Session,
        cabinet_id: int,
        limit: int = 50
    ) -> List[StockAlertHistory]:
        """Получить историю уведомлений"""
        return db.query(StockAlertHistory).filter(
            StockAlertHistory.cabinet_id == cabinet_id
        ).order_by(desc(StockAlertHistory.notification_sent_at)).limit(limit).all()
    
    @staticmethod
    def delete_old_records(db: Session, days_to_keep: int = 90) -> int:
        """Удалить старые записи"""
        cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = db.query(StockAlertHistory).filter(
            StockAlertHistory.notification_sent_at < cutoff_time
        ).delete()
        
        db.commit()
        logger.info(f"Deleted {deleted_count} old alert history records")
        return deleted_count

