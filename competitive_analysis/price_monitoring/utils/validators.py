"""
Утилиты для валидации входных данных.

Содержит валидаторы для различных типов данных, используемых в системе
мониторинга цен конкурентов.
"""

from typing import Any, List, Dict, Optional, Union, Tuple
from datetime import datetime, date
import re
from urllib.parse import urlparse
from decimal import Decimal, InvalidOperation
import json


class ValidationError(Exception):
    """Исключение для ошибок валидации."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class ValidationResult:
    """Результат валидации."""
    
    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def add_error(self, error: str):
        """Добавляет ошибку валидации."""
        self.errors.append(error)
        self.is_valid = False
    
    def __bool__(self) -> bool:
        return self.is_valid
    
    def __str__(self) -> str:
        if self.is_valid:
            return "Валидация пройдена"
        return f"Ошибки валидации: {'; '.join(self.errors)}"


class BaseValidator:
    """Базовый класс для валидаторов."""
    
    @staticmethod
    def validate(value: Any, **kwargs) -> ValidationResult:
        """
        Валидирует значение.
        
        Args:
            value: Значение для валидации
            **kwargs: Дополнительные параметры валидации
            
        Returns:
            ValidationResult: Результат валидации
        """
        raise NotImplementedError("Метод validate должен быть реализован в подклассе")


class StringValidator(BaseValidator):
    """Валидатор для строковых значений."""
    
    @staticmethod
    def validate(value: Any, 
                min_length: int = 0, 
                max_length: int = 1000,
                pattern: Optional[str] = None,
                required: bool = True,
                allowed_values: Optional[List[str]] = None) -> ValidationResult:
        """
        Валидирует строковое значение.
        
        Args:
            value: Значение для валидации
            min_length: Минимальная длина строки
            max_length: Максимальная длина строки
            pattern: Регулярное выражение для проверки
            required: Обязательно ли поле
            allowed_values: Список допустимых значений
            
        Returns:
            ValidationResult: Результат валидации
        """
        result = ValidationResult()
        
        # Проверка на None
        if value is None:
            if required:
                result.add_error("Поле обязательно для заполнения")
            return result
        
        # Конвертация в строку
        if not isinstance(value, str):
            value = str(value)
        
        # Проверка на пустую строку при required=True
        if required and len(value.strip()) == 0:
            result.add_error("Поле не может быть пустым")
        
        # Проверка длины
        if len(value) < min_length:
            result.add_error(f"Минимальная длина: {min_length} символов")
        
        if len(value) > max_length:
            result.add_error(f"Максимальная длина: {max_length} символов")
        
        # Проверка паттерна
        if pattern and not re.match(pattern, value):
            result.add_error(f"Значение не соответствует паттерну: {pattern}")
        
        # Проверка допустимых значений
        if allowed_values and value not in allowed_values:
            result.add_error(f"Допустимые значения: {', '.join(allowed_values)}")
        
        return result


class NumberValidator(BaseValidator):
    """Валидатор для числовых значений."""
    
    @staticmethod
    def validate(value: Any,
                min_value: Optional[Union[int, float]] = None,
                max_value: Optional[Union[int, float]] = None,
                required: bool = True,
                allow_zero: bool = True,
                decimal_places: Optional[int] = None) -> ValidationResult:
        """
        Валидирует числовое значение.
        
        Args:
            value: Значение для валидации
            min_value: Минимальное значение
            max_value: Максимальное значение
            required: Обязательно ли поле
            allow_zero: Разрешен ли ноль
            decimal_places: Количество знаков после запятой
            
        Returns:
            ValidationResult: Результат валидации
        """
        result = ValidationResult()
        
        # Проверка на None
        if value is None:
            if required:
                result.add_error("Поле обязательно для заполнения")
            return result
        
        # Попытка конвертации в число
        try:
            if isinstance(value, str):
                # Очистка строки от лишних символов
                cleaned = value.strip().replace(',', '.')
                cleaned = re.sub(r'[^\d.-]', '', cleaned)
                numeric_value = float(cleaned)
            elif isinstance(value, (int, float, Decimal)):
                numeric_value = float(value)
            else:
                result.add_error("Значение должно быть числом")
                return result
        except (ValueError, InvalidOperation):
            result.add_error("Невозможно преобразовать в число")
            return result
        
        # Проверка на ноль
        if not allow_zero and numeric_value == 0:
            result.add_error("Значение не может быть равно нулю")
        
        # Проверка диапазона
        if min_value is not None and numeric_value < min_value:
            result.add_error(f"Минимальное значение: {min_value}")
        
        if max_value is not None and numeric_value > max_value:
            result.add_error(f"Максимальное значение: {max_value}")
        
        # Проверка знаков после запятой
        if decimal_places is not None:
            decimal_part = str(numeric_value).split('.')
            if len(decimal_part) > 1 and len(decimal_part[1]) > decimal_places:
                result.add_error(f"Максимум {decimal_places} знаков после запятой")
        
        return result


class PriceValidator(NumberValidator):
    """Специализированный валидатор для цен."""
    
    @staticmethod
    def validate(value: Any, 
                min_price: float = 0.01,
                max_price: float = 1000000.0,
                required: bool = True) -> ValidationResult:
        """
        Валидирует цену товара.
        
        Args:
            value: Цена для валидации
            min_price: Минимальная цена
            max_price: Максимальная цена
            required: Обязательно ли поле
            
        Returns:
            ValidationResult: Результат валидации
        """
        return NumberValidator.validate(
            value=value,
            min_value=min_price,
            max_value=max_price,
            required=required,
            allow_zero=False,
            decimal_places=2
        )


class URLValidator(BaseValidator):
    """Валидатор для URL адресов."""
    
    @staticmethod
    def validate(value: Any,
                required: bool = True,
                allowed_schemes: Optional[List[str]] = None) -> ValidationResult:
        """
        Валидирует URL адрес.
        
        Args:
            value: URL для валидации
            required: Обязательно ли поле
            allowed_schemes: Разрешенные схемы (http, https)
            
        Returns:
            ValidationResult: Результат валидации
        """
        result = ValidationResult()
        
        if value is None:
            if required:
                result.add_error("URL обязателен для заполнения")
            return result
        
        if not isinstance(value, str):
            result.add_error("URL должен быть строкой")
            return result
        
        # Парсинг URL
        try:
            parsed = urlparse(value)
        except Exception:
            result.add_error("Некорректный формат URL")
            return result
        
        # Проверка схемы
        if not parsed.scheme:
            result.add_error("URL должен содержать схему (http/https)")
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        if parsed.scheme not in allowed_schemes:
            result.add_error(f"Разрешенные схемы: {', '.join(allowed_schemes)}")
        
        # Проверка домена
        if not parsed.netloc:
            result.add_error("URL должен содержать домен")
        
        return result


class EmailValidator(BaseValidator):
    """Валидатор для email адресов."""
    
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    @staticmethod
    def validate(value: Any, required: bool = True) -> ValidationResult:
        """
        Валидирует email адрес.
        
        Args:
            value: Email для валидации
            required: Обязательно ли поле
            
        Returns:
            ValidationResult: Результат валидации
        """
        result = ValidationResult()
        
        if value is None:
            if required:
                result.add_error("Email обязателен для заполнения")
            return result
        
        if not isinstance(value, str):
            result.add_error("Email должен быть строкой")
            return result
        
        if not re.match(EmailValidator.EMAIL_PATTERN, value):
            result.add_error("Некорректный формат email")
        
        return result


class DateTimeValidator(BaseValidator):
    """Валидатор для дат и времени."""
    
    @staticmethod
    def validate(value: Any,
                required: bool = True,
                min_date: Optional[datetime] = None,
                max_date: Optional[datetime] = None,
                formats: Optional[List[str]] = None) -> ValidationResult:
        """
        Валидирует дату и время.
        
        Args:
            value: Дата для валидации
            required: Обязательно ли поле
            min_date: Минимальная дата
            max_date: Максимальная дата
            formats: Допустимые форматы дат
            
        Returns:
            ValidationResult: Результат валидации
        """
        result = ValidationResult()
        
        if value is None:
            if required:
                result.add_error("Дата обязательна для заполнения")
            return result
        
        # Если уже datetime объект
        if isinstance(value, datetime):
            dt_value = value
        elif isinstance(value, date):
            dt_value = datetime.combine(value, datetime.min.time())
        elif isinstance(value, str):
            # Попытка парсинга строки
            if formats is None:
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%d.%m.%Y %H:%M:%S",
                    "%d.%m.%Y",
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y"
                ]
            
            dt_value = None
            for fmt in formats:
                try:
                    dt_value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            
            if dt_value is None:
                result.add_error(f"Неверный формат даты. Допустимые форматы: {', '.join(formats)}")
                return result
        else:
            result.add_error("Дата должна быть строкой или datetime объектом")
            return result
        
        # Проверка диапазона
        if min_date and dt_value < min_date:
            result.add_error(f"Дата не может быть раньше {min_date.strftime('%Y-%m-%d')}")
        
        if max_date and dt_value > max_date:
            result.add_error(f"Дата не может быть позже {max_date.strftime('%Y-%m-%d')}")
        
        return result


class ListValidator(BaseValidator):
    """Валидатор для списков."""
    
    @staticmethod
    def validate(value: Any,
                min_length: int = 0,
                max_length: int = 1000,
                required: bool = True,
                item_validator: Optional[BaseValidator] = None) -> ValidationResult:
        """
        Валидирует список.
        
        Args:
            value: Список для валидации
            min_length: Минимальная длина списка
            max_length: Максимальная длина списка
            required: Обязательно ли поле
            item_validator: Валидатор для элементов списка
            
        Returns:
            ValidationResult: Результат валидации
        """
        result = ValidationResult()
        
        if value is None:
            if required:
                result.add_error("Список обязателен для заполнения")
            return result
        
        if not isinstance(value, list):
            result.add_error("Значение должно быть списком")
            return result
        
        # Проверка длины
        if len(value) < min_length:
            result.add_error(f"Минимальная длина списка: {min_length}")
        
        if len(value) > max_length:
            result.add_error(f"Максимальная длина списка: {max_length}")
        
        # Валидация элементов списка
        if item_validator:
            for i, item in enumerate(value):
                item_result = item_validator.validate(item)
                if not item_result.is_valid:
                    for error in item_result.errors:
                        result.add_error(f"Элемент {i}: {error}")
        
        return result


class ProductValidator:
    """Комплексный валидатор для товаров."""
    
    @staticmethod
    def validate_product_data(data: Dict[str, Any]) -> ValidationResult:
        """
        Валидирует данные товара.
        
        Args:
            data: Словарь с данными товара
            
        Returns:
            ValidationResult: Результат валидации
        """
        result = ValidationResult()
        
        # Валидация ID
        id_result = StringValidator.validate(
            data.get('id'), 
            min_length=1, 
            max_length=100,
            required=True
        )
        if not id_result.is_valid:
            for error in id_result.errors:
                result.add_error(f"ID: {error}")
        
        # Валидация названия
        name_result = StringValidator.validate(
            data.get('name'),
            min_length=1,
            max_length=500,
            required=True
        )
        if not name_result.is_valid:
            for error in name_result.errors:
                result.add_error(f"Название: {error}")
        
        # Валидация бренда
        brand_result = StringValidator.validate(
            data.get('brand'),
            min_length=1,
            max_length=200,
            required=True
        )
        if not brand_result.is_valid:
            for error in brand_result.errors:
                result.add_error(f"Бренд: {error}")
        
        # Валидация цены
        price_result = PriceValidator.validate(
            data.get('current_price'),
            required=True
        )
        if not price_result.is_valid:
            for error in price_result.errors:
                result.add_error(f"Цена: {error}")
        
        # Валидация URL маркетплейса
        if data.get('marketplace_url'):
            url_result = URLValidator.validate(
                data.get('marketplace_url'),
                required=False
            )
            if not url_result.is_valid:
                for error in url_result.errors:
                    result.add_error(f"URL маркетплейса: {error}")
        
        # Валидация списка цен конкурентов
        if data.get('competitor_prices'):
            prices_result = ListValidator.validate(
                data.get('competitor_prices'),
                required=False,
                item_validator=PriceValidator
            )
            if not prices_result.is_valid:
                for error in prices_result.errors:
                    result.add_error(f"Цены конкурентов: {error}")
        
        return result


class DataCleaner:
    """Класс для очистки и нормализации данных."""
    
    @staticmethod
    def clean_string(value: str) -> str:
        """
        Очищает строку от лишних символов.
        
        Args:
            value: Строка для очистки
            
        Returns:
            str: Очищенная строка
        """
        if not isinstance(value, str):
            return str(value)
        
        # Удаляем лишние пробелы
        cleaned = value.strip()
        
        # Заменяем множественные пробелы на одинарные
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Удаляем управляющие символы
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        return cleaned
    
    @staticmethod
    def clean_price(value: Any) -> Optional[float]:
        """
        Очищает и нормализует цену.
        
        Args:
            value: Значение цены
            
        Returns:
            Optional[float]: Очищенная цена или None
        """
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Удаляем все кроме цифр, точек и запятых
            cleaned = re.sub(r'[^\d.,]', '', value)
            
            # Заменяем запятые на точки
            cleaned = cleaned.replace(',', '.')
            
            # Если несколько точек, оставляем только последнюю
            parts = cleaned.split('.')
            if len(parts) > 2:
                cleaned = '.'.join(parts[:-1]).replace('.', '') + '.' + parts[-1]
            
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Нормализует URL.
        
        Args:
            url: URL для нормализации
            
        Returns:
            str: Нормализованный URL
        """
        if not url:
            return ""
        
        # Добавляем схему если отсутствует
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Удаляем лишние слеши в конце
        url = url.rstrip('/')
        
        return url
    
    @staticmethod
    def clean_product_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Очищает данные товара.
        
        Args:
            data: Данные товара
            
        Returns:
            Dict[str, Any]: Очищенные данные
        """
        cleaned = {}
        
        # Очистка строковых полей
        string_fields = ['id', 'name', 'brand', 'article', 'sku', 'category']
        for field in string_fields:
            if field in data:
                cleaned[field] = DataCleaner.clean_string(data[field])
        
        # Очистка цены
        if 'current_price' in data:
            cleaned['current_price'] = DataCleaner.clean_price(data['current_price'])
        
        # Очистка URL
        if 'marketplace_url' in data:
            cleaned['marketplace_url'] = DataCleaner.normalize_url(data['marketplace_url'])
        
        # Очистка списка цен конкурентов
        if 'competitor_prices' in data and isinstance(data['competitor_prices'], list):
            cleaned_prices = []
            for price in data['competitor_prices']:
                clean_price = DataCleaner.clean_price(price)
                if clean_price is not None:
                    cleaned_prices.append(clean_price)
            cleaned['competitor_prices'] = cleaned_prices
        
        # Копируем остальные поля без изменений
        for key, value in data.items():
            if key not in cleaned:
                cleaned[key] = value
        
        return cleaned


# Глобальные экземпляры валидаторов для удобства
string_validator = StringValidator()
number_validator = NumberValidator()
price_validator = PriceValidator()
url_validator = URLValidator()
email_validator = EmailValidator()
datetime_validator = DateTimeValidator()
list_validator = ListValidator()
product_validator = ProductValidator()
data_cleaner = DataCleaner()


# Удобные функции для быстрого доступа
def validate_string(value: Any, **kwargs) -> ValidationResult:
    """Валидирует строку."""
    return string_validator.validate(value, **kwargs)

def validate_number(value: Any, **kwargs) -> ValidationResult:
    """Валидирует число."""
    return number_validator.validate(value, **kwargs)

def validate_price(value: Any, **kwargs) -> ValidationResult:
    """Валидирует цену."""
    return price_validator.validate(value, **kwargs)

def validate_url(value: Any, **kwargs) -> ValidationResult:
    """Валидирует URL."""
    return url_validator.validate(value, **kwargs)

def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Очищает данные."""
    return data_cleaner.clean_product_data(data)