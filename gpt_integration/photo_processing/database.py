"""
Database configuration for Photo Processing Service.

Provides SQLAlchemy engine, session factory, and dependency injection for FastAPI.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator


# Database URL priority:
# 1. PHOTO_PROCESSING_DATABASE_URL (dedicated for this service)
# 2. DATABASE_URL (shared with main server)
# 3. SQLite fallback for development
DATABASE_URL = os.getenv(
    "PHOTO_PROCESSING_DATABASE_URL",
    os.getenv("DATABASE_URL", "sqlite:///./photo_processing.db")
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connection before using
    echo=False,  # Don't log SQL queries
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.
    
    Called on application startup.
    """
    Base.metadata.create_all(bind=engine)







