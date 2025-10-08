"""
Утилиты для форматирования данных под Google Sheets.

Содержит функции для конвертации типов данных, форматирования значений
и подготовки данных для записи в Google Sheets.
"""

from typing import Any, List, Dict, Optional, Union, Tuple
from datetime import datetime, date
from decimal import Decimal
import re
import json
from dataclasses import is_dataclass


class DataFormatter:
    """
    Класс для форматирования данных под Google Sheets.
    
    Предоставляет методы для конвертации различных типов данных
    в формат, совместимый с Google Sheets API.
    """
    
    # Максимальная длина текста в ячейке Google Sheets
    MAX_CELL_LENGTH = 50000
    
    # Форматы дат для Google Sheets
    DATE_FORMAT = "%d.%m.%Y"
    DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"
    TIME_FORMAT = "%H:%M:%S"
    
    @staticmethod
    def format_value(value: Any) -> str:
        """
        Форматирует значение для записи в Google Sheets.
        
        Args:
            value: Значение для форматирования
            
        Returns:
            str: Отформатированное значение
        """
        if value is None:
            return ""
        
        # Обработка булевых значений
        if isinstance(value, bool):
            return "Да" if value else "Нет"
        
        # Обработка чисел
        if isinstance(value, (int, float, Decimal)):
            return DataFormatter._format_number(value)
        
        # Обработка дат и времени
        if isinstance(value, datetime):
            # Если время 00:00:00, показываем только дату
            if value.time() == datetime.min.time():
                return value.strftime(DataFormatter.DATE_FORMAT)
            return value.strftime(DataFormatter.DATETIME_FORMAT)
        
        if isinstance(value, date):
            return value.strftime(DataFormatter.DATE_FORMAT)
        
        # Обработка списков
        if isinstance(value, list):
            return DataFormatter._format_list(value)
        
        # Обработка словарей
        if isinstance(value, dict):
            return DataFormatter._format_dict(value)
        
        # Обработка dataclass объектов
        if is_dataclass(value):
            return DataFormatter._format_dataclass(value)
        
        # Обработка строк
        if isinstance(value, str):
            return DataFormatter._format_string(value)
        
        # Для всех остальных типов
        return str(value)
    
    @staticmethod
    def _format_number(value: Union[int, float, Decimal]) -> str:
        """
        Форматирует числовые значения.
        
        Args:
            value: Числовое значение
            
        Returns:
            str: Отформатированное число
        """
        if isinstance(value, float):
            # Округляем до 2 знаков после запятой для цен, но убираем лишние нули
            if abs(value) < 0.01 and value != 0:
                return f"{value:.6f}".rstrip('0').rstrip('.')
            formatted = f"{value:.2f}".rstrip('0').rstrip('.')
            return formatted if formatted else "0"
        
        if isinstance(value, Decimal):
            return str(value)
        
        return str(value)
    
    @staticmethod
    def _format_string(value: str) -> str:
        """
        Форматирует строковые значения.
        
        Args:
            value: Строковое значение
            
        Returns:
            str: Отформатированная строка
        """
        # Удаляем лишние пробелы
        formatted = value.strip()
        
        # Ограничиваем длину
        if len(formatted) > DataFormatter.MAX_CELL_LENGTH:
            formatted = formatted[:DataFormatter.MAX_CELL_LENGTH - 3] + "..."
        
        # Заменяем переносы строк на пробелы для лучшего отображения
        formatted = re.sub(r'\s+', ' ', formatted)
        
        return formatted
    
    @staticmethod
    def _format_list(value: List[Any]) -> str:
        """
        Форматирует списки для отображения в ячейке.
        
        Args:
            value: Список значений
            
        Returns:
            str: Отформатированный список
        """
        if not value:
            return ""
        
        # Форматируем каждый элемент списка
        formatted_items = [DataFormatter.format_value(item) for item in value]
        
        # Объединяем через запятую
        result = ", ".join(formatted_items)
        
        # Ограничиваем длину
        if len(result) > DataFormatter.MAX_CELL_LENGTH:
            result = result[:DataFormatter.MAX_CELL_LENGTH - 3] + "..."
        
        return result
    
    @staticmethod
    def _format_dict(value: Dict[str, Any]) -> str:
        """
        Форматирует словари для отображения в ячейке.
        
        Args:
            value: Словарь значений
            
        Returns:
            str: Отформатированный словарь
        """
        if not value:
            return ""
        
        # Создаем читаемое представление словаря
        formatted_pairs = []
        for key, val in value.items():
            formatted_val = DataFormatter.format_value(val)
            formatted_pairs.append(f"{key}: {formatted_val}")
        
        result = "; ".join(formatted_pairs)
        
        # Ограничиваем длину
        if len(result) > DataFormatter.MAX_CELL_LENGTH:
            result = result[:DataFormatter.MAX_CELL_LENGTH - 3] + "..."
        
        return result
    
    @staticmethod
    def _format_dataclass(value: Any) -> str:
        """
        Форматирует dataclass объекты.
        
        Args:
            value: Dataclass объект
            
        Returns:
            str: Отформатированный объект
        """
        try:
            # Пытаемся использовать метод to_dict если он есть
            if hasattr(value, 'to_dict'):
                return DataFormatter._format_dict(value.to_dict())
            
            # Иначе используем __dict__
            return DataFormatter._format_dict(value.__dict__)
        except Exception:
            return str(value)
    
    @staticmethod
    def format_row(data: List[Any]) -> List[str]:
        """
        Форматирует строку данных для Google Sheets.
        
        Args:
            data: Список значений для строки
            
        Returns:
            List[str]: Отформатированная строка
        """
        if data is None:
            return []
        return [DataFormatter.format_value(value) for value in data]
    
    @staticmethod
    def format_rows(data: List[List[Any]]) -> List[List[str]]:
        """
        Форматирует множество строк данных.
        
        Args:
            data: Список строк данных
            
        Returns:
            List[List[str]]: Отформатированные строки
        """
        return [DataFormatter.format_row(row) for row in data]
    
    @staticmethod
    def convert_to_sheets_format(data: Any) -> Any:
        """
        Конвертирует данные в формат, совместимый с Google Sheets.
        
        Args:
            data: Данные для конвертации
            
        Returns:
            Any: Конвертированные данные
        """
        if isinstance(data, list):
            if data and isinstance(data[0], list):
                # Это матрица данных
                return DataFormatter.format_rows(data)
            else:
                # Это одна строка
                return DataFormatter.format_row(data)
        
        # Для одиночных значений
        return DataFormatter.format_value(data)
    
    @staticmethod
    def prepare_product_data(product: Any) -> List[str]:
        """
        Подготавливает данные товара для записи в Google Sheets.
        
        Args:
            product: Объект товара
            
        Returns:
            List[str]: Отформатированная строка данных товара
        """
        if hasattr(product, 'to_sheets_row'):
            raw_data = product.to_sheets_row()
            return DataFormatter.format_row(raw_data)
        
        # Базовая обработка если метод to_sheets_row отсутствует
        if hasattr(product, 'to_dict'):
            product_dict = product.to_dict()
            return DataFormatter.format_row(list(product_dict.values()))
        
        return [DataFormatter.format_value(product)]
    
    @staticmethod
    def prepare_headers(headers: List[str]) -> List[str]:
        """
        Подготавливает заголовки для Google Sheets.
        
        Args:
            headers: Список заголовков
            
        Returns:
            List[str]: Отформатированные заголовки
        """
        formatted_headers = []
        for header in headers:
            # Делаем заголовки более читаемыми
            formatted = header.replace('_', ' ').title()
            formatted_headers.append(formatted)
        
        return formatted_headers
    
    @staticmethod
    def create_summary_row(data: List[Dict[str, Any]], 
                          numeric_fields: List[str]) -> List[str]:
        """
        Создает итоговую строку с суммами и средними значениями.
        
        Args:
            data: Список данных для анализа
            numeric_fields: Поля для которых нужно считать суммы
            
        Returns:
            List[str]: Итоговая строка
        """
        if not data:
            return []
        
        summary = ["ИТОГО"]
        
        # Получаем все ключи из первого элемента
        all_keys = list(data[0].keys()) if data else []
        
        for key in all_keys[1:]:  # Пропускаем первый ключ (обычно ID)
            if key in numeric_fields:
                # Считаем сумму для числовых полей
                values = [item.get(key, 0) for item in data if isinstance(item.get(key), (int, float))]
                if values:
                    total = sum(values)
                    avg = total / len(values)
                    summary.append(f"Σ={DataFormatter._format_number(total)}, μ={DataFormatter._format_number(avg)}")
                else:
                    summary.append("")
            else:
                # Для нечисловых полей показываем количество
                non_empty = [item.get(key) for item in data if item.get(key)]
                summary.append(f"Записей: {len(non_empty)}")
        
        return summary


