"""
Конфигурация логирования для модуля мониторинга цен.

Предоставляет централизованную настройку логирования с различными уровнями
и форматами для разных компонентов системы.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Настройка системы логирования.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов (если None, используется logs/price_monitoring.log)
        max_file_size: Максимальный размер файла лога в байтах
        backup_count: Количество резервных файлов логов
        console_output: Выводить ли логи в консоль
    
    Returns:
        Настроенный logger
    """
    # Создание директории для логов
    if log_file is None:
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'price_monitoring.log')
    else:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очистка существующих обработчиков
    root_logger.handlers.clear()
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Обработчик для консоли
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Настройка специфичных логгеров
    setup_module_loggers(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Система логирования настроена. Уровень: {log_level}, Файл: {log_file}")
    
    return root_logger


def setup_module_loggers(log_level: str = 'INFO') -> None:
    """
    Настройка логгеров для специфичных модулей.
    
    Args:
        log_level: Уровень логирования
    """
    # Логгер для Google Sheets API
    sheets_logger = logging.getLogger('price_monitoring.core.google_sheets_client')
    sheets_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Логгер для мониторинга цен
    monitor_logger = logging.getLogger('price_monitoring.core.price_monitor')
    monitor_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Логгер для анализа конкурентов
    competitor_logger = logging.getLogger('price_monitoring.core.competitor_analyzer')
    competitor_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Логгер для уведомлений
    notification_logger = logging.getLogger('price_monitoring.core.notification_service')
    notification_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Снижение уровня логирования для внешних библиотек
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('google_auth_oauthlib').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Получение логгера с заданным именем.
    
    Args:
        name: Имя логгера
    
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    Миксин для добавления логирования в классы.
    
    Предоставляет удобный доступ к логгеру через self.logger
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Получение логгера для текущего класса."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")


# Настройка логирования по умолчанию при импорте модуля
if not logging.getLogger().handlers:
    setup_logging()