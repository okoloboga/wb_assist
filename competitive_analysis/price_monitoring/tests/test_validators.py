"""
Тесты для модуля validators.py
"""

import unittest
from datetime import datetime, date
from typing import Dict, Any

# Импортируем тестируемые модули
from utils.validators import (
    ValidationError, ValidationResult, StringValidator, NumberValidator,
    PriceValidator, URLValidator, EmailValidator, DateTimeValidator,
    ListValidator, ProductValidator, DataCleaner,
    validate_string, validate_number, validate_price, validate_url, clean_data
)


class TestValidationResult(unittest.TestCase):
    """Тесты для класса ValidationResult."""
    
    def test_valid_result(self):
        """Тест валидного результата."""
        result = ValidationResult(is_valid=True)
        self.assertTrue(result.is_valid)
        self.assertTrue(bool(result))
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(str(result), "Валидация пройдена")
    
    def test_invalid_result(self):
        """Тест невалидного результата."""
        result = ValidationResult(is_valid=False, errors=["Ошибка 1", "Ошибка 2"])
        self.assertFalse(result.is_valid)
        self.assertFalse(bool(result))
        self.assertEqual(len(result.errors), 2)
        self.assertIn("Ошибка 1", str(result))
        self.assertIn("Ошибка 2", str(result))
    
    def test_add_error(self):
        """Тест добавления ошибки."""
        result = ValidationResult()
        self.assertTrue(result.is_valid)
        
        result.add_error("Новая ошибка")
        self.assertFalse(result.is_valid)
        self.assertIn("Новая ошибка", result.errors)


class TestStringValidator(unittest.TestCase):
    """Тесты для StringValidator."""
    
    def test_valid_string(self):
        """Тест валидной строки."""
        result = StringValidator.validate("Тестовая строка")
        self.assertTrue(result.is_valid)
    
    def test_empty_string_required(self):
        """Тест пустой строки когда поле обязательно."""
        result = StringValidator.validate("", required=True)
        self.assertFalse(result.is_valid)
        self.assertIn("Поле не может быть пустым", result.errors[0])
    
    def test_empty_string_not_required(self):
        """Тест пустой строки когда поле не обязательно."""
        result = StringValidator.validate("", required=False, min_length=0)
        self.assertTrue(result.is_valid)
    
    def test_none_required(self):
        """Тест None когда поле обязательно."""
        result = StringValidator.validate(None, required=True)
        self.assertFalse(result.is_valid)
        self.assertIn("обязательно", result.errors[0])
    
    def test_none_not_required(self):
        """Тест None когда поле не обязательно."""
        result = StringValidator.validate(None, required=False)
        self.assertTrue(result.is_valid)
    
    def test_min_length(self):
        """Тест минимальной длины."""
        result = StringValidator.validate("abc", min_length=5)
        self.assertFalse(result.is_valid)
        self.assertIn("Минимальная длина", result.errors[0])
    
    def test_max_length(self):
        """Тест максимальной длины."""
        result = StringValidator.validate("a" * 100, max_length=50)
        self.assertFalse(result.is_valid)
        self.assertIn("Максимальная длина", result.errors[0])
    
    def test_pattern_match(self):
        """Тест соответствия паттерну."""
        # Валидный email паттерн
        result = StringValidator.validate("test@example.com", pattern=r'^[^@]+@[^@]+\.[^@]+$')
        self.assertTrue(result.is_valid)
        
        # Невалидный email
        result = StringValidator.validate("invalid-email", pattern=r'^[^@]+@[^@]+\.[^@]+$')
        self.assertFalse(result.is_valid)
        self.assertIn("паттерну", result.errors[0])
    
    def test_allowed_values(self):
        """Тест допустимых значений."""
        allowed = ["red", "green", "blue"]
        
        # Валидное значение
        result = StringValidator.validate("red", allowed_values=allowed)
        self.assertTrue(result.is_valid)
        
        # Невалидное значение
        result = StringValidator.validate("yellow", allowed_values=allowed)
        self.assertFalse(result.is_valid)
        self.assertIn("Допустимые значения", result.errors[0])
    
    def test_non_string_conversion(self):
        """Тест конвертации не-строки в строку."""
        result = StringValidator.validate(123, min_length=1, max_length=10)
        self.assertTrue(result.is_valid)


