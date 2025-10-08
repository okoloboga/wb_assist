"""
Клиент для работы с Google Sheets API.

Предоставляет методы для:
- Аутентификации через OAuth 2.0
- Создания новых таблиц
- Чтения и записи данных
- Массовых операций (batch operations)
"""

import os
import json
import time
import logging
from typing import List, Optional, Dict, Any, Callable
from functools import wraps
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .exceptions import (
    GoogleSheetsError, AuthenticationError, SpreadsheetNotFoundError,
    SheetNotFoundError, InvalidRangeError, QuotaExceededError,
    RateLimitError, NetworkError
)

# Настройка логирования
logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Декоратор для повторных попыток при ошибках API.
    
    Args:
        max_retries: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель для увеличения задержки
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except HttpError as e:
                    last_exception = e
                    error_code = e.resp.status
                    
                    # Не повторяем для некоторых типов ошибок
                    if error_code in [400, 401, 403, 404]:
                        break
                    
                    # Повторяем для временных ошибок
                    if error_code in [429, 500, 502, 503, 504] and attempt < max_retries:
                        logger.warning(
                            f"Попытка {attempt + 1}/{max_retries + 1} не удалась: {e}. "
                            f"Повтор через {current_delay} сек."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                        continue
                    break
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Попытка {attempt + 1}/{max_retries + 1} не удалась: {e}. "
                            f"Повтор через {current_delay} сек."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                        continue
                    break
            
            # Если все попытки исчерпаны, выбрасываем соответствующее исключение
            if isinstance(last_exception, HttpError):
                error_code = last_exception.resp.status
                error_message = str(last_exception)
                
                if error_code == 401:
                    raise AuthenticationError(f"Ошибка аутентификации: {error_message}")
                elif error_code == 404:
                    raise SpreadsheetNotFoundError(f"Таблица не найдена: {error_message}")
                elif error_code == 429:
                    raise RateLimitError(f"Превышен лимит запросов: {error_message}")
                elif error_code in [500, 502, 503, 504]:
                    raise NetworkError(f"Ошибка сервера: {error_message}")
                else:
                    raise GoogleSheetsError(f"Ошибка API: {error_message}")
            else:
                raise GoogleSheetsError(f"Неожиданная ошибка: {last_exception}")
        
        return wrapper
    return decorator


class GoogleSheetsClient:
    """
    Клиент для работы с Google Sheets API.
    
    Обеспечивает аутентификацию и базовые операции с таблицами.
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, credentials_path: str = 'config/credentials.json'):
        """
        Инициализация клиента.
        
        Args:
            credentials_path: Путь к файлу с OAuth credentials
        """
        self.credentials_path = credentials_path
        self.token_path = 'config/token.json'
        self.service = None
        logger.info(f"Инициализация GoogleSheetsClient с credentials: {credentials_path}")
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Аутентификация с Google API."""
        logger.info("Начало процесса аутентификации")
        creds = None
        
        # Загрузка существующих токенов
        if os.path.exists(self.token_path):
            logger.info("Загрузка существующих токенов")
            creds = Credentials.from_authorized_user_file(
                self.token_path, self.SCOPES
            )
        
        # Если токены недействительны, запрос новых
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Обновление истекших токенов")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f'Ошибка обновления токена: {e}')
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    error_msg = f'Файл credentials не найден: {self.credentials_path}'
                    logger.error(error_msg)
                    raise AuthenticationError(error_msg)
                
                logger.info("Запуск процесса OAuth авторизации")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Сохранение токенов
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info("Токены сохранены")
        
        self.service = build('sheets', 'v4', credentials=creds)
        logger.info("Аутентификация завершена успешно")
    
    @retry_on_error(max_retries=3)
    def create_spreadsheet(self, title: str) -> Optional[str]:
        """
        Создание новой таблицы.
        
        Args:
            title: Название таблицы
            
        Returns:
            ID созданной таблицы или None в случае ошибки
        """
        logger.info(f"Создание новой таблицы: {title}")
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            
            result = self.service.spreadsheets().create(
                body=spreadsheet
            ).execute()
            
            spreadsheet_id = result.get('spreadsheetId')
            logger.info(f'Таблица создана успешно: {title} (ID: {spreadsheet_id})')
            return spreadsheet_id
        
        except HttpError as error:
            logger.error(f'Ошибка создания таблицы {title}: {error}')
            raise
    
    @retry_on_error(max_retries=3)
    def get_spreadsheet_info(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о таблице.
        
        Args:
            spreadsheet_id: ID таблицы
            
        Returns:
            Информация о таблице или None в случае ошибки
        """
        logger.debug(f"Получение информации о таблице: {spreadsheet_id}")
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            logger.debug(f"Информация о таблице {spreadsheet_id} получена")
            return result
        
        except HttpError as error:
            logger.error(f'Ошибка получения информации о таблице {spreadsheet_id}: {error}')
            raise
    
    @retry_on_error(max_retries=3)
    def read_values(self, spreadsheet_id: str, range_name: str) -> List[List[str]]:
        """
        Чтение данных из таблицы.
        
        Args:
            spreadsheet_id: ID таблицы
            range_name: Диапазон ячеек (например, 'Sheet1!A1:C10')
            
        Returns:
            Список строк с данными
        """
        logger.debug(f"Чтение данных из {spreadsheet_id}, диапазон: {range_name}")
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            logger.info(f'Прочитано {len(values)} строк из диапазона {range_name}')
            return values
        
        except HttpError as error:
            logger.error(f'Ошибка чтения данных из {spreadsheet_id}, диапазон {range_name}: {error}')
            raise
    
    @retry_on_error(max_retries=3)
    def update_values(self, spreadsheet_id: str, range_name: str, 
                     values: List[List[Any]]) -> int:
        """
        Обновление данных в таблице.
        
        Args:
            spreadsheet_id: ID таблицы
            range_name: Диапазон ячеек
            values: Данные для записи
            
        Returns:
            Количество обновленных ячеек
        """
        logger.debug(f"Обновление данных в {spreadsheet_id}, диапазон: {range_name}")
        try:
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logger.info(f'Обновлено {updated_cells} ячеек в диапазоне {range_name}')
            return updated_cells
        
        except HttpError as error:
            logger.error(f'Ошибка обновления данных в {spreadsheet_id}, диапазон {range_name}: {error}')
            raise
    
    @retry_on_error(max_retries=3)
    def batch_update_values(self, spreadsheet_id: str, 
                           data: List[Dict[str, Any]]) -> int:
        """
        Массовое обновление данных в таблице.
        
        Args:
            spreadsheet_id: ID таблицы
            data: Список словарей с данными для обновления
                  Формат: [{'range': 'A1:B2', 'values': [['A1', 'B1'], ['A2', 'B2']]}]
            
        Returns:
            Общее количество обновленных ячеек
        """
        logger.debug(f"Массовое обновление данных в {spreadsheet_id}, {len(data)} диапазонов")
        try:
            body = {
                'valueInputOption': 'RAW',
                'data': data
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            total_updated_cells = result.get('totalUpdatedCells', 0)
            logger.info(f'Массовое обновление: {total_updated_cells} ячеек')
            return total_updated_cells
        
        except HttpError as error:
            logger.error(f'Ошибка массового обновления в {spreadsheet_id}: {error}')
            raise
    
    @retry_on_error(max_retries=3)
    def batch_get_values(self, spreadsheet_id: str, 
                        ranges: List[str]) -> Dict[str, List[List[str]]]:
        """
        Массовое чтение данных из нескольких диапазонов.
        
        Args:
            spreadsheet_id: ID таблицы
            ranges: Список диапазонов для чтения
            
        Returns:
            Словарь с данными по диапазонам
        """
        logger.debug(f"Массовое чтение данных из {spreadsheet_id}, {len(ranges)} диапазонов")
        try:
            result = self.service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges
            ).execute()
            
            value_ranges = result.get('valueRanges', [])
            data = {}
            
            for i, value_range in enumerate(value_ranges):
                range_name = ranges[i]
                values = value_range.get('values', [])
                data[range_name] = values
            
            logger.info(f'Прочитано данных из {len(ranges)} диапазонов')
            return data
        
        except HttpError as error:
            logger.error(f'Ошибка массового чтения из {spreadsheet_id}: {error}')
            raise
    
    @retry_on_error(max_retries=3)
    def format_cells(self, spreadsheet_id: str, requests: List[Dict[str, Any]]) -> bool:
        """
        Форматирование ячеек через batchUpdate.
        
        Args:
            spreadsheet_id: ID таблицы
            requests: Список запросов на форматирование
            
        Returns:
            True если операция успешна, False иначе
        """
        logger.debug(f"Форматирование ячеек в {spreadsheet_id}, {len(requests)} запросов")
        try:
            body = {
                'requests': requests
            }
            
            result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f'Выполнено {len(requests)} операций форматирования')
            return True
        
        except HttpError as error:
            logger.error(f'Ошибка форматирования в {spreadsheet_id}: {error}')
            raise
    
    @retry_on_error(max_retries=3)
    def add_sheet(self, spreadsheet_id: str, sheet_title: str) -> Optional[int]:
        """
        Добавление нового листа в таблицу.
        
        Args:
            spreadsheet_id: ID таблицы
            sheet_title: Название нового листа
            
        Returns:
            ID созданного листа или None в случае ошибки
        """
        logger.info(f"Добавление нового листа '{sheet_title}' в таблицу {spreadsheet_id}")
        try:
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': sheet_title
                    }
                }
            }]
            
            body = {
                'requests': requests
            }
            
            result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            sheet_id = result['replies'][0]['addSheet']['properties']['sheetId']
            logger.info(f'Добавлен лист: {sheet_title} (ID: {sheet_id})')
            return sheet_id
        
        except HttpError as error:
            logger.error(f'Ошибка добавления листа {sheet_title} в {spreadsheet_id}: {error}')
            raise