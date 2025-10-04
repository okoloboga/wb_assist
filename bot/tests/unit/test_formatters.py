import pytest
from utils.formatters import (
    format_error_message,
    format_currency,
    format_percentage,
    format_datetime,
    format_relative_time,
    format_stocks_summary,
    format_order_summary,
    format_product_summary,
    truncate_text,
    format_rating
)


class TestFormatters:
    """Тесты для функций форматирования"""
    
    def test_format_error_message_503(self):
        """Тест форматирования ошибки 503"""
        result = format_error_message("Service unavailable", 503)
        assert "Сервер временно недоступен" in result
    
    def test_format_error_message_404(self):
        """Тест форматирования ошибки 404"""
        result = format_error_message("Not found", 404)
        assert "Ресурс не найден" in result
    
    def test_format_error_message_400(self):
        """Тест форматирования ошибки 400"""
        result = format_error_message("Bad request", 400)
        assert "Некорректный запрос" in result
        assert "Bad request" in result
    
    def test_format_error_message_500(self):
        """Тест форматирования ошибки 500"""
        result = format_error_message("Internal error", 500)
        assert "Внутренняя ошибка сервера" in result
    
    def test_format_error_message_unknown(self):
        """Тест форматирования неизвестной ошибки"""
        result = format_error_message("Unknown error", 999)
        assert "Внутренняя ошибка сервера" in result
    
    def test_format_error_message_none(self):
        """Тест форматирования None ошибки"""
        result = format_error_message(None, 500)
        assert "Внутренняя ошибка сервера" in result
    
    def test_format_currency(self):
        """Тест форматирования валюты"""
        assert format_currency(1000) == "1 000₽"
        assert format_currency(1234567) == "1 234 567₽"
        assert format_currency(0) == "0₽"
        assert format_currency(999.99) == "1 000₽"
    
    def test_format_percentage(self):
        """Тест форматирования процентов"""
        assert format_percentage(10.5) == "+10.5%"
        assert format_percentage(-5.2) == "-5.2%"
        assert format_percentage(0) == "+0.0%"
    
    def test_format_datetime(self):
        """Тест форматирования даты и времени"""
        # ISO формат
        result = format_datetime("2025-01-28T14:30:15")
        assert "28.01.2025 14:30" in result
        
        # С Z в конце
        result = format_datetime("2025-01-28T14:30:15Z")
        assert "28.01.2025 14:30" in result
        
        # Неверный формат
        result = format_datetime("invalid_date")
        assert result == "invalid_date"
    
    def test_format_relative_time(self):
        """Тест форматирования относительного времени"""
        from datetime import datetime, timedelta
        
        # Недавно (меньше минуты) - используем текущее время
        now = datetime.now()
        recent_time = now.strftime("%Y-%m-%dT%H:%M:%S")
        result = format_relative_time(recent_time)
        assert "только что" in result or "мин. назад" in result
        
        # Неверный формат
        result = format_relative_time("invalid_date")
        assert result == "invalid_date"
    
    def test_format_stocks_summary(self):
        """Тест форматирования сводки остатков"""
        stocks = {"S": 10, "M": 2, "L": 0, "XL": 1}
        result = format_stocks_summary(stocks)
        
        assert "S(10)" in result
        assert "M(2)⚠️" in result  # Меньше 5
        assert "L(0)" in result
        assert "XL(1)⚠️" in result  # Меньше 5
    
    def test_format_stocks_summary_empty(self):
        """Тест форматирования пустых остатков"""
        result = format_stocks_summary({})
        assert result == "Нет данных"
    
    def test_format_order_summary(self):
        """Тест форматирования сводки заказа"""
        order = {
            "id": 123,
            "date": "2025-01-28T14:30:15",
            "amount": 1500
        }
        result = format_order_summary(order)
        
        assert "#123" in result
        assert "1 500₽" in result
    
    def test_format_product_summary(self):
        """Тест форматирования сводки товара"""
        product = {
            "name": "Test Product",
            "brand": "Test Brand",
            "price": 2000
        }
        result = format_product_summary(product)
        
        assert "Test Product" in result
        assert "Test Brand" in result
        assert "2 000₽" in result
    
    def test_truncate_text(self):
        """Тест обрезания текста"""
        text = "This is a very long text that should be truncated"
        result = truncate_text(text, 20)
        
        assert len(result) <= 20
        assert result.endswith("...")
        assert "This is a very lo..." == result
    
    def test_truncate_text_short(self):
        """Тест обрезания короткого текста"""
        text = "Short text"
        result = truncate_text(text, 20)
        
        assert result == text
    
    def test_format_rating(self):
        """Тест форматирования рейтинга"""
        # 5 звезд
        result = format_rating(5.0)
        assert "⭐⭐⭐⭐⭐" in result
        assert "5.0/5" in result
        
        # 4.5 звезды
        result = format_rating(4.5)
        assert "⭐⭐⭐⭐✨" in result
        assert "4.5/5" in result
        
        # 3.2 звезды
        result = format_rating(3.2)
        assert "⭐⭐⭐☆☆" in result
        assert "3.2/5" in result
        
        # 0 звезд
        result = format_rating(0.0)
        assert "☆☆☆☆☆" in result
        assert "0.0/5" in result