class TypeConverter:
    """
    Класс для конвертации типов данных.
    """
    
    @staticmethod
    def to_float(value: Any) -> Optional[float]:
        """
        Безопасно конвертирует значение в float.
        
        Args:
            value: Значение для конвертации
            
        Returns:
            Optional[float]: Конвертированное значение или None
        """
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, Decimal):
            return float(value)
        
        if isinstance(value, str):
            # Удаляем пробелы и заменяем запятые на точки
            cleaned = value.strip().replace(',', '.')
            
            # Удаляем все символы кроме цифр, точек и знака минус
            cleaned = re.sub(r'[^\d.-]', '', cleaned)
            
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def to_int(value: Any) -> Optional[int]:
        """
        Безопасно конвертирует значение в int.
        
        Args:
            value: Значение для конвертации
            
        Returns:
            Optional[int]: Конвертированное значение или None
        """
        float_val = TypeConverter.to_float(value)
        if float_val is not None:
            return int(float_val)
        return None
    
    @staticmethod
    def to_bool(value: Any) -> Optional[bool]:
        """
        Конвертирует значение в bool.
        
        Args:
            value: Значение для конвертации
            
        Returns:
            Optional[bool]: Конвертированное значение или None
        """
        if value is None:
            return None
            
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ('true', '1', 'да', 'yes', 'on', 'включено'):
                return True
            elif lower_val in ('false', '0', 'нет', 'no', 'off', 'выключено'):
                return False
            else:
                return None
        
        if isinstance(value, (int, float)):
            return value != 0
        
        return bool(value)
    
    @staticmethod
    def to_datetime(value: Any) -> Optional[datetime]:
        """
        Конвертирует значение в datetime.
        
        Args:
            value: Значение для конвертации
            
        Returns:
            Optional[datetime]: Конвертированное значение или None
        """
        if value is None:
            return None
            
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        
        if isinstance(value, str):
            # Пробуем различные форматы
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d.%m.%Y %H:%M:%S",
                "%d.%m.%Y",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        
        return None


# Глобальный экземпляр форматтера
formatter = DataFormatter()

# Удобные функции для быстрого доступа
def format_value(value: Any) -> str:
    """Форматирует значение для Google Sheets."""
    return formatter.format_value(value)

def format_row(data: List[Any]) -> List[str]:
    """Форматирует строку данных."""
    return formatter.format_row(data)

def convert_to_sheets_format(data: Any) -> Any:
    """Конвертирует данные в формат Google Sheets."""
    return formatter.convert_to_sheets_format(data)