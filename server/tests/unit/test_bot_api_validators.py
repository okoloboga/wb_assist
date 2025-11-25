"""
Unit тесты для валидаторов Bot API
"""

import pytest
from pydantic import ValidationError
from app.features.bot_api.validators import (
    StocksQueryParams,
    AnalyticsQueryParams,
    OrdersQueryParams,
    ReviewsQueryParams,
    TelegramIdParam,
    PaginationParams
)


class TestStocksQueryParams:
    """Тесты для StocksQueryParams"""
    
    def test_valid_params(self):
        """Тест валидных параметров"""
        params = StocksQueryParams(
            telegram_id=123456,
            limit=20,
            offset=10,
            warehouse="Коледино",
            size="M",
            search="футболка"
        )
        assert params.telegram_id == 123456
        assert params.limit == 20
        assert params.offset == 10
        assert params.warehouse == "Коледино"
        assert params.size == "M"
        assert params.search == "футболка"
    
    def test_default_values(self):
        """Тест значений по умолчанию"""
        params = StocksQueryParams(telegram_id=123456)
        assert params.limit == 15
        assert params.offset == 0
        assert params.warehouse is None
        assert params.size is None
        assert params.search is None
    
    def test_invalid_telegram_id(self):
        """Тест невалидного telegram_id"""
        with pytest.raises(ValidationError) as exc_info:
            StocksQueryParams(telegram_id=-1)
        assert "ensure this value is greater than 0" in str(exc_info.value)
    
    def test_limit_out_of_range(self):
        """Тест limit вне диапазона"""
        with pytest.raises(ValidationError):
            StocksQueryParams(telegram_id=123, limit=0)
        
        with pytest.raises(ValidationError):
            StocksQueryParams(telegram_id=123, limit=101)
    
    def test_negative_offset(self):
        """Тест отрицательного offset"""
        with pytest.raises(ValidationError):
            StocksQueryParams(telegram_id=123, offset=-1)
    
    def test_warehouse_with_dangerous_chars(self):
        """Тест склада с опасными символами"""
        with pytest.raises(ValidationError) as exc_info:
            StocksQueryParams(telegram_id=123, warehouse="Коледино<script>")
        assert "Недопустимые символы" in str(exc_info.value)
    
    def test_size_with_dangerous_chars(self):
        """Тест размера с опасными символами"""
        with pytest.raises(ValidationError) as exc_info:
            StocksQueryParams(telegram_id=123, size="M{test}")
        assert "Недопустимые символы" in str(exc_info.value)
    
    def test_search_sql_injection(self):
        """Тест защиты от SQL injection"""
        with pytest.raises(ValidationError) as exc_info:
            StocksQueryParams(telegram_id=123, search="'; DROP TABLE users--")
        assert "Недопустимые символы" in str(exc_info.value)
    
    def test_search_empty_string(self):
        """Тест пустой строки поиска"""
        with pytest.raises(ValidationError) as exc_info:
            StocksQueryParams(telegram_id=123, search="   ")
        assert "не может быть пустым" in str(exc_info.value)
    
    def test_search_too_long(self):
        """Тест слишком длинной строки поиска"""
        with pytest.raises(ValidationError):
            StocksQueryParams(telegram_id=123, search="a" * 201)


class TestAnalyticsQueryParams:
    """Тесты для AnalyticsQueryParams"""
    
    def test_valid_periods(self):
        """Тест валидных периодов"""
        for period in ["7d", "30d", "60d", "90d", "180d"]:
            params = AnalyticsQueryParams(telegram_id=123, period=period)
            assert params.period == period
    
    def test_default_period(self):
        """Тест периода по умолчанию"""
        params = AnalyticsQueryParams(telegram_id=123)
        assert params.period == "30d"
    
    def test_invalid_period_format(self):
        """Тест невалидного формата периода"""
        with pytest.raises(ValidationError):
            AnalyticsQueryParams(telegram_id=123, period="999d")
    
    def test_invalid_period_string(self):
        """Тест невалидной строки периода"""
        with pytest.raises(ValidationError):
            AnalyticsQueryParams(telegram_id=123, period="invalid")