class TestNumberValidator(unittest.TestCase):
    """Тесты для NumberValidator."""
    
    def test_valid_number(self):
        """Тест валидного числа."""
        result = NumberValidator.validate(42)
        self.assertTrue(result.is_valid)
        
        result = NumberValidator.validate(3.14)
        self.assertTrue(result.is_valid)
    
    def test_string_number(self):
        """Тест числа в виде строки."""
        result = NumberValidator.validate("42")
        self.assertTrue(result.is_valid)
        
        result = NumberValidator.validate("3,14")  # Запятая как разделитель
        self.assertTrue(result.is_valid)
        
        result = NumberValidator.validate("1 234.56")  # С пробелами
        self.assertTrue(result.is_valid)
    
    def test_invalid_number(self):
        """Тест невалидного числа."""
        result = NumberValidator.validate("не число")
        self.assertFalse(result.is_valid)
        self.assertIn("преобразовать в число", result.errors[0])
    
    def test_none_required(self):
        """Тест None когда поле обязательно."""
        result = NumberValidator.validate(None, required=True)
        self.assertFalse(result.is_valid)
        self.assertIn("обязательно", result.errors[0])
    
    def test_none_not_required(self):
        """Тест None когда поле не обязательно."""
        result = NumberValidator.validate(None, required=False)
        self.assertTrue(result.is_valid)
    
    def test_zero_allowed(self):
        """Тест нуля когда он разрешен."""
        result = NumberValidator.validate(0, allow_zero=True)
        self.assertTrue(result.is_valid)
    
    def test_zero_not_allowed(self):
        """Тест нуля когда он не разрешен."""
        result = NumberValidator.validate(0, allow_zero=False)
        self.assertFalse(result.is_valid)
        self.assertIn("не может быть равно нулю", result.errors[0])
    
    def test_min_value(self):
        """Тест минимального значения."""
        result = NumberValidator.validate(5, min_value=10)
        self.assertFalse(result.is_valid)
        self.assertIn("Минимальное значение", result.errors[0])
    
    def test_max_value(self):
        """Тест максимального значения."""
        result = NumberValidator.validate(15, max_value=10)
        self.assertFalse(result.is_valid)
        self.assertIn("Максимальное значение", result.errors[0])
    
    def test_decimal_places(self):
        """Тест количества знаков после запятой."""
        result = NumberValidator.validate(3.14159, decimal_places=2)
        self.assertFalse(result.is_valid)
        self.assertIn("знаков после запятой", result.errors[0])


class TestPriceValidator(unittest.TestCase):
    """Тесты для PriceValidator."""
    
    def test_valid_price(self):
        """Тест валидной цены."""
        result = PriceValidator.validate(99.99)
        self.assertTrue(result.is_valid)
    
    def test_zero_price(self):
        """Тест нулевой цены."""
        result = PriceValidator.validate(0)
        self.assertFalse(result.is_valid)
        self.assertIn("не может быть равно нулю", result.errors[0])
    
    def test_negative_price(self):
        """Тест отрицательной цены."""
        result = PriceValidator.validate(-10)
        self.assertFalse(result.is_valid)
        self.assertIn("Минимальное значение", result.errors[0])
    
    def test_too_high_price(self):
        """Тест слишком высокой цены."""
        result = PriceValidator.validate(2000000)
        self.assertFalse(result.is_valid)
        self.assertIn("Максимальное значение", result.errors[0])


class TestURLValidator(unittest.TestCase):
    """Тесты для URLValidator."""
    
    def test_valid_url(self):
        """Тест валидного URL."""
        result = URLValidator.validate("https://example.com")
        self.assertTrue(result.is_valid)
        
        result = URLValidator.validate("http://test.ru/path?param=value")
        self.assertTrue(result.is_valid)
    
    def test_invalid_url(self):
        """Тест невалидного URL."""
        result = URLValidator.validate("не url")
        self.assertFalse(result.is_valid)
    
    def test_url_without_scheme(self):
        """Тест URL без схемы."""
        result = URLValidator.validate("example.com")
        self.assertFalse(result.is_valid)
        self.assertIn("схему", result.errors[0])
    
    def test_url_without_domain(self):
        """Тест URL без домена."""
        result = URLValidator.validate("https://")
        self.assertFalse(result.is_valid)
        self.assertIn("домен", result.errors[0])
    
    def test_allowed_schemes(self):
        """Тест разрешенных схем."""
        result = URLValidator.validate("ftp://example.com", allowed_schemes=["http", "https"])
        self.assertFalse(result.is_valid)
        self.assertIn("Разрешенные схемы", result.errors[0])
    
    def test_none_not_required(self):
        """Тест None когда поле не обязательно."""
        result = URLValidator.validate(None, required=False)
        self.assertTrue(result.is_valid)


