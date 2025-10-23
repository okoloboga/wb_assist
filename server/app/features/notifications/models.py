"""
Модели базы данных для системы уведомлений S3
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from ...core.database import Base


class NotificationSettings(Base):
    """Настройки уведомлений пользователя"""
    __tablename__ = "notification_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    
    # Настройки по типам уведомлений (включено/выключено)
    new_orders_enabled = Column(Boolean, default=True, nullable=False)
    order_buyouts_enabled = Column(Boolean, default=True, nullable=False)
    order_cancellations_enabled = Column(Boolean, default=True, nullable=False)
    order_returns_enabled = Column(Boolean, default=True, nullable=False)
    negative_reviews_enabled = Column(Boolean, default=True, nullable=False)
    critical_stocks_enabled = Column(Boolean, default=True, nullable=False)
    
    # Группировка
    grouping_enabled = Column(Boolean, default=True, nullable=False)
    max_group_size = Column(Integer, default=5, nullable=False)
    group_timeout = Column(Integer, default=300, nullable=False)  # секунды
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<NotificationSettings {self.id} - User {self.user_id}>"


class NotificationHistory(Base):
    """История отправленных уведомлений"""
    __tablename__ = "notification_history"
    
    id = Column(String(100), primary_key=True)  # notif_12345
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, delivered, failed
    delivery_time = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<NotificationHistory {self.id} - {self.notification_type}>"


class OrderStatusHistory(Base):
    """История изменений статуса заказов"""
    __tablename__ = "order_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, nullable=False, index=True)
    previous_status = Column(String(50), nullable=True)
    current_status = Column(String(50), nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    notification_sent = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<OrderStatusHistory {self.id} - Order {self.order_id}>"
