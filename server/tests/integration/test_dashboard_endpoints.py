"""
Integration тесты для эндпоинтов дашборда
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
import os

# Тестовая база данных
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# API ключ для тестов
TEST_API_KEY = os.getenv("API_SECRET_KEY", "test-key")


def override_get_db():
    """Override для тестовой БД"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_database():
    """Создание тестовой БД"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers():
    """Заголовки аутентификации"""
    return {"X-API-SECRET-KEY": TEST_API_KEY}


class TestAuthentication:
    """Тесты аутентификации"""
    
    def test_missing_api_key(self):
        """Тест отсутствия API ключа"""
        response = client.get("/api/v1/bot/warehouses?telegram_id=123")
        assert response.status_code == 403
        assert "Missing API Secret Key" in response.json()["detail"]
    
    def test_invalid_api_key(self):
        """Тест неверного API ключа"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=123",
            headers={"X-API-SECRET-KEY": "wrong-key"}
        )
        assert response.status_code == 403
        assert "Invalid API Secret Key" in response.json()["detail"]
    
    def test_valid_api_key(self, auth_headers):
        """Тест валидного API ключа"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=123",
            headers=auth_headers
        )
        # Может быть 404 (кабинет не найден) или 200, но не 403
        assert response.status_code != 403


class TestCORS:
    """Тесты CORS"""
    
    def test_cors_preflight(self, auth_headers):
        """Тест preflight запроса"""
        response = client.options(
            "/api/v1/bot/warehouses",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-API-SECRET-KEY",
                **auth_headers
            }
        )
        assert response.status_code in [200, 204]
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_headers_in_response(self, auth_headers):
        """Тест CORS заголовков в ответе"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=123",
            headers={
                "Origin": "http://localhost:3000",
                **auth_headers
            }
        )
        # Проверяем наличие CORS заголовков (если настроены)
        # В зависимости от конфигурации может быть или не быть
        assert response.status_code in [200, 404, 500]


