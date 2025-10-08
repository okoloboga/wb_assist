import pytest
from unittest.mock import Mock, patch
from wb_api.analytics import WBAnalytics

class TestWBAnalytics:
    """Тесты аналитики Wildberries"""
    
    def test_analytics_initialization(self):
        """Тест инициализации аналитики"""
        # 🔴 Тест упадет
        analytics = WBAnalytics()
        assert analytics.api is not None
    
    def test_get_daily_sales_empty_data(self):
        """Тест аналитики с пустыми данными"""
        with patch('wb_api.analytics.WildberriesAPI') as MockAPI:
            mock_api = MockAPI.return_value
            mock_api.get_sales.return_value = []
            
            analytics = WBAnalytics()
            result = analytics.get_daily_sales(days=7)
            
            assert result == {}
    
    def test_get_daily_sales_with_data(self):
        """Тест аналитики с реальными данными"""
        sample_sales = [
            {
                "date": "2023-10-01T12:00:00Z",
                "totalPrice": 1000.0,
                "quantity": 1
            },
            {
                "date": "2023-10-01T14:00:00Z", 
                "totalPrice": 2000.0,
                "quantity": 2
            },
            {
                "date": "2023-10-02T10:00:00Z",
                "totalPrice": 1500.0,
                "quantity": 1
            }
        ]
        
        with patch('wb_api.analytics.WildberriesAPI') as MockAPI:
            mock_api = MockAPI.return_value
            mock_api.get_sales.return_value = sample_sales
            
            analytics = WBAnalytics()
            result = analytics.get_daily_sales(days=7)
            
            assert "2023-10-01" in result
            assert "2023-10-02" in result
            assert result["2023-10-01"]["revenue"] == 3000.0
            assert result["2023-10-01"]["orders"] == 2
            assert result["2023-10-01"]["items"] == 3
    
    def test_get_top_products(self):
        """Тест получения топ товаров"""
        sample_sales = [
            {"nmId": 1, "subject": "Товар A", "totalPrice": 1000.0, "quantity": 1},
            {"nmId": 1, "subject": "Товар A", "totalPrice": 1000.0, "quantity": 1},
            {"nmId": 2, "subject": "Товар B", "totalPrice": 500.0, "quantity": 1},
        ]
        
        with patch('wb_api.analytics.WildberriesAPI') as MockAPI:
            mock_api = MockAPI.return_value
            mock_api.get_sales.return_value = sample_sales
            
            analytics = WBAnalytics()
            top_products = analytics.get_top_products(limit=2)
            
            assert len(top_products) == 2
            assert top_products[0]["nmId"] == 1
            assert top_products[0]["revenue"] == 2000.0
            assert top_products[0]["quantity"] == 2
            assert top_products[0]["orders"] == 2
    
    def test_get_stock_analysis(self):
        """Тест анализа остатков"""
        sample_stocks = [
            {"nmId": 1, "quantity": 10, "warehouseName": "Москва"},
            {"nmId": 2, "quantity": 0, "warehouseName": "Москва"},
            {"nmId": 3, "quantity": 5, "warehouseName": "СПб"},
            {"nmId": 4, "quantity": 20, "warehouseName": "СПб"},
        ]
        
        with patch('wb_api.analytics.WildberriesAPI') as MockAPI:
            mock_api = MockAPI.return_value
            mock_api.get_stocks.return_value = sample_stocks
            
            analytics = WBAnalytics()
            analysis = analytics.get_stock_analysis()
            
            assert analysis["total_sku"] == 4
            assert analysis["total_quantity"] == 35
            assert analysis["zero_stock"] == 1
            assert analysis["low_stock"] == 2  # 5 и 10
            assert "Москва" in analysis["warehouses"]
            assert "СПб" in analysis["warehouses"]