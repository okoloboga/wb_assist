from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...core.database import Base
from datetime import datetime, timezone


class WBCabinet(Base):
    """Модель кабинета Wildberries"""
    __tablename__ = "wb_cabinets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    api_key = Column(String(500), unique=True, nullable=False, index=True)
    cabinet_name = Column(String(100), nullable=False)
    region = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    # Связи
    user = relationship("User", back_populates="wb_cabinets")
    orders = relationship("WBOrder", back_populates="cabinet", cascade="all, delete-orphan")
    products = relationship("WBProduct", back_populates="cabinet", cascade="all, delete-orphan")
    stocks = relationship("WBStock", back_populates="cabinet", cascade="all, delete-orphan")
    reviews = relationship("WBReview", back_populates="cabinet", cascade="all, delete-orphan")
    analytics_cache = relationship("WBAnalyticsCache", back_populates="cabinet", cascade="all, delete-orphan")
    warehouses = relationship("WBWarehouse", back_populates="cabinet", cascade="all, delete-orphan")
    sync_logs = relationship("WBSyncLog", back_populates="cabinet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WBCabinet {self.id} - {self.cabinet_name}>"


class WBOrder(Base):
    """Модель заказа Wildberries"""
    __tablename__ = "wb_orders"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    order_id = Column(String(50), nullable=False)
    nm_id = Column(Integer, nullable=False, index=True)
    article = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    name = Column(String(500), nullable=True)
    subject = Column(String(200), nullable=True)
    category = Column(String(200), nullable=True)
    size = Column(String(50), nullable=True)
    barcode = Column(String(50), nullable=True)
    total_price = Column(Float, nullable=True)
    finished_price = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    spp = Column(Float, nullable=True, default=0.0)
    is_cancel = Column(Boolean, default=False, nullable=False)
    is_realization = Column(Boolean, default=False, nullable=False)
    order_date = Column(DateTime(timezone=True), nullable=True)
    last_change_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="orders")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'order_id', name='uq_cabinet_order'),
        Index('idx_cabinet_nm_id', 'cabinet_id', 'nm_id'),
        Index('idx_order_date', 'order_date'),
    )

    def __repr__(self):
        return f"<WBOrder {self.order_id} - {self.nm_id}>"


class WBProduct(Base):
    """Модель товара Wildberries"""
    __tablename__ = "wb_products"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    nm_id = Column(Integer, nullable=False, index=True)
    article = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    name = Column(String(500), nullable=True)
    subject = Column(String(200), nullable=True)
    category = Column(String(200), nullable=True)
    characteristics = Column(JSON, nullable=True)
    sizes = Column(JSON, nullable=True)
    photos = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="products")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'nm_id', name='uq_cabinet_nm_id'),
        Index('idx_brand', 'brand'),
        Index('idx_subject', 'subject'),
    )

    def __repr__(self):
        return f"<WBProduct {self.nm_id} - {self.name}>"


class WBStock(Base):
    """Модель остатков Wildberries"""
    __tablename__ = "wb_stocks"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    nm_id = Column(Integer, nullable=False, index=True)
    warehouse_id = Column(Integer, nullable=False, index=True)
    warehouse_name = Column(String(200), nullable=True)
    article = Column(String(100), nullable=True)
    size = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    discount = Column(Float, nullable=True)
    last_change_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="stocks")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'nm_id', 'warehouse_id', 'size', name='uq_cabinet_nm_warehouse_size'),
        Index('idx_warehouse_nm_id', 'warehouse_id', 'nm_id'),
        Index('idx_quantity', 'quantity'),
    )

    def __repr__(self):
        return f"<WBStock {self.nm_id} - {self.warehouse_name} - {self.quantity}>"


class WBReview(Base):
    """Модель отзыва Wildberries"""
    __tablename__ = "wb_reviews"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    nm_id = Column(Integer, nullable=False, index=True)
    review_id = Column(String(100), nullable=False)
    text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    is_answered = Column(Boolean, default=False, nullable=False)
    created_date = Column(DateTime(timezone=True), nullable=True)
    updated_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="reviews")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'review_id', name='uq_cabinet_review_id'),
        Index('idx_nm_id_rating', 'nm_id', 'rating'),
        Index('idx_is_answered', 'is_answered'),
    )

    def __repr__(self):
        return f"<WBReview {self.review_id} - {self.rating}★>"


class WBAnalyticsCache(Base):
    """Модель кэша аналитики Wildberries"""
    __tablename__ = "wb_analytics_cache"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    nm_id = Column(Integer, nullable=False, index=True)
    period = Column(String(10), nullable=False)  # 7d, 14d, 30d, 60d, 90d
    sales_count = Column(Integer, nullable=True, default=0)
    sales_amount = Column(Float, nullable=True, default=0.0)
    buyouts_count = Column(Integer, nullable=True, default=0)
    buyouts_amount = Column(Float, nullable=True, default=0.0)
    buyout_rate = Column(Float, nullable=True, default=0.0)
    avg_order_speed = Column(Float, nullable=True, default=0.0)
    reviews_count = Column(Integer, nullable=True, default=0)
    avg_rating = Column(Float, nullable=True, default=0.0)
    last_calculated = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="analytics_cache")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'nm_id', 'period', name='uq_cabinet_nm_period'),
        Index('idx_period', 'period'),
        Index('idx_last_calculated', 'last_calculated'),
    )

    def __repr__(self):
        return f"<WBAnalyticsCache {self.nm_id} - {self.period}>"


class WBWarehouse(Base):
    """Модель склада Wildberries"""
    __tablename__ = "wb_warehouses"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    region = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="warehouses")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'warehouse_id', name='uq_cabinet_warehouse_id'),
        Index('idx_warehouse_id', 'warehouse_id'),
    )

    def __repr__(self):
        return f"<WBWarehouse {self.warehouse_id} - {self.name}>"


class WBSyncLog(Base):
    """Модель лога синхронизации Wildberries"""
    __tablename__ = "wb_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    sync_type = Column(String(50), nullable=False)  # full, orders, products, stocks, reviews
    status = Column(String(20), nullable=False)  # success, error, running
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    records_processed = Column(Integer, nullable=True, default=0)
    records_created = Column(Integer, nullable=True, default=0)
    records_updated = Column(Integer, nullable=True, default=0)
    records_skipped = Column(Integer, nullable=True, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="sync_logs")

    # Индексы
    __table_args__ = (
        Index('idx_cabinet_status', 'cabinet_id', 'status'),
        Index('idx_sync_type', 'sync_type'),
        Index('idx_started_at', 'started_at'),
    )

    def __repr__(self):
        return f"<WBSyncLog {self.cabinet_id} - {self.sync_type} - {self.status}>"