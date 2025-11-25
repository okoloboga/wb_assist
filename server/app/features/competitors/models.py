"""
Модели базы данных для работы с конкурентами Wildberries
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, UniqueConstraint, Index, func
from sqlalchemy.orm import relationship
from ...core.database import Base


class CompetitorLink(Base):
    """Модель ссылки на конкурента (бренд или селлер)"""
    __tablename__ = "competitor_links"
    
    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id", ondelete="CASCADE"), nullable=False, index=True)
    competitor_url = Column(Text, nullable=False)
    competitor_name = Column(String(255), nullable=True)  # Извлекается из данных скрапинга
    status = Column(String(20), nullable=False, default='pending')  # pending, scraping, completed, error
    products_count = Column(Integer, default=0, nullable=False)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    next_update_at = Column(DateTime(timezone=True), nullable=True)  # Время следующего обновления
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    products = relationship("CompetitorProduct", back_populates="competitor_link", cascade="all, delete-orphan")
    semantic_cores = relationship("CompetitorSemanticCore", back_populates="competitor_link", cascade="all, delete-orphan")
    
    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('cabinet_id', 'competitor_url', name='uq_cabinet_competitor_url'),
        Index('idx_competitor_cabinet', 'cabinet_id'),
        Index('idx_competitor_status', 'status'),
        Index('idx_competitor_next_update', 'next_update_at'),
    )
    
    def __repr__(self):
        return f"<CompetitorLink {self.id} - {self.competitor_name or self.competitor_url[:50]}>"


class CompetitorProduct(Base):
    """Модель товара конкурента"""
    __tablename__ = "competitor_products"
    
    id = Column(Integer, primary_key=True, index=True)
    competitor_link_id = Column(Integer, ForeignKey("competitor_links.id", ondelete="CASCADE"), nullable=False, index=True)
    nm_id = Column(String(50), nullable=False)  # Артикул товара WB
    product_url = Column(Text, nullable=False)
    name = Column(Text, nullable=True)
    current_price = Column(Numeric(10, 2), nullable=True)
    original_price = Column(Numeric(10, 2), nullable=True)
    brand = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    rating = Column(Numeric(3, 2), nullable=True)
    description = Column(Text, nullable=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    competitor_link = relationship("CompetitorLink", back_populates="products")
    
    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint('competitor_link_id', 'nm_id', name='uq_competitor_product'),
        Index('idx_competitor_product_link', 'competitor_link_id'),
        Index('idx_competitor_product_nm', 'nm_id'),
    )
    
    def __repr__(self):
        return f"<CompetitorProduct {self.nm_id} - {self.name[:50] if self.name else 'N/A'}>"


class CompetitorSemanticCore(Base):
    """Модель семантического ядра, собранного для конкурента по категории"""
    __tablename__ = "competitor_semantic_cores"

    id = Column(Integer, primary_key=True, index=True)
    competitor_link_id = Column(Integer, ForeignKey("competitor_links.id", ondelete="CASCADE"), nullable=False, index=True)
    category_name = Column(String(255), nullable=False)
    core_data = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default='pending')  # pending, processing, completed, error
    error_message = Column(Text, nullable=True) # New column
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Связи
    competitor_link = relationship("CompetitorLink", back_populates="semantic_cores")

    # Индексы и ограничения
    __table_args__ = (
        Index('idx_semantic_core_link_category', 'competitor_link_id', 'category_name'),
    )

    def __repr__(self):
        return f"<CompetitorSemanticCore {self.id} for competitor {self.competitor_link_id}>"