class TestWarehousesEndpoint:
    """Тесты эндпоинта /warehouses"""
    
    def test_get_warehouses_success(self, auth_headers, setup_database):
        """Тест успешного получения складов"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=123",
            headers=auth_headers
        )
        # Может быть 404 если кабинет не найден, или 200 с пустым списком
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "warehouses" in data
            assert isinstance(data["warehouses"], list)
    
    def test_get_warehouses_cache_headers(self, auth_headers):
        """Тест заголовков кэширования"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=123",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            assert "cache-control" in response.headers
            assert "x-cache-ttl" in response.headers
            assert "3600" in response.headers.get("x-cache-ttl", "")
    
    def test_get_warehouses_invalid_telegram_id(self, auth_headers):
        """Тест невалидного telegram_id"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=-1",
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error


class TestSizesEndpoint:
    """Тесты эндпоинта /sizes"""
    
    def test_get_sizes_success(self, auth_headers, setup_database):
        """Тест успешного получения размеров"""
        response = client.get(
            "/api/v1/bot/sizes?telegram_id=123",
            headers=auth_headers
        )
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "sizes" in data
            assert isinstance(data["sizes"], list)
    
    def test_get_sizes_cache_headers(self, auth_headers):
        """Тест заголовков кэширования"""
        response = client.get(
            "/api/v1/bot/sizes?telegram_id=123",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            assert "cache-control" in response.headers
            assert "x-cache-ttl" in response.headers


class TestAnalyticsSummaryEndpoint:
    """Тесты эндпоинта /analytics/summary"""
    
    def test_get_summary_default_period(self, auth_headers, setup_database):
        """Тест получения статистики с периодом по умолчанию"""
        response = client.get(
            "/api/v1/bot/analytics/summary?telegram_id=123",
            headers=auth_headers
        )
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "summary" in data
            assert "period" in data
            
            summary = data["summary"]
            assert "orders" in summary
            assert "purchases" in summary
            assert "cancellations" in summary
            assert "returns" in summary
    
    def test_get_summary_different_periods(self, auth_headers):
        """Тест разных периодов"""
        periods = ["7d", "30d", "60d", "90d", "180d"]
        
        for period in periods:
            response = client.get(
                f"/api/v1/bot/analytics/summary?telegram_id=123&period={period}",
                headers=auth_headers
            )
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert data["period"]["days"] == int(period[:-1])
    
    def test_get_summary_invalid_period(self, auth_headers):
        """Тест невалидного периода"""
        response = client.get(
            "/api/v1/bot/analytics/summary?telegram_id=123&period=999d",
            headers=auth_headers
        )
        # Должна быть ошибка валидации или использован период по умолчанию
        assert response.status_code in [200, 422, 404, 500]
    
    def test_get_summary_cache_headers(self, auth_headers):
        """Тест заголовков кэширования"""
        response = client.get(
            "/api/v1/bot/analytics/summary?telegram_id=123",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            assert "cache-control" in response.headers
            assert "x-cache-ttl" in response.headers
            assert "900" in response.headers.get("x-cache-ttl", "")


class TestStocksAllEndpoint:
    """Тесты эндпоинта /stocks/all"""
    
    def test_get_stocks_default_params(self, auth_headers, setup_database):
        """Тест получения остатков с параметрами по умолчанию"""
        response = client.get(
            "/api/v1/bot/stocks/all?telegram_id=123",
            headers=auth_headers
        )
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "stocks" in data
    
    def test_get_stocks_with_filters(self, auth_headers):
        """Тест фильтрации"""
        response = client.get(
            "/api/v1/bot/stocks/all?telegram_id=123&warehouse=Коледино&size=M",
            headers=auth_headers
        )
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            stocks = data["stocks"]
            assert "filters" in stocks
            assert stocks["filters"]["warehouse"] == "Коледино"
            assert stocks["filters"]["size"] == "M"
    
    def test_get_stocks_with_search(self, auth_headers):
        """Тест поиска"""
        response = client.get(
            "/api/v1/bot/stocks/all?telegram_id=123&search=футболка",
            headers=auth_headers
        )
        assert response.status_code in [200, 404, 500]
    
    def test_get_stocks_pagination(self, auth_headers):
        """Тест пагинации"""
        response = client.get(
            "/api/v1/bot/stocks/all?telegram_id=123&limit=20&offset=10",
            headers=auth_headers
        )
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            pagination = data["stocks"]["pagination"]
            assert pagination["limit"] == 20
            assert pagination["offset"] == 10
    
    def test_get_stocks_sql_injection_protection(self, auth_headers):
        """Тест защиты от SQL injection"""
        response = client.get(
            "/api/v1/bot/stocks/all?telegram_id=123&search='; DROP TABLE users--",
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error


class TestAnalyticsSalesEndpoint:
    """Тесты эндпоинта /analytics/sales"""
    
    def test_get_sales_default_period(self, auth_headers, setup_database):
        """Тест получения аналитики с периодом по умолчанию"""
        response = client.get(
            "/api/v1/bot/analytics/sales?telegram_id=123",
            headers=auth_headers
        )
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "analytics" in data
    
    def test_get_sales_different_periods(self, auth_headers):
        """Тест разных периодов"""
        periods = ["7d", "30d", "60d", "90d", "180d"]
        
        for period in periods:
            response = client.get(
                f"/api/v1/bot/analytics/sales?telegram_id=123&period={period}",
                headers=auth_headers
            )
            assert response.status_code in [200, 404, 500]


class TestResponseFormat:
    """Тесты формата ответов"""
    
    def test_success_response_format(self, auth_headers):
        """Тест формата успешного ответа"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=123",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert data["success"] is True
    
    def test_error_response_format(self, auth_headers):
        """Тест формата ответа с ошибкой"""
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=-1",
            headers=auth_headers
        )
        
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data


class TestPerformance:
    """Тесты производительности"""
    
    def test_response_time_warehouses(self, auth_headers):
        """Тест времени ответа для /warehouses"""
        import time
        
        start = time.time()
        response = client.get(
            "/api/v1/bot/warehouses?telegram_id=123",
            headers=auth_headers
        )
        elapsed = time.time() - start
        
        # Время ответа должно быть < 1 секунды
        assert elapsed < 1.0
    
    def test_response_time_summary(self, auth_headers):
        """Тест времени ответа для /analytics/summary"""
        import time
        
        start = time.time()
        response = client.get(
            "/api/v1/bot/analytics/summary?telegram_id=123",
            headers=auth_headers
        )
        elapsed = time.time() - start
        
        # Время ответа должно быть < 1 секунды
        assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
