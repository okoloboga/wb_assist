"""
Unit тесты для Bot API эндпоинтов продаж
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.main import app
from app.features.wb_api.models import WBCabinet
from app.features.wb_api.models_sales import WBSales


class TestBotSalesAPI:
    """Тесты для Bot API эндпоинтов продаж"""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных"""
        return Mock()
    
    @pytest.fixture
    def sample_cabinet(self):
        """Пример кабинета"""
        cabinet = Mock(spec=WBCabinet)
        cabinet.id = 1
        cabinet.user_id = 123
        return cabinet
    
    @pytest.fixture
    def sample_sales(self):
        """Пример продаж"""
        sales = []
        for i in range(3):
            sale = Mock(spec=WBSales)
            sale.id = i + 1
            sale.sale_id = f"sale_{i + 1}"
            sale.order_id = f"order_{i + 1}"
            sale.nm_id = 12345 + i
            sale.product_name = f"Product {i + 1}"
            sale.brand = f"Brand {i + 1}"
            sale.size = "M"
            sale.amount = 1000.0 + i * 100
            sale.sale_date = datetime.now(timezone.utc)
            sale.type = "buyout" if i % 2 == 0 else "return"
            sale.status = "completed"
            sale.is_cancel = False
            sales.append(sale)
        return sales
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_recent_sales_success(self, mock_get_db, client, mock_db, sample_cabinet, sample_sales):
        """Тест успешного получения последних продаж"""
        mock_get_db.return_value = mock_db
        
        # Мокаем запросы к БД
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        # Мокаем WBSalesCRUD
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_recent_sales.return_value = sample_sales
            mock_crud.get_sales_statistics.return_value = {
                "total_count": 3,
                "total_amount": 3200.0,
                "buyouts_count": 2,
                "buyouts_amount": 2200.0,
                "returns_count": 1,
                "returns_amount": 1000.0,
                "buyout_rate": 66.7
            }
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/api/v1/bot/sales/recent?user_id=123&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "sales" in data["data"]
        assert "statistics" in data["data"]
        assert len(data["data"]["sales"]) == 3
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_recent_sales_cabinet_not_found(self, mock_get_db, client, mock_db):
        """Тест получения продаж при отсутствии кабинета"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.get("/api/v1/bot/sales/recent?user_id=999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Cabinet not found" in data["detail"]
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_buyouts_success(self, mock_get_db, client, mock_db, sample_cabinet, sample_sales):
        """Тест успешного получения выкупов"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        # Фильтруем только выкупы
        buyouts = [sale for sale in sample_sales if sale.type == "buyout"]
        
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_buyouts.return_value = buyouts
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/api/v1/bot/sales/buyouts?user_id=123&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "buyouts" in data["data"]
        assert "count" in data["data"]
        assert data["data"]["count"] == len(buyouts)
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_returns_success(self, mock_get_db, client, mock_db, sample_cabinet, sample_sales):
        """Тест успешного получения возвратов"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        # Фильтруем только возвраты
        returns = [sale for sale in sample_sales if sale.type == "return"]
        
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_returns.return_value = returns
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/api/v1/bot/sales/returns?user_id=123&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "returns" in data["data"]
        assert "count" in data["data"]
        assert data["data"]["count"] == len(returns)
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_sales_statistics_success(self, mock_get_db, client, mock_db, sample_cabinet):
        """Тест успешного получения статистики продаж"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_sales_statistics.return_value = {
                "total_count": 10,
                "total_amount": 15000.0,
                "buyouts_count": 8,
                "buyouts_amount": 12000.0,
                "returns_count": 2,
                "returns_amount": 3000.0,
                "buyout_rate": 80.0
            }
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/api/v1/bot/sales/statistics?user_id=123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_count" in data["data"]
        assert "total_amount" in data["data"]
        assert "buyouts_count" in data["data"]
        assert "returns_count" in data["data"]
        assert "buyout_rate" in data["data"]
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_sales_statistics_with_date_filters(self, mock_get_db, client, mock_db, sample_cabinet):
        """Тест получения статистики с фильтрами по датам"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_sales_statistics.return_value = {
                "total_count": 5,
                "total_amount": 7500.0,
                "buyouts_count": 4,
                "buyouts_amount": 6000.0,
                "returns_count": 1,
                "returns_amount": 1500.0,
                "buyout_rate": 80.0
            }
            mock_crud_class.return_value = mock_crud
            
            response = client.get(
                "/api/v1/bot/sales/statistics?user_id=123&date_from=2025-01-01&date_to=2025-01-31"
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_sales_statistics_invalid_date_format(self, mock_get_db, client, mock_db, sample_cabinet):
        """Тест получения статистики с неверным форматом даты"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        response = client.get("/api/v1/bot/sales/statistics?user_id=123&date_from=invalid-date")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid date_from format" in data["detail"]
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_buyouts_with_date_filter(self, mock_get_db, client, mock_db, sample_cabinet, sample_sales):
        """Тест получения выкупов с фильтром по дате"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        buyouts = [sale for sale in sample_sales if sale.type == "buyout"]
        
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_buyouts.return_value = buyouts
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/api/v1/bot/sales/buyouts?user_id=123&date_from=2025-01-01")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "buyouts" in data["data"]
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_returns_with_date_filter(self, mock_get_db, client, mock_db, sample_cabinet, sample_sales):
        """Тест получения возвратов с фильтром по дате"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        returns = [sale for sale in sample_sales if sale.type == "return"]
        
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_returns.return_value = returns
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/api/v1/bot/sales/returns?user_id=123&date_from=2025-01-01")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "returns" in data["data"]
    
    @patch('app.features.bot_api.routes_sales.get_db')
    def test_get_recent_sales_with_sale_type_filter(self, mock_get_db, client, mock_db, sample_cabinet, sample_sales):
        """Тест получения продаж с фильтром по типу"""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_cabinet
        
        buyouts = [sale for sale in sample_sales if sale.type == "buyout"]
        
        with patch('app.features.bot_api.routes_sales.WBSalesCRUD') as mock_crud_class:
            mock_crud = Mock()
            mock_crud.get_recent_sales.return_value = buyouts
            mock_crud.get_sales_statistics.return_value = {
                "total_count": 2,
                "total_amount": 2200.0,
                "buyouts_count": 2,
                "buyouts_amount": 2200.0,
                "returns_count": 0,
                "returns_amount": 0.0,
                "buyout_rate": 100.0
            }
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/api/v1/bot/sales/recent?user_id=123&sale_type=buyout")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sales" in data["data"]
