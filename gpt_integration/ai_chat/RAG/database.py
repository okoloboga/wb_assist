"""
Database configuration for RAG system.

Provides SQLAlchemy engine, session factory, and dependency injection for RAG tables.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Приоритет 1: RAG_VECTOR_DB_URL (отдельная БД для векторов)
# Приоритет 2: DATABASE_URL (основная БД, может быть та же)
RAG_VECTOR_DB_URL = os.getenv(
    "RAG_VECTOR_DB_URL",
    os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
)

# Создание engine для векторной БД
# Параметры для оптимизации:
# - pool_pre_ping=True - проверка соединения перед использованием
# - pool_size=5 - размер пула соединений
# - max_overflow=10 - максимальное количество дополнительных соединений
rag_engine = create_engine(
    RAG_VECTOR_DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False  # Установить True для отладки SQL запросов
)

# Session factory
RAGSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=rag_engine
)

# Base для моделей RAG
RAGBase = declarative_base()


def get_rag_db() -> Generator[Session, None, None]:
    """
    Dependency injection для получения сессии БД RAG.
    
    Использование:
        db: Session = Depends(get_rag_db)
    
    Yields:
        Session: SQLAlchemy database session для RAG
    """
    db = RAGSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_rag_db() -> None:
    """
    Инициализация БД: создание расширения pgvector и всех таблиц.
    
    Вызывается при старте приложения.
    """
    from sqlalchemy import text
    from .models import RAGMetadata, RAGEmbedding, RAGIndexStatus
    
    # Создать расширение pgvector, если его нет
    with rag_engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        except Exception as e:
            # Если расширение уже существует или есть другие проблемы, просто логируем
            print(f"Warning: Could not create vector extension: {e}")
            conn.rollback()
    
    # Создать все таблицы
    RAGBase.metadata.create_all(bind=rag_engine)



















