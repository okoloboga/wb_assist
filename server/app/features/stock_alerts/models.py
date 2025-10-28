"""
Модели базы данных для системы динамических уведомлений по остаткам
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, BigInteger, func, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class DailySalesAnalytics(Base):
    """Агрегированные данные о заказах за день для каждой комбинации товар-склад-размер"""
    __tablename__ = "daily_sales_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id", ondelete="CASCADE"), nullable=False)
    nm_id = Column(BigInteger, nullable=False)
    warehouse_name = Column(String(255), nullable=False)
    size = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    orders_count = Column(Integer, default=0, nullable=False)
    quantity_ordered = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Индексы для производительности
    __table_args__ = (
        Index('idx_daily_analytics_cabinet_date', 'cabinet_id', 'date'),
        Index('idx_daily_analytics_product', 'nm_id', 'warehouse_name', 'size'),
        Index('idx_daily_analytics_lookback', 'cabinet_id', 'date'),
        # Уникальность по комбинации
        Index('unique_daily_analytics', 'cabinet_id', 'nm_id', 'warehouse_name', 'size', 'date', unique=True),
    )
    
    def __repr__(self):
        return f"<DailySalesAnalytics(nm_id={self.nm_id}, warehouse={self.warehouse_name}, size={self.size}, date={self.date})>"


class StockAlertHistory(Base):
    """История отправленных уведомлений по остаткам для предотвращения дублирования"""
    __tablename__ = "stock_alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nm_id = Column(BigInteger, nullable=False)
    warehouse_name = Column(String(255), nullable=False)
    size = Column(String(50), nullable=False)
    alert_type = Column(String(50), default='dynamic_stock', nullable=False)
    orders_last_24h = Column(Integer, nullable=False)
    current_stock = Column(Integer, nullable=False)
    days_remaining = Column(Float, nullable=False)
    notification_sent_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Индексы
    __table_args__ = (
        Index('idx_alert_history_cabinet', 'cabinet_id'),
        Index('idx_alert_history_product', 'nm_id', 'warehouse_name', 'size'),
        Index('idx_alert_history_sent_at', 'notification_sent_at'),
    )
    
    def __repr__(self):
        return f"<StockAlertHistory(nm_id={self.nm_id}, warehouse={self.warehouse_name}, size={self.size}, days_remaining={self.days_remaining})>"

