"""
Тесты для модуля настроек и конфигурации.

Включает тесты для Settings и связанных компонентов.
"""

import unittest
import sys
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

# Добавляем путь к модулю в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    Settings, 
    GoogleSheetsConfig, 
    MonitoringConfig, 
    NotificationConfig,
    LoggingConfig,
    DatabaseConfig,
    get_settings
)


class TestGoogleSheetsConfig(unittest.TestCase):
    """Тесты для настроек Google Sheets API."""
    
    def test_default_initialization(self):
        """Тест инициализации с значениями по умолчанию."""
        config = GoogleSheetsConfig()
        
        self.assertEqual(config.credentials_file, 'credentials.json')
        self.assertEqual(config.token_file, 'token.pickle')
        self.assertEqual(config.scopes, [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ])
        self.assertEqual(config.api_version, 'v4')
        self.assertEqual(config.batch_size, 100)
        self.assertEqual(config.retry_attempts, 3)
        self.assertEqual(config.retry_delay, 1.0)


class TestMonitoringConfig(unittest.TestCase):
    """Тесты для настроек мониторинга."""
    
    def test_default_initialization(self):
        """Тест инициализации с значениями по умолчанию."""
        config = MonitoringConfig()
        
        self.assertEqual(config.update_interval_hours, 6)
        self.assertEqual(config.full_scan_interval_days, 1)
        self.assertEqual(config.default_price_threshold, 5.0)
        self.assertEqual(config.significant_change_threshold, 15.0)
        self.assertEqual(config.max_competitors_per_product, 10)
        self.assertEqual(config.max_products_per_scan, 100)
        self.assertEqual(config.request_timeout, 30)
        self.assertEqual(config.page_load_timeout, 60)


class TestNotificationConfig(unittest.TestCase):
    """Тесты для настроек уведомлений."""
    
    def test_default_initialization(self):
        """Тест инициализации с значениями по умолчанию."""
        config = NotificationConfig()
        
        self.assertTrue(config.enabled)
        self.assertFalse(config.email_enabled)
        self.assertFalse(config.telegram_enabled)
        self.assertFalse(config.webhook_enabled)
        self.assertEqual(config.smtp_server, 'smtp.gmail.com')
        self.assertEqual(config.smtp_port, 587)
        self.assertEqual(config.email_from, '')
        self.assertEqual(config.email_password, '')
        self.assertEqual(config.email_to, [])
        self.assertEqual(config.telegram_bot_token, '')
        self.assertEqual(config.telegram_chat_ids, [])
        self.assertEqual(config.webhook_url, '')
        self.assertEqual(config.webhook_headers, {})
        self.assertTrue(config.batch_notifications)
        self.assertEqual(config.notification_cooldown_minutes, 60)


class TestLoggingConfig(unittest.TestCase):
    """Тесты для настроек логирования."""
    
    def test_default_initialization(self):
        """Тест инициализации с значениями по умолчанию."""
        config = LoggingConfig()
        
        self.assertEqual(config.level, 'INFO')
        self.assertEqual(config.log_file, 'price_monitoring.log')
        self.assertEqual(config.error_log_file, 'price_monitoring_errors.log')
        self.assertEqual(config.log_format, '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.assertEqual(config.date_format, '%Y-%m-%d %H:%M:%S')
        self.assertEqual(config.max_file_size_mb, 10)
        self.assertEqual(config.backup_count, 5)
        self.assertTrue(config.console_output)
        self.assertEqual(config.console_level, 'INFO')


class TestDatabaseConfig(unittest.TestCase):
    """Тесты для настроек базы данных."""
    
    def test_default_initialization(self):
        """Тест инициализации с значениями по умолчанию."""
        config = DatabaseConfig()
        
        self.assertEqual(config.db_type, 'sqlite')
        self.assertEqual(config.sqlite_file, 'price_monitoring.db')
        self.assertEqual(config.host, 'localhost')
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.database, 'price_monitoring')
        self.assertEqual(config.username, '')
        self.assertEqual(config.password, '')
        self.assertEqual(config.pool_size, 5)
        self.assertEqual(config.max_overflow, 10)
        self.assertEqual(config.pool_timeout, 30)


class TestSettings(unittest.TestCase):
    """Тесты для основного класса Settings."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir)
        
    def tearDown(self):
        """Очистка тестового окружения."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_default_initialization(self):
        """Тест инициализации с параметрами по умолчанию."""
        settings = Settings(config_dir=str(self.config_dir))
        
        self.assertIsInstance(settings.google_sheets, GoogleSheetsConfig)
        self.assertIsInstance(settings.monitoring, MonitoringConfig)
        self.assertIsInstance(settings.notifications, NotificationConfig)
        self.assertIsInstance(settings.logging, LoggingConfig)
        self.assertIsInstance(settings.database, DatabaseConfig)
        
    def test_get_credentials_path(self):
        """Тест получения пути к файлу credentials."""
        settings = Settings(config_dir=str(self.config_dir))
        path = settings.get_credentials_path()
        
        expected_path = self.config_dir / 'credentials.json'
        self.assertEqual(path, expected_path)
        
    def test_get_token_path(self):
        """Тест получения пути к файлу token."""
        settings = Settings(config_dir=str(self.config_dir))
        path = settings.get_token_path()
        
        expected_path = self.config_dir / 'token.pickle'
        self.assertEqual(path, expected_path)


class TestGetSettings(unittest.TestCase):
    """Тесты для функции get_settings."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        # Сбрасываем глобальный экземпляр
        from config.settings import reset_settings
        reset_settings()
        
    def tearDown(self):
        """Очистка после тестов."""
        from config.settings import reset_settings
        reset_settings()
        
    def test_get_settings_singleton(self):
        """Тест что get_settings возвращает один и тот же экземпляр."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        self.assertIs(settings1, settings2)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    unittest.main(verbosity=2)