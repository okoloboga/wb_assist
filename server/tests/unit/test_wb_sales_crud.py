"""
Unit тесты для WBSalesCRUD
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from unittest.mock import Mock

from app.features.wb_api.crud_sales import WBSalesCRUD
from app.features.wb_api.models_sales import WBSales


class TestWBSalesCRUD:
    """Тесты для WBSalesCRUD"""
    
    @pytest.fixture
    def sales_crud(self):
        """Экземпляр WBSalesCRUD"""
        return WBSalesCRUD()
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_sale_data(self):
        """Пример данных продажи"""
        return {
            "cabinet_id": 1,
            "sale_id": "sale_123",
            "order_id": "order_456",
            "nm_id": 12345,
            "product_name": "Test Product",
            "brand": "Test Brand",
            "size": "M",
            "amount": 1000.0,
            "sale_date": datetime.now(timezone.utc),
            "type": "buyout",
            "status": "completed",
            "is_cancel": False,
            "last_change_date": datetime.now(timezone.utc)
        }
    
    def test_create_sale(self, sales_crud, mock_db, sample_sale_data):
        """Тест создания записи о продаже"""
        mock_sale = Mock(spec=WBSales)
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Мокаем создание объекта
        with pytest.MonkeyPatch().context() as m:
            m.setattr(WBSales, "__init__", lambda self, **kwargs: None)
            result = sales_crud.create_sale(mock_db, sample_sale_data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_get_sales_by_cabinet(self, sales_crud, mock_db):
        """Тест получения продаж по кабинету"""
        mock_sales = [Mock(spec=WBSales), Mock(spec=WBSales)]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_sales
        mock_db.query.return_value = mock_query
        
        result = sales_crud.get_sales_by_cabinet(mock_db, 1, limit=10, offset=0)
        
        assert result == mock_sales
        mock_db.query.assert_called_once_with(WBSales)
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.offset.assert_called_once_with(0)
        mock_query.limit.assert_called_once_with(10)
    
    def test_get_sales_by_cabinet_with_filters(self, sales_crud, mock_db):
        """Тест получения продаж по кабинету с фильтрами"""
        mock_sales = [Mock(spec=WBSales)]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_sales
        mock_db.query.return_value = mock_query
        
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
        date_to = datetime.now(timezone.utc)
        
        result = sales_crud.get_sales_by_cabinet(
            mock_db, 1, limit=5, offset=0, 
            sale_type="buyout", date_from=date_from, date_to=date_to
        )
        
        assert result == mock_sales
        # Проверяем, что фильтры применены
        assert mock_query.filter.call_count >= 1
    
    def test_get_recent_sales(self, sales_crud, mock_db):
        """Тест получения последних продаж"""
        mock_sales = [Mock(spec=WBSales), Mock(spec=WBSales)]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_sales
        mock_db.query.return_value = mock_query
        
        result = sales_crud.get_recent_sales(mock_db, 1, limit=10)
        
        assert result == mock_sales
        mock_db.query.assert_called_once_with(WBSales)
        mock_query.filter.assert_called()
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(10)
    
    def test_get_buyouts(self, sales_crud, mock_db):
        """Тест получения только выкупов"""
        mock_buyouts = [Mock(spec=WBSales)]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_buyouts
        mock_db.query.return_value = mock_query
        
        result = sales_crud.get_buyouts(mock_db, 1, limit=10)
        
        assert result == mock_buyouts
        mock_db.query.assert_called_once_with(WBSales)
        mock_query.filter.assert_called()
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(10)
    
    def test_get_returns(self, sales_crud, mock_db):
        """Тест получения только возвратов"""
        mock_returns = [Mock(spec=WBSales)]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_returns
        mock_db.query.return_value = mock_query
        
        result = sales_crud.get_returns(mock_db, 1, limit=10)
        
        assert result == mock_returns
        mock_db.query.assert_called_once_with(WBSales)
        mock_query.filter.assert_called()
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(10)
    
    def test_get_sales_statistics(self, sales_crud, mock_db):
        """Тест получения статистики продаж"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        mock_db.query.return_value = mock_query
        
        # Мокаем func.sum
        mock_sum = Mock()
        mock_sum.return_value = 5000.0
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5000.0
        
        result = sales_crud.get_sales_statistics(mock_db, 1)
        
        assert "total_count" in result
        assert "total_amount" in result
        assert "buyouts_count" in result
        assert "buyouts_amount" in result
        assert "returns_count" in result
        assert "returns_amount" in result
        assert "buyout_rate" in result
    
    def test_get_sale_by_sale_id(self, sales_crud, mock_db):
        """Тест получения продажи по ID"""
        mock_sale = Mock(spec=WBSales)
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_sale
        mock_db.query.return_value = mock_query
        
        result = sales_crud.get_sale_by_sale_id(mock_db, 1, "sale_123")
        
        assert result == mock_sale
        mock_db.query.assert_called_once_with(WBSales)
        mock_query.filter.assert_called()
        mock_query.first.assert_called_once()
    
    def test_get_sale_by_sale_id_not_found(self, sales_crud, mock_db):
        """Тест получения несуществующей продажи"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = sales_crud.get_sale_by_sale_id(mock_db, 1, "nonexistent")
        
        assert result is None
    
    def test_update_sale(self, sales_crud, mock_db):
        """Тест обновления продажи"""
        mock_sale = Mock(spec=WBSales)
        mock_sale.id = 1
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_sale
        mock_db.query.return_value = mock_query
        
        update_data = {"amount": 1500.0, "status": "updated"}
        
        result = sales_crud.update_sale(mock_db, 1, update_data)
        
        assert result == mock_sale
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_sale)
    
    def test_update_sale_not_found(self, sales_crud, mock_db):
        """Тест обновления несуществующей продажи"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        update_data = {"amount": 1500.0}
        
        result = sales_crud.update_sale(mock_db, 999, update_data)
        
        assert result is None
        mock_db.commit.assert_not_called()
    
    def test_delete_sale(self, sales_crud, mock_db):
        """Тест удаления продажи"""
        mock_sale = Mock(spec=WBSales)
        mock_sale.id = 1
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_sale
        mock_db.query.return_value = mock_query
        
        result = sales_crud.delete_sale(mock_db, 1)
        
        assert result is True
        mock_db.delete.assert_called_once_with(mock_sale)
        mock_db.commit.assert_called_once()
    
    def test_delete_sale_not_found(self, sales_crud, mock_db):
        """Тест удаления несуществующей продажи"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = sales_crud.delete_sale(mock_db, 999)
        
        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
