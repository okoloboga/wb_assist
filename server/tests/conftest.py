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
from app.features.wb_api.models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview, WBAnalyticsCache
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

# ===== ФИКСТУРЫ ДЛЯ BOT_API ТЕСТОВ =====

@pytest.fixture
def test_user_with_cabinet(db_session):
    """Фикстура с пользователем и WB кабинетом"""
    # Создаем пользователя
    user = User(
        telegram_id=12345,
        username="test_user",
        first_name="Тест",
        last_name="Пользователь"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Создаем WB кабинет
    cabinet = WBCabinet(
        user_id=user.id,
        api_key="test_api_key_12345",
        cabinet_name="Test Cabinet",
        is_active=True
    )
    db_session.add(cabinet)
    db_session.commit()
    db_session.refresh(cabinet)
    
    return user, cabinet

@pytest.fixture
def test_orders_data(db_session, test_user_with_cabinet):
    """Фикстура с тестовыми заказами"""
    user, cabinet = test_user_with_cabinet
    
    orders_data = [
        {
            "cabinet_id": cabinet.id,
            "order_id": "12345",
            "total_price": 1500.0,
            "order_date": datetime.now(),
            "nm_id": 1001,
            "is_cancel": False,
            "is_realization": False,
            "brand": "Test Brand",
            "name": "Тестовый товар 1"
        },
        {
            "cabinet_id": cabinet.id,
            "order_id": "12346", 
            "total_price": 2300.0,
            "order_date": datetime.now(),
            "nm_id": 1002,
            "is_cancel": False,
            "is_realization": False,
            "brand": "Test Brand",
            "name": "Тестовый товар 2"
        }
    ]
    
    orders = []
    for order_data in orders_data:
        order = WBOrder(**order_data)
        db_session.add(order)
        orders.append(order)
    
    db_session.commit()
    for order in orders:
        db_session.refresh(order)
    
    return orders

@pytest.fixture
def test_products_data(db_session, test_user_with_cabinet):
    """Фикстура с тестовыми товарами"""
    user, cabinet = test_user_with_cabinet
    
    products_data = [
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1001,
            "name": "Тестовый товар 1",
            "brand": "Test Brand",
            "subject": "Электроника",
            "is_active": True
        },
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1002,
            "name": "Тестовый товар 2", 
            "brand": "Test Brand",
            "subject": "Одежда",
            "is_active": True
        }
    ]
    
    products = []
    for product_data in products_data:
        product = WBProduct(**product_data)
        db_session.add(product)
        products.append(product)
    
    db_session.commit()
    for product in products:
        db_session.refresh(product)
    
    return products

@pytest.fixture
def test_stocks_data(db_session, test_user_with_cabinet):
    """Фикстура с тестовыми остатками"""
    user, cabinet = test_user_with_cabinet
    
    stocks_data = [
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1001,
            "warehouse_id": 1,
            "size": "S",
            "quantity": 5,
            "last_change_date": datetime.now()
        },
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1001,
            "warehouse_id": 1, 
            "size": "M",
            "quantity": 0,  # Критический остаток
            "last_change_date": datetime.now()
        },
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1002,
            "warehouse_id": 1,
            "size": "L",
            "quantity": 2,
            "last_change_date": datetime.now()
        }
    ]
    
    stocks = []
    for stock_data in stocks_data:
        stock = WBStock(**stock_data)
        db_session.add(stock)
        stocks.append(stock)
    
    db_session.commit()
    for stock in stocks:
        db_session.refresh(stock)
    
    return stocks

@pytest.fixture
def test_reviews_data(db_session, test_user_with_cabinet):
    """Фикстура с тестовыми отзывами"""
    user, cabinet = test_user_with_cabinet
    
    reviews_data = [
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1001,
            "review_id": "rev_001",
            "rating": 5,
            "text": "Отличный товар!",
            "created_at": datetime.now(),
            "is_answered": False
        },
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1001,
            "review_id": "rev_002",
            "rating": 3,
            "text": "Нормально",
            "created_at": datetime.now(),
            "is_answered": True
        },
        {
            "cabinet_id": cabinet.id,
            "nm_id": 1002,
            "review_id": "rev_003",
            "rating": 4,
            "text": "Хорошо",
            "created_at": datetime.now(),
            "is_answered": False
        }
    ]
    
    reviews = []
    for review_data in reviews_data:
        review = WBReview(**review_data)
        db_session.add(review)
        reviews.append(review)
    
    db_session.commit()
    for review in reviews:
        db_session.refresh(review)
    
    return reviews

@pytest.fixture
def mock_redis():
    """Фикстура с моком Redis"""
    from unittest.mock import AsyncMock
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.ping.return_value = True
    redis.info.return_value = {"used_memory": 1024}
    redis.dbsize.return_value = 0
    redis.scan_iter.return_value = []
    return redis

@pytest.fixture
def mock_wb_client():
    """Фикстура с моком WB API клиента"""
    from unittest.mock import AsyncMock, patch
    
    with patch('app.features.wb_api.client.WBAPIClient') as mock:
        client = AsyncMock()
        client.get_orders.return_value = [
            {"orderId": "123", "totalPrice": 1000, "createdAt": "2024-01-01T10:00:00Z"}
        ]
        client.get_stocks.return_value = [
            {"nmId": 1001, "quantity": 5, "warehouseId": 1}
        ]
        client.get_reviews.return_value = {
            "data": {"feedbacks": [{"id": "rev_001", "rating": 5}]}
        }
        mock.return_value = client
        yield client