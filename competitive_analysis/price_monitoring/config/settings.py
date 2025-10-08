"""
Настройки и конфигурация модуля мониторинга цен.

Содержит все настройки для работы с Google Sheets API,
параметры мониторинга, уведомлений и другие конфигурации.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import timedelta
import logging


# Настройка логирования
logger = logging.getLogger(__name__)


@dataclass
class GoogleSheetsConfig:
    """Конфигурация для Google Sheets API."""
    
    # Файлы аутентификации
    credentials_file: str = 'credentials.json'
    token_file: str = 'token.pickle'
    
    # Области доступа
    scopes: List[str] = field(default_factory=lambda: [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ])
    
    # Настройки API
    api_version: str = 'v4'
    batch_size: int = 100  # Максимальное количество операций в batch запросе
    retry_attempts: int = 3
    retry_delay: float = 1.0  # Секунды между попытками
    
    # Настройки таблиц
    default_sheet_title: str = 'Мониторинг цен конкурентов'
    default_worksheet_name: str = 'Товары'
    
    # Форматирование
    date_format: str = '%Y-%m-%d %H:%M:%S'
    number_format: str = '0.00'
    currency_format: str = '#,##0.00₽'


@dataclass
class MonitoringConfig:
    """Конфигурация мониторинга цен."""
    
    # Интервалы обновления
    update_interval_hours: int = 6  # Интервал обновления цен в часах
    full_scan_interval_days: int = 1  # Полное сканирование раз в день
    
    # Пороги для уведомлений
    default_price_threshold: float = 5.0  # Процент изменения цены
    significant_change_threshold: float = 15.0  # Значительное изменение цены
    
    # Лимиты
    max_competitors_per_product: int = 10
    max_products_per_scan: int = 100
    
    # Таймауты
    request_timeout: int = 30  # Секунды
    page_load_timeout: int = 60  # Секунды для загрузки страницы
    
    # Настройки парсинга
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    delay_between_requests: float = 1.0  # Секунды между запросами
    
    # Повторные попытки
    max_retries: int = 3
    backoff_factor: float = 2.0


@dataclass
class NotificationConfig:
    """Конфигурация уведомлений."""
    
    # Включение уведомлений
    enabled: bool = True
    
    # Типы уведомлений
    email_enabled: bool = False
    telegram_enabled: bool = False
    webhook_enabled: bool = False
    
    # Email настройки
    smtp_server: str = 'smtp.gmail.com'
    smtp_port: int = 587
    email_from: str = ''
    email_password: str = ''
    email_to: List[str] = field(default_factory=list)
    
    # Telegram настройки
    telegram_bot_token: str = ''
    telegram_chat_ids: List[str] = field(default_factory=list)
    
    # Webhook настройки
    webhook_url: str = ''
    webhook_headers: Dict[str, str] = field(default_factory=dict)
    
    # Настройки отправки
    batch_notifications: bool = True
    notification_cooldown_minutes: int = 60  # Минимальный интервал между уведомлениями


@dataclass
class LoggingConfig:
    """Конфигурация логирования."""
    
    # Уровень логирования
    level: str = 'INFO'
    
    # Файлы логов
    log_file: str = 'price_monitoring.log'
    error_log_file: str = 'price_monitoring_errors.log'
    
    # Форматирование
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    
    # Ротация логов
    max_file_size_mb: int = 10
    backup_count: int = 5
    
    # Консольный вывод
    console_output: bool = True
    console_level: str = 'INFO'


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных (для будущего использования)."""
    
    # Тип БД
    db_type: str = 'sqlite'  # sqlite, postgresql, mysql
    
    # SQLite настройки
    sqlite_file: str = 'price_monitoring.db'
    
    # PostgreSQL/MySQL настройки
    host: str = 'localhost'
    port: int = 5432
    database: str = 'price_monitoring'
    username: str = ''
    password: str = ''
    
    # Настройки подключения
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30