class TestEmailValidator(unittest.TestCase):
    """Тесты для EmailValidator."""
    
    def test_valid_email(self):
        """Тест валидного email."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for email in valid_emails:
            result = EmailValidator.validate(email)
            self.assertTrue(result.is_valid, f"Email {email} должен быть валидным")
    
    def test_invalid_email(self):
        """Тест невалидного email."""
        invalid_emails = [
            "не email",
            "@example.com",
            "user@",
            "user.example.com",
            "user@domain"
        ]
        
        for email in invalid_emails:
            result = EmailValidator.validate(email)
            self.assertFalse(result.is_valid, f"Email {email} должен быть невалидным")
    
    def test_none_not_required(self):
        """Тест None когда поле не обязательно."""
        result = EmailValidator.validate(None, required=False)
        self.assertTrue(result.is_valid)


class TestDateTimeValidator(unittest.TestCase):
    """Тесты для DateTimeValidator."""
    
    def test_datetime_object(self):
        """Тест datetime объекта."""
        dt = datetime(2024, 1, 15, 14, 30)
        result = DateTimeValidator.validate(dt)
        self.assertTrue(result.is_valid)
    
    def test_date_object(self):
        """Тест date объекта."""
        d = date(2024, 1, 15)
        result = DateTimeValidator.validate(d)
        self.assertTrue(result.is_valid)
    
    def test_string_date(self):
        """Тест даты в виде строки."""
        valid_dates = [
            "2024-01-15 14:30:00",
            "2024-01-15",
            "15.01.2024",
            "15/01/2024"
        ]
        
        for date_str in valid_dates:
            result = DateTimeValidator.validate(date_str)
            self.assertTrue(result.is_valid, f"Дата {date_str} должна быть валидной")
    
    def test_invalid_date_string(self):
        """Тест невалидной даты в виде строки."""
        result = DateTimeValidator.validate("не дата")
        self.assertFalse(result.is_valid)
        self.assertIn("формат даты", result.errors[0])
    
    def test_date_range(self):
        """Тест диапазона дат."""
        test_date = datetime(2024, 6, 15)
        min_date = datetime(2024, 1, 1)
        max_date = datetime(2024, 12, 31)
        
        # Валидная дата в диапазоне
        result = DateTimeValidator.validate(test_date, min_date=min_date, max_date=max_date)
        self.assertTrue(result.is_valid)
        
        # Дата раньше минимальной
        early_date = datetime(2023, 12, 31)
        result = DateTimeValidator.validate(early_date, min_date=min_date)
        self.assertFalse(result.is_valid)
        self.assertIn("не может быть раньше", result.errors[0])
        
        # Дата позже максимальной
        late_date = datetime(2025, 1, 1)
        result = DateTimeValidator.validate(late_date, max_date=max_date)
        self.assertFalse(result.is_valid)
        self.assertIn("не может быть позже", result.errors[0])


class TestListValidator(unittest.TestCase):
    """Тесты для ListValidator."""
    
    def test_valid_list(self):
        """Тест валидного списка."""
        result = ListValidator.validate([1, 2, 3, 4, 5])
        self.assertTrue(result.is_valid)
    
    def test_not_list(self):
        """Тест не-списка."""
        result = ListValidator.validate("не список")
        self.assertFalse(result.is_valid)
        self.assertIn("должно быть списком", result.errors[0])
    
    def test_list_length(self):
        """Тест длины списка."""
        # Слишком короткий список
        result = ListValidator.validate([1], min_length=3)
        self.assertFalse(result.is_valid)
        self.assertIn("Минимальная длина", result.errors[0])
        
        # Слишком длинный список
        result = ListValidator.validate([1, 2, 3, 4, 5], max_length=3)
        self.assertFalse(result.is_valid)
        self.assertIn("Максимальная длина", result.errors[0])
    
    def test_item_validation(self):
        """Тест валидации элементов списка."""
        # Список чисел с валидатором
        result = ListValidator.validate([1, 2, 3], item_validator=NumberValidator)
        self.assertTrue(result.is_valid)
        
        # Список с невалидными элементами
        result = ListValidator.validate([1, "не число", 3], item_validator=NumberValidator)
        self.assertFalse(result.is_valid)
        self.assertIn("Элемент 1", result.errors[0])


class TestProductValidator(unittest.TestCase):
    """Тесты для ProductValidator."""
    
    def test_valid_product(self):
        """Тест валидного товара."""
        product_data = {
            "id": "123",
            "name": "Тестовый товар",
            "brand": "Тестовый бренд",
            "current_price": 99.99,
            "marketplace_url": "https://example.com/product/123"
        }
        
        result = ProductValidator.validate_product_data(product_data)
        self.assertTrue(result.is_valid)
    
    def test_missing_required_fields(self):
        """Тест отсутствующих обязательных полей."""
        product_data = {
            "name": "Товар без ID"
        }
        
        result = ProductValidator.validate_product_data(product_data)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("ID:" in error for error in result.errors))
        self.assertTrue(any("Бренд:" in error for error in result.errors))
        self.assertTrue(any("Цена:" in error for error in result.errors))
    
    def test_invalid_price(self):
        """Тест невалидной цены."""
        product_data = {
            "id": "123",
            "name": "Товар",
            "brand": "Бренд",
            "current_price": -10  # Отрицательная цена
        }
        
        result = ProductValidator.validate_product_data(product_data)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Цена:" in error for error in result.errors))
    
    def test_invalid_url(self):
        """Тест невалидного URL."""
        product_data = {
            "id": "123",
            "name": "Товар",
            "brand": "Бренд",
            "current_price": 99.99,
            "marketplace_url": "не url"
        }
        
        result = ProductValidator.validate_product_data(product_data)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("URL маркетплейса:" in error for error in result.errors))


class TestDataCleaner(unittest.TestCase):
    """Тесты для DataCleaner."""
    
    def test_clean_string(self):
        """Тест очистки строки."""
        # Лишние пробелы
        result = DataCleaner.clean_string("  тест  строка  ")
        self.assertEqual(result, "тест строка")
        
        # Множественные пробелы
        result = DataCleaner.clean_string("тест    строка")
        self.assertEqual(result, "тест строка")
        
        # Не строка
        result = DataCleaner.clean_string(123)
        self.assertEqual(result, "123")
    
    def test_clean_price(self):
        """Тест очистки цены."""
        # Число
        result = DataCleaner.clean_price(99.99)
        self.assertEqual(result, 99.99)
        
        # Строка с символами валюты
        result = DataCleaner.clean_price("99,99 руб.")
        self.assertEqual(result, 9999.0)
        
        # Строка с пробелами
        result = DataCleaner.clean_price("1 234.56")
        self.assertEqual(result, 1234.56)
        
        # Невалидная строка
        result = DataCleaner.clean_price("не цена")
        self.assertIsNone(result)
        
        # None
        result = DataCleaner.clean_price(None)
        self.assertIsNone(result)
    
    def test_normalize_url(self):
        """Тест нормализации URL."""
        # URL без схемы
        result = DataCleaner.normalize_url("example.com")
        self.assertEqual(result, "https://example.com")
        
        # URL с лишними слешами
        result = DataCleaner.normalize_url("https://example.com/")
        self.assertEqual(result, "https://example.com")
        
        # Пустой URL
        result = DataCleaner.normalize_url("")
        self.assertEqual(result, "")
    
    def test_clean_product_data(self):
        """Тест очистки данных товара."""
        dirty_data = {
            "id": "  123  ",
            "name": "  Тестовый   товар  ",
            "current_price": "99.99 руб.",  # Используем точку вместо запятой
            "marketplace_url": "example.com/product",
            "competitor_prices": ["100.50", "не цена", "200,00"]
        }
        
        cleaned = DataCleaner.clean_product_data(dirty_data)
        
        self.assertEqual(cleaned["id"], "123")
        self.assertEqual(cleaned["name"], "Тестовый товар")
        self.assertEqual(cleaned["current_price"], 9999.0)
        self.assertEqual(cleaned["marketplace_url"], "https://example.com/product")
        self.assertEqual(len(cleaned["competitor_prices"]), 2)  # Невалидная цена удалена
        self.assertIn(100.5, cleaned["competitor_prices"])
        self.assertIn(200.0, cleaned["competitor_prices"])


class TestGlobalFunctions(unittest.TestCase):
    """Тесты для глобальных функций."""
    
    def test_validate_string_function(self):
        """Тест глобальной функции validate_string."""
        result = validate_string("тест")
        self.assertTrue(result.is_valid)
        
        result = validate_string("", required=True)
        self.assertFalse(result.is_valid)
    
    def test_validate_number_function(self):
        """Тест глобальной функции validate_number."""
        result = validate_number(42)
        self.assertTrue(result.is_valid)
        
        result = validate_number("не число")
        self.assertFalse(result.is_valid)
    
    def test_validate_price_function(self):
        """Тест глобальной функции validate_price."""
        result = validate_price(99.99)
        self.assertTrue(result.is_valid)
        
        result = validate_price(-10)
        self.assertFalse(result.is_valid)
    
    def test_validate_url_function(self):
        """Тест глобальной функции validate_url."""
        result = validate_url("https://example.com")
        self.assertTrue(result.is_valid)
        
        result = validate_url("не url")
        self.assertFalse(result.is_valid)
    
    def test_clean_data_function(self):
        """Тест глобальной функции clean_data."""
        dirty_data = {
            "name": "  тест  ",
            "current_price": "99,99"
        }
        
        cleaned = clean_data(dirty_data)
        self.assertEqual(cleaned["name"], "тест")
        self.assertEqual(cleaned["current_price"], 99.99)


if __name__ == '__main__':
    # Запуск тестов
    unittest.main(verbosity=2)