class TestOrdersQueryParams:
    """Тесты для OrdersQueryParams"""
    
    def test_valid_params(self):
        """Тест валидных параметров"""
        params = OrdersQueryParams(
            telegram_id=123,
            limit=50,
            offset=20,
            status="active"
        )
        assert params.telegram_id == 123
        assert params.limit == 50
        assert params.offset == 20
        assert params.status == "active"
    
    def test_default_values(self):
        """Тест значений по умолчанию"""
        params = OrdersQueryParams(telegram_id=123)
        assert params.limit == 10
        assert params.offset == 0
        assert params.status is None
    
    def test_valid_statuses(self):
        """Тест валидных статусов"""
        for status in ["active", "canceled"]:
            params = OrdersQueryParams(telegram_id=123, status=status)
            assert params.status == status
    
    def test_invalid_status(self):
        """Тест невалидного статуса"""
        with pytest.raises(ValidationError):
            OrdersQueryParams(telegram_id=123, status="invalid")


class TestReviewsQueryParams:
    """Тесты для ReviewsQueryParams"""
    
    def test_valid_params(self):
        """Тест валидных параметров"""
        params = ReviewsQueryParams(
            telegram_id=123,
            limit=20,
            offset=10,
            rating_threshold=3
        )
        assert params.telegram_id == 123
        assert params.limit == 20
        assert params.offset == 10
        assert params.rating_threshold == 3
    
    def test_rating_range(self):
        """Тест диапазона рейтинга"""
        for rating in [1, 2, 3, 4, 5]:
            params = ReviewsQueryParams(telegram_id=123, rating_threshold=rating)
            assert params.rating_threshold == rating
    
    def test_rating_out_of_range(self):
        """Тест рейтинга вне диапазона"""
        with pytest.raises(ValidationError):
            ReviewsQueryParams(telegram_id=123, rating_threshold=0)
        
        with pytest.raises(ValidationError):
            ReviewsQueryParams(telegram_id=123, rating_threshold=6)


class TestTelegramIdParam:
    """Тесты для TelegramIdParam"""
    
    def test_valid_telegram_id(self):
        """Тест валидного telegram_id"""
        params = TelegramIdParam(telegram_id=123456789)
        assert params.telegram_id == 123456789
    
    def test_zero_telegram_id(self):
        """Тест нулевого telegram_id"""
        with pytest.raises(ValidationError):
            TelegramIdParam(telegram_id=0)
    
    def test_negative_telegram_id(self):
        """Тест отрицательного telegram_id"""
        with pytest.raises(ValidationError):
            TelegramIdParam(telegram_id=-123)
    
    def test_too_large_telegram_id(self):
        """Тест слишком большого telegram_id"""
        with pytest.raises(ValidationError):
            TelegramIdParam(telegram_id=99999999999)


class TestPaginationParams:
    """Тесты для PaginationParams"""
    
    def test_valid_params(self):
        """Тест валидных параметров"""
        params = PaginationParams(limit=50, offset=100)
        assert params.limit == 50
        assert params.offset == 100
    
    def test_default_values(self):
        """Тест значений по умолчанию"""
        params = PaginationParams()
        assert params.limit == 15
        assert params.offset == 0
    
    def test_limit_boundaries(self):
        """Тест границ limit"""
        params = PaginationParams(limit=1)
        assert params.limit == 1
        
        params = PaginationParams(limit=100)
        assert params.limit == 100
        
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)
        
        with pytest.raises(ValidationError):
            PaginationParams(limit=101)
    
    def test_offset_max(self):
        """Тест максимального offset"""
        params = PaginationParams(offset=10000)
        assert params.offset == 10000
        
        with pytest.raises(ValidationError):
            PaginationParams(offset=10001)


class TestSecurityValidation:
    """Тесты безопасности валидации"""
    
    def test_sql_injection_patterns(self):
        """Тест различных паттернов SQL injection"""
        sql_patterns = [
            "'; DROP TABLE users--",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
            "'; DELETE FROM products WHERE '1'='1",
            "1; exec xp_cmdshell('dir')",
        ]
        
        for pattern in sql_patterns:
            with pytest.raises(ValidationError):
                StocksQueryParams(telegram_id=123, search=pattern)
    
    def test_xss_patterns(self):
        """Тест различных паттернов XSS"""
        xss_patterns = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='evil.com'>",
        ]
        
        for pattern in xss_patterns:
            with pytest.raises(ValidationError):
                StocksQueryParams(telegram_id=123, warehouse=pattern)
    
    def test_path_traversal(self):
        """Тест защиты от path traversal"""
        patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
        ]
        
        for pattern in patterns:
            with pytest.raises(ValidationError):
                StocksQueryParams(telegram_id=123, warehouse=pattern)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