class Settings:
    """
    Основной класс настроек модуля мониторинга цен.
    
    Управляет загрузкой, сохранением и валидацией всех конфигураций.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Инициализация настроек.
        
        Args:
            config_dir: Директория с конфигурационными файлами
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config_file = self.config_dir / 'config.json'
        
        # Инициализация конфигураций с значениями по умолчанию
        self.google_sheets = GoogleSheetsConfig()
        self.monitoring = MonitoringConfig()
        self.notifications = NotificationConfig()
        self.logging = LoggingConfig()
        self.database = DatabaseConfig()
        
        # Загружаем настройки из файла если существует
        self.load_config()
        
        logger.info(f"Настройки инициализированы из {self.config_dir}")
    
    def load_config(self) -> None:
        """Загрузка настроек из файла конфигурации."""
        if not self.config_file.exists():
            logger.info("Файл конфигурации не найден, используются настройки по умолчанию")
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Загружаем каждую секцию конфигурации
            if 'google_sheets' in config_data:
                self._update_config(self.google_sheets, config_data['google_sheets'])
            
            if 'monitoring' in config_data:
                self._update_config(self.monitoring, config_data['monitoring'])
            
            if 'notifications' in config_data:
                self._update_config(self.notifications, config_data['notifications'])
            
            if 'logging' in config_data:
                self._update_config(self.logging, config_data['logging'])
            
            if 'database' in config_data:
                self._update_config(self.database, config_data['database'])
            
            logger.info("Настройки успешно загружены из файла")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")
            logger.info("Используются настройки по умолчанию")
    
    def _update_config(self, config_obj: Any, config_data: Dict[str, Any]) -> None:
        """
        Обновление объекта конфигурации данными из словаря.
        
        Args:
            config_obj: Объект конфигурации для обновления
            config_data: Данные для обновления
        """
        for key, value in config_data.items():
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)
    
    def save_config(self) -> None:
        """Сохранение настроек в файл конфигурации."""
        try:
            # Создаем директорию если не существует
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                'google_sheets': asdict(self.google_sheets),
                'monitoring': asdict(self.monitoring),
                'notifications': asdict(self.notifications),
                'logging': asdict(self.logging),
                'database': asdict(self.database)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Настройки сохранены в {self.config_file}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
            raise
    
    def validate_config(self) -> List[str]:
        """
        Валидация настроек.
        
        Returns:
            Список ошибок валидации
        """
        errors = []
        
        # Валидация Google Sheets конфигурации
        if not self.google_sheets.credentials_file:
            errors.append("Не указан файл учетных данных Google Sheets")
        
        if not self.google_sheets.scopes:
            errors.append("Не указаны области доступа для Google Sheets API")
        
        # Валидация мониторинга
        if self.monitoring.update_interval_hours <= 0:
            errors.append("Интервал обновления должен быть больше 0")
        
        if self.monitoring.default_price_threshold < 0:
            errors.append("Порог изменения цены не может быть отрицательным")
        
        # Валидация уведомлений
        if self.notifications.enabled:
            if (self.notifications.email_enabled and 
                not self.notifications.email_from):
                errors.append("Для email уведомлений необходимо указать отправителя")
            
            if (self.notifications.telegram_enabled and 
                not self.notifications.telegram_bot_token):
                errors.append("Для Telegram уведомлений необходимо указать токен бота")
        
        # Валидация логирования
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level not in valid_levels:
            errors.append(f"Неверный уровень логирования: {self.logging.level}")
        
        return errors
    
    def get_credentials_path(self) -> Path:
        """
        Получение полного пути к файлу учетных данных.
        
        Returns:
            Путь к файлу credentials.json
        """
        return self.config_dir / self.google_sheets.credentials_file
    
    def get_token_path(self) -> Path:
        """
        Получение полного пути к файлу токена.
        
        Returns:
            Путь к файлу token.pickle
        """
        return self.config_dir / self.google_sheets.token_file
    
    def get_log_path(self) -> Path:
        """
        Получение полного пути к файлу логов.
        
        Returns:
            Путь к файлу логов
        """
        return self.config_dir / self.logging.log_file
    
    def get_error_log_path(self) -> Path:
        """
        Получение полного пути к файлу логов ошибок.
        
        Returns:
            Путь к файлу логов ошибок
        """
        return self.config_dir / self.logging.error_log_file
    
    def setup_logging(self) -> None:
        """Настройка системы логирования."""
        import logging.handlers
        
        # Создаем директорию для логов
        log_dir = self.get_log_path().parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.logging.level))
        
        # Очищаем существующие обработчики
        root_logger.handlers.clear()
        
        # Форматтер
        formatter = logging.Formatter(
            self.logging.log_format,
            datefmt=self.logging.date_format
        )
        
        # Файловый обработчик с ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            self.get_log_path(),
            maxBytes=self.logging.max_file_size_mb * 1024 * 1024,
            backupCount=self.logging.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, self.logging.level))
        root_logger.addHandler(file_handler)
        
        # Обработчик для ошибок
        error_handler = logging.handlers.RotatingFileHandler(
            self.get_error_log_path(),
            maxBytes=self.logging.max_file_size_mb * 1024 * 1024,
            backupCount=self.logging.backup_count,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # Консольный обработчик
        if self.logging.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, self.logging.console_level))
            root_logger.addHandler(console_handler)
        
        logger.info("Система логирования настроена")
    
    def get_environment_variables(self) -> Dict[str, str]:
        """
        Получение переменных окружения для конфигурации.
        
        Returns:
            Словарь с переменными окружения
        """
        env_vars = {}
        
        # Google Sheets
        if os.getenv('GOOGLE_CREDENTIALS_FILE'):
            env_vars['google_credentials_file'] = os.getenv('GOOGLE_CREDENTIALS_FILE')
        
        # Уведомления
        if os.getenv('EMAIL_FROM'):
            env_vars['email_from'] = os.getenv('EMAIL_FROM')
        
        if os.getenv('EMAIL_PASSWORD'):
            env_vars['email_password'] = os.getenv('EMAIL_PASSWORD')
        
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            env_vars['telegram_bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # База данных
        if os.getenv('DATABASE_URL'):
            env_vars['database_url'] = os.getenv('DATABASE_URL')
        
        return env_vars
    
    def apply_environment_variables(self) -> None:
        """Применение переменных окружения к настройкам."""
        env_vars = self.get_environment_variables()
        
        # Применяем переменные окружения
        if 'google_credentials_file' in env_vars:
            self.google_sheets.credentials_file = env_vars['google_credentials_file']
        
        if 'email_from' in env_vars:
            self.notifications.email_from = env_vars['email_from']
        
        if 'email_password' in env_vars:
            self.notifications.email_password = env_vars['email_password']
        
        if 'telegram_bot_token' in env_vars:
            self.notifications.telegram_bot_token = env_vars['telegram_bot_token']
        
        logger.info("Переменные окружения применены к настройкам")
    
    def create_default_config_file(self) -> None:
        """Создание файла конфигурации по умолчанию."""
        if self.config_file.exists():
            logger.warning("Файл конфигурации уже существует")
            return
        
        self.save_config()
        logger.info(f"Создан файл конфигурации по умолчанию: {self.config_file}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование настроек в словарь.
        
        Returns:
            Словарь со всеми настройками
        """
        return {
            'google_sheets': asdict(self.google_sheets),
            'monitoring': asdict(self.monitoring),
            'notifications': asdict(self.notifications),
            'logging': asdict(self.logging),
            'database': asdict(self.database)
        }
    
    def __str__(self) -> str:
        """Строковое представление настроек."""
        return f"Settings(config_dir={self.config_dir})"
    
    def __repr__(self) -> str:
        """Представление для отладки."""
        return f"Settings(config_file='{self.config_file}')"


# Глобальный экземпляр настроек
_settings_instance: Optional[Settings] = None


def get_settings(config_dir: Optional[str] = None) -> Settings:
    """
    Получение глобального экземпляра настроек.
    
    Args:
        config_dir: Директория конфигурации (используется только при первом вызове)
        
    Returns:
        Экземпляр Settings
    """
    global _settings_instance
    
    if _settings_instance is None:
        _settings_instance = Settings(config_dir=config_dir)
    
    return _settings_instance


def reset_settings() -> None:
    """Сброс глобального экземпляра настроек."""
    global _settings_instance
    _settings_instance = None


# Константы для удобства
DEFAULT_CONFIG_DIR = Path(__file__).parent
DEFAULT_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]