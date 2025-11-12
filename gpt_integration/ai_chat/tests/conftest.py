"""
Pytest configuration and fixtures for AI Chat Service tests.
"""

import os
import sys
import pytest
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for tests BEFORE importing service
os.environ["API_SECRET_KEY"] = "test-api-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["TESTING"] = "1"  # Disable DB init in startup event

from gpt_integration.ai_chat.app.database import Base
from gpt_integration.ai_chat.app.service import app
from gpt_integration.ai_chat.app.models import AIChatRequest, AIChatDailyLimit


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine (in-memory SQLite)."""
    # Use StaticPool to ensure all connections use the same in-memory database
    # This is critical for TestClient which creates connections in different threads
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db_engine):
    """Create a test client with test database."""
    from gpt_integration.ai_chat.app.database import get_db
    
    # Ensure tables exist in test database
    Base.metadata.create_all(bind=test_db_engine)
    
    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    
    def override_get_db():
        """Override get_db to use test database."""
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client (startup events will use default DB, so we override get_db first)
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def sample_telegram_id():
    """Sample Telegram user ID."""
    return 123456789


@pytest.fixture
def sample_user_message():
    """Sample user message."""
    return "Как увеличить конверсию карточки товара на Wildberries?"


@pytest.fixture
def sample_ai_response():
    """Sample AI response."""
    return (
        "📊 Для увеличения конверсии карточки товара на Wildberries:\n\n"
        "1. ✅ Качественные фото (минимум 5-7 изображений)\n"
        "2. 📝 Подробное описание с ключевыми словами\n"
        "3. ⭐ Работайте над отзывами\n"
        "4. 💰 Конкурентная цена"
    )


@pytest.fixture
def sample_chat_request(test_db_session, sample_telegram_id):
    """Create a sample chat request in database."""
    request = AIChatRequest(
        telegram_id=sample_telegram_id,
        user_id=None,
        message="Тестовый вопрос",
        response="Тестовый ответ",
        tokens_used=50,
        request_date=date.today()
    )
    test_db_session.add(request)
    test_db_session.commit()
    test_db_session.refresh(request)
    return request


@pytest.fixture
def sample_daily_limit(test_db_session, sample_telegram_id):
    """Create a sample daily limit record in database."""
    limit = AIChatDailyLimit(
        telegram_id=sample_telegram_id,
        request_count=5,
        last_reset_date=date.today()
    )
    test_db_session.add(limit)
    test_db_session.commit()
    test_db_session.refresh(limit)
    return limit


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def api_key():
    """API key for testing."""
    return os.getenv("API_SECRET_KEY", "test-api-key")


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "response": "Это тестовый ответ от AI",
        "tokens_used": 100
    }


# ============================================================================
# Helper Functions
# ============================================================================

@pytest.fixture
def create_chat_history(test_db_session, sample_telegram_id):
    """Factory fixture to create multiple chat history records."""
    def _create_history(count: int = 5):
        records = []
        for i in range(count):
            record = AIChatRequest(
                telegram_id=sample_telegram_id,
                user_id=None,
                message=f"Вопрос {i+1}",
                response=f"Ответ {i+1}",
                tokens_used=50 + i * 10,
                request_date=date.today()
            )
            test_db_session.add(record)
            records.append(record)
        test_db_session.commit()
        return records
    return _create_history


@pytest.fixture
def headers(api_key):
    """Default headers with API key."""
    return {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }

