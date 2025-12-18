"""
SQLAlchemy models for RAG system.

Models:
    - RAGMetadata: Метаданные и исходный текст чанков
    - RAGEmbedding: Векторные представления документов
    - RAGIndexStatus: Статус индексации для каждого кабинета
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .database import RAGBase


class RAGMetadata(RAGBase):
    """
    Метаданные и исходный текст чанков.

    Связывает векторные представления с исходными данными из основной БД.
    """
    __tablename__ = "rag_metadata"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, nullable=False, index=True)
    source_table = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=False)
    chunk_type = Column(String(20), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash для hash-based change detection
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    embeddings = relationship("RAGEmbedding", back_populates="rag_metadata", cascade="all, delete-orphan")

    # Индексы и ограничения
    __table_args__ = (
        Index('idx_rag_metadata_cabinet_type', 'cabinet_id', 'chunk_type'),
        Index('idx_rag_metadata_source', 'source_table', 'source_id'),
        Index('idx_rag_metadata_cabinet_source', 'cabinet_id', 'source_table', 'source_id'),  # Для full rebuild
        UniqueConstraint('cabinet_id', 'source_table', 'source_id', name='uq_rag_metadata_cabinet_source'),
    )
    
    def __repr__(self) -> str:
        return f"<RAGMetadata(id={self.id}, cabinet_id={self.cabinet_id}, chunk_type={self.chunk_type})>"


class RAGEmbedding(RAGBase):
    """
    Векторные представления документов.
    
    Хранит embedding размерности 1536 (для OpenAI text-embedding-3-small).
    """
    __tablename__ = "rag_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    embedding = Column(Vector(1536), nullable=False)
    metadata_id = Column(Integer, ForeignKey("rag_metadata.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    rag_metadata = relationship("RAGMetadata", back_populates="embeddings")
    
    def __repr__(self) -> str:
        return f"<RAGEmbedding(id={self.id}, metadata_id={self.metadata_id})>"


class RAGIndexStatus(RAGBase):
    """
    Статус индексации для каждого кабинета.
    
    Отслеживает прогресс индексации и предотвращает параллельную обработку.
    """
    __tablename__ = "rag_index_status"
    
    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, unique=True, nullable=False, index=True)
    last_indexed_at = Column(DateTime(timezone=True), nullable=True)
    last_incremental_at = Column(DateTime(timezone=True), nullable=True)
    indexing_status = Column(String(20), default='pending', nullable=False)
    total_chunks = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<RAGIndexStatus(cabinet_id={self.cabinet_id}, status={self.indexing_status}, chunks={self.total_chunks})>"









