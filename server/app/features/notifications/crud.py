"""
CRUD операции для системы уведомлений S3
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .models import NotificationSettings, NotificationHistory, OrderStatusHistory


class NotificationSettingsCRUD:
    """CRUD операции для настроек уведомлений"""
    
    def get_user_settings(self, db: Session, user_id: int) -> Optional[NotificationSettings]:
        """Получение настроек пользователя"""
        return db.query(NotificationSettings).filter(
            NotificationSettings.user_id == user_id
        ).first()
    
    def create_default_settings(self, db: Session, user_id: int) -> NotificationSettings:
        """Создание настроек по умолчанию для нового пользователя"""
        settings = NotificationSettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    
    def update_settings(self, db: Session, user_id: int, settings_data: Dict[str, Any]) -> NotificationSettings:
        """Обновление настроек пользователя"""
        settings = self.get_user_settings(db, user_id)
        if not settings:
            settings = self.create_default_settings(db, user_id)
        
        # Обновляем только переданные поля
        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        db.commit()
        db.refresh(settings)
        return settings


class NotificationHistoryCRUD:
    """CRUD операции для истории уведомлений"""
    
    def create_notification(self, db: Session, notification_data: Dict[str, Any]) -> NotificationHistory:
        """Создание записи уведомления"""
        notification = NotificationHistory(**notification_data)
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification
    
    def update_delivery_status(self, db: Session, notification_id: str, status: str) -> bool:
        """Обновление статуса доставки уведомления"""
        notification = db.query(NotificationHistory).filter(
            NotificationHistory.id == notification_id
        ).first()
        
        if not notification:
            return False
        
        notification.status = status
        if status == "delivered":
            notification.delivery_time = datetime.now(timezone.utc)
        elif status == "failed":
            notification.retry_count += 1
        
        db.commit()
        return True
    
    def get_user_history(
        self, 
        db: Session, 
        user_id: int, 
        filters: Dict[str, Any]
    ) -> List[NotificationHistory]:
        """Получение истории уведомлений пользователя с фильтрацией"""
        query = db.query(NotificationHistory).filter(
            NotificationHistory.user_id == user_id
        )
        
        # Фильтрация по типу уведомления
        if "type" in filters:
            query = query.filter(NotificationHistory.notification_type == filters["type"])
        
        # Фильтрация по датам
        if "date_from" in filters:
            query = query.filter(NotificationHistory.sent_at >= filters["date_from"])
        
        if "date_to" in filters:
            query = query.filter(NotificationHistory.sent_at <= filters["date_to"])
        
        # Сортировка по времени отправки (новые сначала)
        query = query.order_by(NotificationHistory.sent_at.desc())
        
        # Пагинация
        limit = filters.get("limit", 20)
        offset = filters.get("offset", 0)
        query = query.offset(offset).limit(limit)
        
        return query.all()


class OrderStatusHistoryCRUD:
    """CRUD операции для истории статуса заказов"""
    
    def track_status_change(
        self, 
        db: Session, 
        user_id: int, 
        order_id: int, 
        previous_status: Optional[str], 
        current_status: str
    ) -> OrderStatusHistory:
        """Отслеживание изменения статуса заказа"""
        # Проверяем, есть ли уже такая запись
        existing = db.query(OrderStatusHistory).filter(
            and_(
                OrderStatusHistory.user_id == user_id,
                OrderStatusHistory.order_id == order_id,
                OrderStatusHistory.previous_status == previous_status,
                OrderStatusHistory.current_status == current_status
            )
        ).first()
        
        if existing:
            return existing
        
        # Создаем новую запись
        status_history = OrderStatusHistory(
            user_id=user_id,
            order_id=order_id,
            previous_status=previous_status,
            current_status=current_status,
            changed_at=datetime.now(timezone.utc)
        )
        
        db.add(status_history)
        db.commit()
        db.refresh(status_history)
        return status_history
    
    def prevent_duplicate_notifications(
        self, 
        db: Session, 
        user_id: int, 
        order_id: int, 
        previous_status: Optional[str], 
        current_status: str
    ) -> bool:
        """Предотвращение дубликатов уведомлений"""
        existing = db.query(OrderStatusHistory).filter(
            and_(
                OrderStatusHistory.user_id == user_id,
                OrderStatusHistory.order_id == order_id,
                OrderStatusHistory.previous_status == previous_status,
                OrderStatusHistory.current_status == current_status,
                OrderStatusHistory.notification_sent == True
            )
        ).first()
        
        return existing is not None
    
    def get_pending_changes(self, db: Session, user_id: int) -> List[OrderStatusHistory]:
        """Получение ожидающих изменений статуса"""
        return db.query(OrderStatusHistory).filter(
            and_(
                OrderStatusHistory.user_id == user_id,
                OrderStatusHistory.notification_sent == False
            )
        ).order_by(OrderStatusHistory.changed_at.desc()).all()
    
    def mark_notification_sent(self, db: Session, status_history_id: int) -> bool:
        """Отметка уведомления как отправленного"""
        status_history = db.query(OrderStatusHistory).filter(
            OrderStatusHistory.id == status_history_id
        ).first()
        
        if not status_history:
            return False
        
        status_history.notification_sent = True
        db.commit()
        return True
