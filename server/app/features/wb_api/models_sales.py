"""
Модель для продаж и возвратов Wildberries
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, func, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from ...core.database import Base

# Импортируем func для работы с БД
from sqlalchemy import func


class WBSales(Base):
    """Модель продаж и возвратов Wildberries"""
    __tablename__ = "wb_sales"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id", ondelete="CASCADE"), nullable=False, index=True)
    sale_id = Column(String(100), nullable=False, index=True)  # srid из WB API
    order_id = Column(String(100), nullable=True, index=True)
    nm_id = Column(Integer, nullable=False, index=True)
    product_name = Column(String(500), nullable=True)  # subject из WB API
    brand = Column(String(255), nullable=True)
    size = Column(String(50), nullable=True)  # techSize из WB API
    barcode = Column(String(100), nullable=True)  # barcode из WB API
    amount = Column(Float, nullable=True)  # totalPrice из WB API
    sale_date = Column(DateTime(timezone=True), nullable=True)  # date из WB API
    type = Column(String(20), nullable=False, index=True)  # 'buyout' или 'return'
    status = Column(String(50), nullable=True)
    is_cancel = Column(Boolean, nullable=True)  # isCancel из WB API
    last_change_date = Column(DateTime(timezone=True), nullable=True)  # lastChangeDate из WB API
    
    # Дополнительные поля для аналитики
    commission_percent = Column(Float, nullable=True)
    commission_amount = Column(Float, nullable=True)
    
    # Поля для детальной финансовой информации (как в заказах)
    spp_percent = Column(Float, nullable=True)  # СПП процент
    customer_price = Column(Float, nullable=True)  # Цена для покупателя
    discount_percent = Column(Float, nullable=True)  # Скидка в процентах
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связи
    cabinet = relationship("WBCabinet", back_populates="sales")

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'sale_id', 'type', name='uq_cabinet_sale_type'),
        Index('idx_sales_nm_id', 'nm_id'),
        Index('idx_sales_date', 'sale_date'),
        Index('idx_sales_type', 'type'),
        Index('idx_sales_is_cancel', 'is_cancel'),
    )

    def __repr__(self):
        return f"<WBSales {self.sale_id} - {self.product_name} ({self.type})>"
