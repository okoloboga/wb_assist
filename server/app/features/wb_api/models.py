from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

# Используем Base из database.py
from ...core.database import Base

# Импортируем WBSales для связи
from .models_sales import WBSales
from .models_cabinet_users import CabinetUser


class WBCabinet(Base):
    """Модель WB кабинета"""
    __tablename__ = "wb_cabinets"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(500), nullable=False, unique=True)  # Уникальный API ключ
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    products = relationship("WBProduct", back_populates="cabinet")
    orders = relationship("WBOrder", back_populates="cabinet")
    stocks = relationship("WBStock", back_populates="cabinet")
    reviews = relationship("WBReview", back_populates="cabinet")
    sales = relationship("WBSales", back_populates="cabinet")
    analytics_cache = relationship("WBAnalyticsCache", back_populates="cabinet")
    cabinet_users = relationship("CabinetUser", back_populates="cabinet")

    def __repr__(self):
        return f"<WBCabinet {self.id} - {self.name}>"


class WBProduct(Base):
    """Модель товара Wildberries"""
    __tablename__ = "wb_products"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    nm_id = Column(Integer, nullable=False, index=True)
    name = Column(String(500), nullable=True)
    vendor_code = Column(String(100), nullable=True)
    brand = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    price = Column(Float, nullable=True)
    discount_price = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    reviews_count = Column(Integer, nullable=True)
    in_stock = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="products")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'nm_id', name='uq_cabinet_nm_id'),
        Index('idx_brand_category', 'brand', 'category'),
        Index('idx_price', 'price'),
        Index('idx_rating', 'rating'),
    )

    def __repr__(self):
        return f"<WBProduct {self.nm_id} - {self.name}>"


class WBOrder(Base):
    """Модель заказа Wildberries"""
    __tablename__ = "wb_orders"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    order_id = Column(String(100), nullable=True, index=True)  # ИСПРАВЛЕНО: nullable=True
    nm_id = Column(Integer, nullable=False, index=True)
    article = Column(String(100), nullable=True)
    name = Column(String(500), nullable=True)
    brand = Column(String(255), nullable=True)
    size = Column(String(50), nullable=True)
    barcode = Column(String(100), nullable=True)
    # Поля категории для расчета комиссии
    category = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    # Поля комиссии
    commission_percent = Column(Float, nullable=True)
    commission_amount = Column(Float, nullable=True)
    
    # Поля складов (из WB API)
    warehouse_from = Column(String(255), nullable=True)      # warehouseName
    warehouse_to = Column(String(255), nullable=True)       # regionName
    
    # Поля цен и СПП (из WB API)
    spp_percent = Column(Float, nullable=True)               # spp
    customer_price = Column(Float, nullable=True)            # finishedPrice
    discount_percent = Column(Float, nullable=True)         # discountPercent
    
    # Поля логистики (рассчитывается)
    logistics_amount = Column(Float, nullable=True)
    
    order_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="orders")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'order_id', name='uq_cabinet_order_id'),
        Index('idx_nm_id', 'nm_id'),
        Index('idx_order_date', 'order_date'),
        Index('idx_order_status', 'status'),
    )

    def __repr__(self):
        return f"<WBOrder {self.order_id} - {self.name}>"


class WBStock(Base):
    """Модель остатков Wildberries"""
    __tablename__ = "wb_stocks"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    nm_id = Column(Integer, nullable=False, index=True)
    article = Column(String(100), nullable=True)
    name = Column(String(500), nullable=True)
    brand = Column(String(255), nullable=True)
    size = Column(String(50), nullable=True)
    barcode = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=True)
    in_way_to_client = Column(Integer, nullable=True)
    in_way_from_client = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=True)  # ИСПРАВЛЕНО: nullable=True
    warehouse_name = Column(String(255), nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)
    
    # Новые поля из WB API остатков
    category = Column(String(255), nullable=True)            # category
    subject = Column(String(255), nullable=True)             # subject
    price = Column(Float, nullable=True)                     # Price
    discount = Column(Float, nullable=True)                  # Discount
    quantity_full = Column(Integer, nullable=True)           # quantityFull
    is_supply = Column(Boolean, nullable=True)              # isSupply
    is_realization = Column(Boolean, nullable=True)          # isRealization
    sc_code = Column(String(50), nullable=True)             # SCCode
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="stocks")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'nm_id', 'warehouse_id', name='uq_cabinet_nm_warehouse'),
        Index('idx_quantity', 'quantity'),
        Index('idx_warehouse', 'warehouse_id'),
        Index('idx_last_updated', 'last_updated'),
    )

    def __repr__(self):
        return f"<WBStock {self.nm_id} - {self.quantity} шт>"


class WBReview(Base):
    """Модель отзыва Wildberries"""
    __tablename__ = "wb_reviews"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    nm_id = Column(Integer, nullable=True, index=True)  # ИСПРАВЛЕНО: nullable=True
    review_id = Column(String(100), nullable=False)
    text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    is_answered = Column(Boolean, default=False, nullable=False)
    created_date = Column(DateTime(timezone=True), nullable=True)
    updated_date = Column(DateTime(timezone=True), nullable=True)
    
    # Новые поля из WB API отзывов
    pros = Column(Text, nullable=True)                       # pros
    cons = Column(Text, nullable=True)                        # cons
    user_name = Column(String(255), nullable=True)             # userName
    color = Column(String(100), nullable=True)                # color
    bables = Column(Text, nullable=True)                        # bables (JSON array)
    matching_size = Column(String(50), nullable=True)          # matchingSize
    was_viewed = Column(Boolean, nullable=True)                # wasViewed
    supplier_feedback_valuation = Column(Integer, nullable=True)  # supplierFeedbackValuation
    supplier_product_valuation = Column(Integer, nullable=True)    # supplierProductValuation
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
    name = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'warehouse_id', name='uq_cabinet_warehouse_id'),
        Index('idx_warehouse_id', 'warehouse_id'),
        Index('idx_is_active', 'is_active'),
    )

    def __repr__(self):
        return f"<WBWarehouse {self.warehouse_id} - {self.name}>"


class WBSyncLog(Base):
    """Модель логов синхронизации"""
    __tablename__ = "wb_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id"), nullable=False, index=True)
    sync_type = Column(String(50), nullable=False)  # products, orders, stocks, reviews
    status = Column(String(20), nullable=False)  # success, error, partial
    records_processed = Column(Integer, nullable=True)
    records_created = Column(Integer, nullable=True)
    records_updated = Column(Integer, nullable=True)
    records_errors = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    cabinet = relationship("WBCabinet")

    # Индексы и ограничения
    __table_args__ = (
        Index('idx_cabinet_sync_type', 'cabinet_id', 'sync_type'),
        Index('idx_sync_status', 'status'),
        Index('idx_sync_started_at', 'started_at'),
    )

    def __repr__(self):
        return f"<WBSyncLog {self.sync_type} - {self.status}>"