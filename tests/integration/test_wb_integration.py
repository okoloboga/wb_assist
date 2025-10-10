import pytest
from wb_api.client import WildberriesAPI
from wb_api.analytics import WBAnalytics

@pytest.mark.integration
class TestWBIntegration:
    """Интеграционные тесты с реальным API"""
    
    @pytest.fixture
    def wb_client(self):
        return WildberriesAPI()
    
    @pytest.fixture
    def analytics(self):
        return WBAnalytics()
    
    def test_real_api_connection(self, wb_client):
        """Тест реального подключения к API"""
        # Этот тест требует настоящий API ключ
        orders = wb_client.get_orders()
        # Проверяем что получаем данные (или пустой список если нет заказов)
        assert isinstance(orders, list)
    
    def test_get_prices_real_api(self, wb_client):
        """Тест получения цен с реального API"""
        # Этот тест требует настоящий API ключ
        prices = wb_client.get_prices()
        
        # Проверяем что получаем данные (или пустой список)
        assert isinstance(prices, list)
        
        # Если есть данные, проверяем структуру
        if prices:
            price_item = prices[0]
            # Проверяем наличие ключевых полей (могут отличаться в реальном API)
            assert isinstance(price_item, dict)
            # Обычно в ответе есть поля связанные с ценами
            # Точная структура зависит от реального API Wildberries
    
    def test_analytics_with_real_data(self, analytics):
        """Тест аналитики с реальными данными"""
        daily_stats = analytics.get_daily_sales(days=1)
        assert isinstance(daily_stats, dict)
        
        stock_analysis = analytics.get_stock_analysis()
        assert isinstance(stock_analysis, dict)
        assert 'total_sku' in stock_analysis