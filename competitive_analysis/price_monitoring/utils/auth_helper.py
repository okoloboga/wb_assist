"""
Вспомогательный модуль для аутентификации OAuth 2.0 с Google API.

Обеспечивает безопасную аутентификацию, управление токенами
и автоматическое обновление учетных данных.
"""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Настройка логирования
logger = logging.getLogger(__name__)


class AuthHelper:
    """
    Помощник для аутентификации OAuth 2.0 с Google API.
    
    Управляет процессом аутентификации, сохранением и обновлением токенов,
    а также предоставляет методы для работы с различными Google API.
    """
    
    # Области доступа для Google Sheets API
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, 
                 credentials_file: str = 'credentials.json',
                 token_file: str = 'token.pickle',
                 config_dir: Optional[str] = None):
        """
        Инициализация помощника аутентификации.
        
        Args:
            credentials_file: Путь к файлу с учетными данными OAuth 2.0
            token_file: Путь к файлу для сохранения токена
            config_dir: Директория для конфигурационных файлов
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / 'config'
        self.credentials_file = self.config_dir / credentials_file
        self.token_file = self.config_dir / token_file
        
        self._credentials: Optional[Credentials] = None
        self._service_cache: Dict[str, Any] = {}
        
        # Создаем директорию конфигурации если не существует
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AuthHelper инициализирован с config_dir: {self.config_dir}")
    
    @property
    def credentials(self) -> Optional[Credentials]:
        """
        Получение текущих учетных данных.
        
        Returns:
            Объект Credentials или None если не аутентифицирован
        """
        return self._credentials
    
    @property
    def is_authenticated(self) -> bool:
        """
        Проверка статуса аутентификации.
        
        Returns:
            True если пользователь аутентифицирован
        """
        return self._credentials is not None and self._credentials.valid
    
    def authenticate(self, force_reauth: bool = False) -> bool:
        """
        Выполнение аутентификации OAuth 2.0.
        
        Args:
            force_reauth: Принудительная повторная аутентификация
            
        Returns:
            True если аутентификация успешна
            
        Raises:
            FileNotFoundError: Если файл credentials.json не найден
            Exception: При ошибках аутентификации
        """
        try:
            # Загружаем существующий токен если не принудительная аутентификация
            if not force_reauth:
                self._load_existing_token()
            
            # Проверяем валидность токена
            if self._credentials and self._credentials.valid:
                logger.info("Используются существующие валидные учетные данные")
                return True
            
            # Обновляем токен если возможно
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                logger.info("Обновление истекшего токена")
                self._refresh_token()
                if self._credentials.valid:
                    self._save_token()
                    return True
            
            # Выполняем новую аутентификацию
            logger.info("Выполнение новой аутентификации OAuth 2.0")
            self._perform_oauth_flow()
            
            if self._credentials:
                self._save_token()
                logger.info("Аутентификация успешно завершена")
                return True
            
            return False
            
        except FileNotFoundError:
            logger.error(f"Файл учетных данных не найден: {self.credentials_file}")
            raise FileNotFoundError(
                f"Файл credentials.json не найден по пути: {self.credentials_file}\n"
                "Скачайте файл из Google Cloud Console и поместите его в директорию config/"
            )
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            raise
    
    def _load_existing_token(self) -> None:
        """Загрузка существующего токена из файла."""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'rb') as token:
                    self._credentials = pickle.load(token)
                logger.debug("Токен загружен из файла")
            except Exception as e:
                logger.warning(f"Не удалось загрузить токен: {e}")
                self._credentials = None
    
    def _refresh_token(self) -> None:
        """Обновление истекшего токена."""
        try:
            self._credentials.refresh(Request())
            logger.info("Токен успешно обновлен")
        except Exception as e:
            logger.error(f"Ошибка обновления токена: {e}")
            self._credentials = None
    
    def _perform_oauth_flow(self) -> None:
        """Выполнение OAuth 2.0 flow для получения нового токена."""
        if not self.credentials_file.exists():
            raise FileNotFoundError(f"Файл учетных данных не найден: {self.credentials_file}")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.credentials_file), 
            self.SCOPES
        )
        
        # Запускаем локальный сервер для получения авторизационного кода
        self._credentials = flow.run_local_server(
            port=0,
            prompt='consent',
            authorization_prompt_message='Откройте браузер для авторизации...',
            success_message='Авторизация завершена! Можете закрыть это окно.'
        )
    
    def _save_token(self) -> None:
        """Сохранение токена в файл."""
        try:
            with open(self.token_file, 'wb') as token:
                pickle.dump(self._credentials, token)
            logger.debug("Токен сохранен в файл")
        except Exception as e:
            logger.error(f"Ошибка сохранения токена: {e}")
    
    def get_service(self, service_name: str, version: str = 'v4') -> Any:
        """
        Получение сервиса Google API.
        
        Args:
            service_name: Название сервиса (например, 'sheets', 'drive')
            version: Версия API
            
        Returns:
            Объект сервиса Google API
            
        Raises:
            Exception: Если не аутентифицирован или ошибка создания сервиса
        """
        if not self.is_authenticated:
            raise Exception("Необходима аутентификация. Вызовите authenticate() сначала.")
        
        service_key = f"{service_name}_{version}"
        
        # Используем кэш для сервисов
        if service_key not in self._service_cache:
            try:
                self._service_cache[service_key] = build(
                    service_name, 
                    version, 
                    credentials=self._credentials
                )
                logger.debug(f"Создан сервис {service_name} v{version}")
            except Exception as e:
                logger.error(f"Ошибка создания сервиса {service_name}: {e}")
                raise
        
        return self._service_cache[service_key]
    
    def get_sheets_service(self):
        """
        Получение сервиса Google Sheets API.
        
        Returns:
            Объект сервиса Google Sheets
        """
        return self.get_service('sheets', 'v4')
    
    def get_drive_service(self):
        """
        Получение сервиса Google Drive API.
        
        Returns:
            Объект сервиса Google Drive
        """
        return self.get_service('drive', 'v3')
    
    def revoke_credentials(self) -> bool:
        """
        Отзыв учетных данных и удаление токена.
        
        Returns:
            True если отзыв успешен
        """
        try:
            if self._credentials:
                # Отзываем токен
                self._credentials.revoke(Request())
                logger.info("Учетные данные отозваны")
            
            # Удаляем файл токена
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("Файл токена удален")
            
            # Очищаем кэш
            self._credentials = None
            self._service_cache.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отзыва учетных данных: {e}")
            return False
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Получение информации о пользователе.
        
        Returns:
            Словарь с информацией о пользователе или None
        """
        if not self.is_authenticated:
            return None
        
        try:
            # Используем People API для получения информации о пользователе
            service = self.get_service('people', 'v1')
            profile = service.people().get(
                resourceName='people/me',
                personFields='names,emailAddresses'
            ).execute()
            
            return {
                'name': profile.get('names', [{}])[0].get('displayName', 'Unknown'),
                'email': profile.get('emailAddresses', [{}])[0].get('value', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о пользователе: {e}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Тестирование подключения к Google API.
        
        Returns:
            Словарь с результатами тестирования
        """
        results = {
            'authenticated': False,
            'sheets_api': False,
            'drive_api': False,
            'user_info': None,
            'errors': []
        }
        
        try:
            # Проверяем аутентификацию
            results['authenticated'] = self.is_authenticated
            
            if not results['authenticated']:
                results['errors'].append("Не аутентифицирован")
                return results
            
            # Тестируем Sheets API
            try:
                sheets_service = self.get_sheets_service()
                # Простой запрос для проверки доступности API
                sheets_service.spreadsheets().create(body={
                    'properties': {'title': 'Test Connection'}
                }).execute()
                results['sheets_api'] = True
            except Exception as e:
                results['errors'].append(f"Sheets API: {e}")
            
            # Тестируем Drive API
            try:
                drive_service = self.get_drive_service()
                # Простой запрос для проверки доступности API
                drive_service.files().list(pageSize=1).execute()
                results['drive_api'] = True
            except Exception as e:
                results['errors'].append(f"Drive API: {e}")
            
            # Получаем информацию о пользователе
            results['user_info'] = self.get_user_info()
            
        except Exception as e:
            results['errors'].append(f"Общая ошибка: {e}")
        
        return results
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Получение информации о токене.
        
        Returns:
            Словарь с информацией о токене или None
        """
        if not self._credentials:
            return None
        
        info = {
            'valid': self._credentials.valid,
            'expired': self._credentials.expired,
            'has_refresh_token': bool(self._credentials.refresh_token),
            'scopes': getattr(self._credentials, 'scopes', [])
        }
        
        # Добавляем информацию о времени истечения если доступна
        if hasattr(self._credentials, 'expiry') and self._credentials.expiry:
            info['expires_at'] = self._credentials.expiry.isoformat()
            info['expires_in_seconds'] = (
                self._credentials.expiry - datetime.utcnow()
            ).total_seconds()
        
        return info
    
    def validate_credentials_file(self) -> Dict[str, Any]:
        """
        Валидация файла credentials.json.
        
        Returns:
            Словарь с результатами валидации
        """
        result = {
            'valid': False,
            'exists': False,
            'readable': False,
            'has_required_fields': False,
            'errors': []
        }
        
        try:
            # Проверяем существование файла
            result['exists'] = self.credentials_file.exists()
            if not result['exists']:
                result['errors'].append(f"Файл не найден: {self.credentials_file}")
                return result
            
            # Проверяем читаемость файла
            try:
                with open(self.credentials_file, 'r', encoding='utf-8') as f:
                    credentials_data = json.load(f)
                result['readable'] = True
            except json.JSONDecodeError as e:
                result['errors'].append(f"Некорректный JSON: {e}")
                return result
            except Exception as e:
                result['errors'].append(f"Ошибка чтения файла: {e}")
                return result
            
            # Проверяем наличие обязательных полей
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            
            if 'installed' in credentials_data:
                installed = credentials_data['installed']
                missing_fields = [field for field in required_fields if field not in installed]
                
                if not missing_fields:
                    result['has_required_fields'] = True
                    result['valid'] = True
                else:
                    result['errors'].append(f"Отсутствуют обязательные поля: {missing_fields}")
            else:
                result['errors'].append("Отсутствует секция 'installed' в файле credentials")
            
        except Exception as e:
            result['errors'].append(f"Неожиданная ошибка: {e}")
        
        return result
    
    def validate_token_file(self) -> Dict[str, Any]:
        """
        Валидация файла токена.
        
        Returns:
            Словарь с результатами валидации
        """
        result = {
            'valid': False,
            'exists': False,
            'readable': False,
            'token_valid': False,
            'errors': []
        }
        
        try:
            # Проверяем существование файла
            result['exists'] = self.token_file.exists()
            if not result['exists']:
                result['errors'].append(f"Файл токена не найден: {self.token_file}")
                return result
            
            # Проверяем читаемость файла
            try:
                with open(self.token_file, 'rb') as f:
                    credentials = pickle.load(f)
                result['readable'] = True
            except Exception as e:
                result['errors'].append(f"Ошибка чтения файла токена: {e}")
                return result
            
            # Проверяем валидность токена
            if hasattr(credentials, 'valid'):
                result['token_valid'] = credentials.valid
                if credentials.valid:
                    result['valid'] = True
                else:
                    result['errors'].append("Токен недействителен или истек")
            else:
                result['errors'].append("Некорректный формат токена")
            
        except Exception as e:
            result['errors'].append(f"Неожиданная ошибка: {e}")
        
        return result
    
    def validate_scopes(self, required_scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Валидация областей доступа (scopes).
        
        Args:
            required_scopes: Список требуемых областей доступа
            
        Returns:
            Словарь с результатами валидации
        """
        if required_scopes is None:
            required_scopes = self.SCOPES
        
        result = {
            'valid': False,
            'has_all_scopes': False,
            'current_scopes': [],
            'missing_scopes': [],
            'errors': []
        }
        
        try:
            if not self._credentials:
                result['errors'].append("Нет учетных данных для проверки")
                return result
            
            current_scopes = getattr(self._credentials, 'scopes', [])
            result['current_scopes'] = current_scopes
            
            missing_scopes = [scope for scope in required_scopes if scope not in current_scopes]
            result['missing_scopes'] = missing_scopes
            
            if not missing_scopes:
                result['has_all_scopes'] = True
                result['valid'] = True
            else:
                result['errors'].append(f"Отсутствуют области доступа: {missing_scopes}")
            
        except Exception as e:
            result['errors'].append(f"Ошибка проверки областей доступа: {e}")
        
        return result
    
    def is_token_expiring_soon(self, minutes_threshold: int = 30) -> bool:
        """
        Проверка, истекает ли токен в ближайшее время.
        
        Args:
            minutes_threshold: Порог в минутах для предупреждения
            
        Returns:
            True если токен истекает в ближайшее время
        """
        if not self._credentials or not hasattr(self._credentials, 'expiry'):
            return False
        
        if not self._credentials.expiry:
            return False
        
        time_until_expiry = self._credentials.expiry - datetime.utcnow()
        return time_until_expiry.total_seconds() < (minutes_threshold * 60)
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Получение полного статуса аутентификации.
        
        Returns:
            Словарь с полной информацией о статусе
        """
        status = {
            'authenticated': self.is_authenticated,
            'credentials_file': self.validate_credentials_file(),
            'token_file': self.validate_token_file(),
            'scopes': self.validate_scopes(),
            'token_info': self.get_token_info(),
            'user_info': self.get_user_info(),
            'expiring_soon': False,
            'recommendations': []
        }
        
        # Проверяем, истекает ли токен скоро
        if self._credentials:
            status['expiring_soon'] = self.is_token_expiring_soon()
            if status['expiring_soon']:
                status['recommendations'].append("Токен истекает в ближайшее время, рекомендуется обновление")
        
        # Добавляем рекомендации на основе статуса
        if not status['authenticated']:
            status['recommendations'].append("Необходима аутентификация")
        
        if not status['credentials_file']['valid']:
            status['recommendations'].append("Проверьте файл credentials.json")
        
        if not status['scopes']['valid']:
            status['recommendations'].append("Необходимо переаутентифицироваться с правильными областями доступа")
        
        return status

    @staticmethod
    def create_credentials_template() -> str:
        """
        Создание шаблона файла credentials.json.
        
        Returns:
            JSON строка с шаблоном
        """
        template = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID.googleusercontent.com",
                "project_id": "your-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        return json.dumps(template, indent=2)
    
    def setup_credentials_file(self, client_id: str, client_secret: str, project_id: str) -> None:
        """
        Создание файла credentials.json с предоставленными данными.
        
        Args:
            client_id: ID клиента OAuth 2.0
            client_secret: Секрет клиента OAuth 2.0
            project_id: ID проекта Google Cloud
        """
        credentials_data = {
            "installed": {
                "client_id": client_id,
                "project_id": project_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost"]
            }
        }
        
        with open(self.credentials_file, 'w', encoding='utf-8') as f:
            json.dump(credentials_data, f, indent=2)
        
        logger.info(f"Файл credentials.json создан: {self.credentials_file}")
    
    def __str__(self) -> str:
        """Строковое представление объекта."""
        status = "аутентифицирован" if self.is_authenticated else "не аутентифицирован"
        return f"AuthHelper({status}, config_dir={self.config_dir})"
    
    def __repr__(self) -> str:
        """Представление для отладки."""
        return f"AuthHelper(credentials_file='{self.credentials_file}', token_file='{self.token_file}')"


# Глобальный экземпляр для удобства использования
_auth_helper_instance: Optional[AuthHelper] = None


def get_auth_helper(config_dir: Optional[str] = None) -> AuthHelper:
    """
    Получение глобального экземпляра AuthHelper.
    
    Args:
        config_dir: Директория конфигурации (используется только при первом вызове)
        
    Returns:
        Экземпляр AuthHelper
    """
    global _auth_helper_instance
    
    if _auth_helper_instance is None:
        _auth_helper_instance = AuthHelper(config_dir=config_dir)
    
    return _auth_helper_instance


def reset_auth_helper() -> None:
    """Сброс глобального экземпляра AuthHelper."""
    global _auth_helper_instance
    _auth_helper_instance = None