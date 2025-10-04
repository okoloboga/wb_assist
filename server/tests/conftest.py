import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

# Импорты из приложения
from app.core.database import Base, get_db
from app.core.config import settings
from app.features.user.models import User
from app.features.user.schemas import UserCreate
from main import app

# Отладочная информация
print(f"DEBUG: API_SECRET_KEY from settings: {settings.API_SECRET_KEY}")
print(f"DEBUG: Environment API_SECRET_KEY: {os.getenv('API_SECRET_KEY')}")

# Настройка тестовой базы данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Переопределяем зависимость get_db для тестов"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Подменяем зависимость
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db_session():
    """Фикстура для создания тестовой сессии БД"""
    # Очищаем и создаем таблицы заново
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Создаем сессию
    session = TestingSessionLocal()
    
    yield session
    
    # Очищаем после теста
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Фикстура для тестового клиента FastAPI"""
    with TestClient(app) as test_client:
        # Создаем обертку для автоматической передачи заголовков
        class TestClientWithAuth:
            def __init__(self, client):
                self.client = client
                # Используем ключ из переменной окружения напрямую
                secret_key = os.getenv('API_SECRET_KEY') or "test-secret-key-for-development"
                print(f"DEBUG: Using API_SECRET_KEY: {secret_key}")  # Отладочная информация
                self.headers = {
                    "X-API-SECRET-KEY": secret_key
                }
            
            def get(self, url, **kwargs):
                headers = {**self.headers, **kwargs.get('headers', {})}
                kwargs['headers'] = headers
                return self.client.get(url, **kwargs)
            
            def post(self, url, **kwargs):
                headers = {**self.headers, **kwargs.get('headers', {})}
                kwargs['headers'] = headers
                return self.client.post(url, **kwargs)
            
            def put(self, url, **kwargs):
                headers = {**self.headers, **kwargs.get('headers', {})}
                kwargs['headers'] = headers
                return self.client.put(url, **kwargs)
            
            def delete(self, url, **kwargs):
                headers = {**self.headers, **kwargs.get('headers', {})}
                kwargs['headers'] = headers
                return self.client.delete(url, **kwargs)
        
        yield TestClientWithAuth(test_client)

@pytest.fixture
def sample_user_data():
    """Фикстура с тестовыми данными пользователя"""
    return {
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Тест",
        "last_name": "Пользователь"
    }

@pytest.fixture
def sample_user_create(sample_user_data):
    """Фикстура для создания UserCreate объекта"""
    return UserCreate(**sample_user_data)

@pytest.fixture
def created_user(db_session, sample_user_create):
    """Фикстура с созданным пользователем в БД"""
    user = User(
        telegram_id=sample_user_create.telegram_id,
        username=sample_user_create.username,
        first_name=sample_user_create.first_name,
        last_name=sample_user_create.last_name
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def multiple_users(db_session):
    """Фикстура с несколькими пользователями в БД"""
    users_data = [
        {
            "telegram_id": 111111111,
            "username": "user1",
            "first_name": "Пользователь",
            "last_name": "Первый"
        },
        {
            "telegram_id": 222222222,
            "username": "user2", 
            "first_name": "Пользователь",
            "last_name": "Второй"
        },
        {
            "telegram_id": 333333333,
            "username": None,
            "first_name": "Пользователь",
            "last_name": "Третий"
        }
    ]
    
    users = []
    for user_data in users_data:
        user = User(**user_data)
        db_session.add(user)
        users.append(user)
    
    db_session.commit()
    for user in users:
        db_session.refresh(user)
    
    return users