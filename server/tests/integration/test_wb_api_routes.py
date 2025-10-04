import pytest
from unittest.mock import patch, Mock
from sqlalchemy.orm import Session
from app.features.wb_api.models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview, WBAnalyticsCache, WBWarehouse
from app.features.user.models import User


@pytest.fixture
def test_user(db_session):
    """Фикстура для тестового пользователя"""
    user = User(
        id=1,
        telegram_id=123456789,
        first_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestWBCabinetAPI:
    """Тесты API кабинетов WB"""

    def test_create_cabinet_success(self, client, test_user):
        """Тест создания кабинета"""
        cabinet_data = {
            "user_id": 1,
            "api_key": "test_api_key_123",
            "name": "Test Cabinet"
        }
        
        response = client.post("/wb/cabinets/?user_id=1&api_key=test_api_key_123&name=Test Cabinet")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cabinet_id" in data

    def test_get_cabinet_success(self, client, test_user, db_session):
        """Тест получения кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        db_session.commit()
        
        response = client.get("/wb/cabinets/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cabinet_name"] == "Test Cabinet"

    def test_get_cabinets_success(self, client, test_user, db_session):
        """Тест получения списка кабинетов"""
        # Создаем тестовые кабинеты
        for i in range(3):
            cabinet = WBCabinet(
                id=i+1,
                user_id=1,
                api_key=f"test_key_{i}",
                cabinet_name=f"Test Cabinet {i}"
            )
            db_session.add(cabinet)
        db_session.commit()
        
        response = client.get("/wb/cabinets/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_delete_cabinet_success(self, client, db_session):
        """Тест удаления кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        db_session.commit()
        
        response = client.delete("/wb/cabinets/1")
        
        assert response.status_code == 200
        data = response.json()
        assert "deactivated successfully" in data["message"].lower()

    def test_sync_cabinet_success(self, client, db_session):
        """Тест синхронизации кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        db_session.commit()
        
        with patch('app.features.wb_api.sync_service.WBSyncService.sync_cabinet') as mock_sync:
            mock_sync.return_value = {"status": "success", "records_processed": 10}
            
            response = client.post("/wb/cabinets/1/sync")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_cabinet_products(self, client, db_session):
        """Тест получения товаров кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        
        # Создаем тестовые товары
        for i in range(3):
            product = WBProduct(
                cabinet_id=1,
                nm_id=525760326 + i,
                brand=f"Brand {i}",
                name=f"Product {i}"
            )
            db_session.add(product)
        db_session.commit()
        
        response = client.get("/wb/cabinets/1/products")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_cabinet_orders(self, client, test_user, db_session):
        """Тест получения заказов кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        
        # Создаем тестовые заказы
        from datetime import datetime, timezone
        for i in range(3):
            order = WBOrder(
                cabinet_id=1,
                order_id=f"1234{i}",
                nm_id=525760326,
                total_price=1000.0 + i * 100,
                finished_price=900.0 + i * 100,
                order_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
            db_session.add(order)
        db_session.commit()
        
        response = client.get("/wb/cabinets/1/orders?date_from=2024-01-01")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_cabinet_stocks(self, client, db_session):
        """Тест получения остатков кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        
        # Создаем тестовые остатки
        from datetime import datetime, timezone
        for i in range(3):
            stock = WBStock(
                cabinet_id=1,
                nm_id=525760326 + i,
                warehouse_id=658434,
                warehouse_name="Test Warehouse",
                quantity=50 + i * 10,
                last_change_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
            db_session.add(stock)
        db_session.commit()
        
        response = client.get("/wb/cabinets/1/stocks?date_from=2024-01-01")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_cabinet_reviews(self, client, db_session):
        """Тест получения отзывов кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        
        # Создаем тестовые отзывы
        for i in range(3):
            review = WBReview(
                cabinet_id=1,
                nm_id=525760326,
                review_id=f"rev_{i}",
                text=f"Review {i}",
                rating=4 + i
            )
            db_session.add(review)
        db_session.commit()
        
        response = client.get("/wb/cabinets/1/reviews")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_cabinet_warehouses(self, client, db_session):
        """Тест получения складов кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        
        # Создаем тестовые склады
        for i in range(3):
            warehouse = WBWarehouse(
                cabinet_id=1,
                warehouse_id=658434 + i,
                name=f"Warehouse {i}"
            )
            db_session.add(warehouse)
        db_session.commit()
        
        response = client.get("/wb/cabinets/1/warehouses")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_cabinet_analytics(self, client, db_session):
        """Тест получения аналитики кабинета"""
        # Создаем тестовый кабинет
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet"
        )
        db_session.add(cabinet)
        db_session.commit()
        
        with patch('app.features.wb_api.cache_manager.WBCacheManager.get_analytics_cache') as mock_analytics:
            mock_analytics.return_value = {
                "total_sales": 100,
                "total_amount": 150000.0,
                "buyout_rate": 0.85
            }
            
            response = client.get("/wb/cabinets/1/analytics?date_from=2024-01-01")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["total_sales"] == 100

    def test_health_check_success(self, client, test_user, db_session):
        """Тест проверки здоровья системы"""
        # Создаем активный кабинет для теста
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_key",
            cabinet_name="Test Cabinet",
            is_active=True
        )
        db_session.add(cabinet)
        db_session.commit()
        
        response = client.get("/wb/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["active_cabinets"] == 1