import pytest
from unittest.mock import AsyncMock, patch
from aiogram.fsm.context import FSMContext

from handlers.dashboard import show_dashboard
from handlers.orders import show_recent_orders
from handlers.stocks import show_critical_stocks
from handlers.reviews import show_new_reviews
from handlers.analytics import show_analytics_period
from handlers.sync import start_manual_sync


class TestDashboardHandlers:
    """Тесты для обработчиков дашборда"""
    
    @pytest.mark.asyncio
    async def test_show_dashboard_success(self, mock_callback_query, mock_api_response):
        """Тест успешного показа дашборда"""
        response = mock_api_response(
            success=True,
            data={"cabinet_name": "Test Cabinet"},
            telegram_text="Test dashboard text"
        )
        
        with patch('handlers.dashboard.bot_api_client.get_dashboard', return_value=response):
            await show_dashboard(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_show_dashboard_error(self, mock_callback_query, mock_api_response):
        """Тест ошибки показа дашборда"""
        response = mock_api_response(
            success=False,
            error="Server error",
            status_code=500
        )
        
        with patch('handlers.dashboard.bot_api_client.get_dashboard', return_value=response):
            await show_dashboard(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            # Проверяем, что в тексте есть сообщение об ошибке
            call_args = mock_callback_query.message.edit_text.call_args
            assert "Ошибка загрузки дашборда" in call_args[0][0]


class TestOrdersHandlers:
    """Тесты для обработчиков заказов"""
    
    @pytest.mark.asyncio
    async def test_show_recent_orders_success(self, mock_callback_query, mock_api_response):
        """Тест успешного показа заказов"""
        response = mock_api_response(
            success=True,
            data={
                "orders": [
                    {"id": 1, "amount": 1000, "product_name": "Test Product"}
                ],
                "pagination": {"has_more": False}
            },
            telegram_text="Test orders text"
        )
        
        with patch('handlers.orders.bot_api_client.get_recent_orders', return_value=response):
            await show_recent_orders(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_show_recent_orders_empty(self, mock_callback_query, mock_api_response):
        """Тест показа пустого списка заказов"""
        response = mock_api_response(
            success=True,
            data={"orders": [], "pagination": {"has_more": False}},
            telegram_text="No orders"
        )
        
        with patch('handlers.orders.bot_api_client.get_recent_orders', return_value=response):
            await show_recent_orders(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            # Проверяем, что показано сообщение об отсутствии заказов
            call_args = mock_callback_query.message.edit_text.call_args
            assert "Заказов пока нет" in call_args[0][0]


class TestStocksHandlers:
    """Тесты для обработчиков остатков"""
    
    @pytest.mark.asyncio
    async def test_show_critical_stocks_success(self, mock_callback_query, mock_api_response):
        """Тест успешного показа критичных остатков"""
        response = mock_api_response(
            success=True,
            data={
                "critical_products": [
                    {"nm_id": 123, "name": "Test Product", "stocks": {"S": 1, "M": 0}}
                ],
                "zero_products": [],
                "summary": {"critical_count": 1}
            },
            telegram_text="Test stocks text"
        )
        
        with patch('handlers.stocks.bot_api_client.get_critical_stocks', return_value=response):
            await show_critical_stocks(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_show_critical_stocks_empty(self, mock_callback_query, mock_api_response):
        """Тест показа пустого списка остатков"""
        response = mock_api_response(
            success=True,
            data={
                "critical_products": [],
                "zero_products": [],
                "summary": {"critical_count": 0}
            },
            telegram_text="No critical stocks"
        )
        
        with patch('handlers.stocks.bot_api_client.get_critical_stocks', return_value=response):
            await show_critical_stocks(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            # Проверяем, что показано сообщение об отсутствии критичных остатков
            call_args = mock_callback_query.message.edit_text.call_args
            assert "Все остатки в норме" in call_args[0][0]


class TestReviewsHandlers:
    """Тесты для обработчиков отзывов"""
    
    @pytest.mark.asyncio
    async def test_show_new_reviews_success(self, mock_callback_query, mock_api_response):
        """Тест успешного показа отзывов"""
        response = mock_api_response(
            success=True,
            data={
                "new_reviews": [
                    {"id": "1", "product_name": "Test Product", "rating": 5, "text": "Great!"}
                ],
                "unanswered_questions": [],
                "statistics": {"total_reviews": 10}
            },
            telegram_text="Test reviews text"
        )
        
        with patch('handlers.reviews.bot_api_client.get_reviews_summary', return_value=response):
            await show_new_reviews(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_show_new_reviews_empty(self, mock_callback_query, mock_api_response):
        """Тест показа пустого списка отзывов"""
        response = mock_api_response(
            success=True,
            data={
                "new_reviews": [],
                "unanswered_questions": [],
                "statistics": {"total_reviews": 0}
            },
            telegram_text="No new reviews"
        )
        
        with patch('handlers.reviews.bot_api_client.get_reviews_summary', return_value=response):
            await show_new_reviews(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            # Проверяем, что показано сообщение об отсутствии отзывов
            call_args = mock_callback_query.message.edit_text.call_args
            assert "Новых отзывов и вопросов нет" in call_args[0][0]


class TestAnalyticsHandlers:
    """Тесты для обработчиков аналитики"""
    
    @pytest.mark.asyncio
    async def test_show_analytics_period_success(self, mock_callback_query, mock_api_response):
        """Тест успешного показа аналитики"""
        response = mock_api_response(
            success=True,
            data={
                "sales_periods": {"7_days": {"count": 100, "amount": 50000}},
                "dynamics": {"week_growth_percent": 10},
                "top_products": []
            },
            telegram_text="Test analytics text"
        )
        
        with patch('handlers.analytics.bot_api_client.get_analytics_sales', return_value=response):
            await show_analytics_period(mock_callback_query)
            
            mock_callback_query.message.edit_text.assert_called_once()
            mock_callback_query.answer.assert_called_once()


class TestSyncHandlers:
    """Тесты для обработчиков синхронизации"""
    
    @pytest.mark.asyncio
    async def test_start_manual_sync(self, mock_callback_query, mock_api_response):
        """Тест запуска ручной синхронизации"""
        # Создаем мок FSMContext
        mock_state = AsyncMock(spec=FSMContext)
        mock_callback_query.data = "start_sync"
        
        response = mock_api_response(
            success=True,
            data={"sync_id": "test_sync_123"},
            telegram_text="Sync started"
        )
        
        with patch('handlers.sync.bot_api_client.start_sync', return_value=response):
            await start_manual_sync(mock_callback_query, mock_state)
            
            mock_state.set_state.assert_called_once()
            mock_callback_query.message.edit_text.assert_called_once()
            mock_callback_query.answer.assert_called_once()