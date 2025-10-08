"""
Тесты для AuthHelper - помощника OAuth 2.0 аутентификации.

Включает тесты аутентификации, работы с токенами, и интеграции с Google API.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import os
from pathlib import Path
import tempfile
import json
import pickle
from datetime import datetime, timedelta

# Добавляем путь к модулю в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.auth_helper import AuthHelper


class TestAuthHelper(unittest.TestCase):
    """Тесты для класса AuthHelper."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.auth_helper = AuthHelper(config_dir=str(self.config_dir))
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Тест инициализации AuthHelper."""
        self.assertEqual(self.auth_helper.config_dir, self.config_dir)
        self.assertEqual(self.auth_helper.credentials_file, self.config_dir / 'credentials.json')
        self.assertEqual(self.auth_helper.token_file, self.config_dir / 'token.pickle')
        self.assertIsNone(self.auth_helper._credentials)
        self.assertFalse(self.auth_helper.is_authenticated)
    
    def test_credentials_property_none(self):
        """Тест свойства credentials когда оно None."""
        self.assertIsNone(self.auth_helper.credentials)
        self.assertFalse(self.auth_helper.is_authenticated)
    
    def test_credentials_property_valid(self):
        """Тест свойства credentials когда оно валидно."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        self.auth_helper._credentials = mock_credentials
        
        self.assertEqual(self.auth_helper.credentials, mock_credentials)
        self.assertTrue(self.auth_helper.is_authenticated)
    
    def test_credentials_property_invalid(self):
        """Тест свойства credentials когда оно невалидно."""
        mock_credentials = Mock()
        mock_credentials.valid = False
        self.auth_helper._credentials = mock_credentials
        
        self.assertEqual(self.auth_helper.credentials, mock_credentials)
        self.assertFalse(self.auth_helper.is_authenticated)
    
    def test_create_credentials_template(self):
        """Тест создания шаблона credentials."""
        template = AuthHelper.create_credentials_template()
        
        self.assertIsInstance(template, str)
        template_data = json.loads(template)
        
        # Проверяем структуру
        self.assertIn('installed', template_data)
        installed = template_data['installed']
        
        self.assertIn('client_id', installed)
        self.assertIn('client_secret', installed)
        self.assertIn('project_id', installed)
        self.assertIn('auth_uri', installed)
        self.assertIn('token_uri', installed)
        self.assertIn('redirect_uris', installed)
        
        # Проверяем значения по умолчанию
        self.assertEqual(installed['auth_uri'], 'https://accounts.google.com/o/oauth2/auth')
        self.assertEqual(installed['token_uri'], 'https://oauth2.googleapis.com/token')
        self.assertEqual(installed['redirect_uris'], ['http://localhost'])
    
    def test_setup_credentials_file(self):
        """Тест создания файла credentials."""
        client_id = 'test_client_id_123'
        client_secret = 'test_client_secret_456'
        project_id = 'test_project_789'
        
        self.auth_helper.setup_credentials_file(client_id, client_secret, project_id)
        
        # Проверяем, что файл создан
        self.assertTrue(self.auth_helper.credentials_file.exists())
        
        # Проверяем содержимое файла
        with open(self.auth_helper.credentials_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIn('installed', data)
        installed = data['installed']
        
        self.assertEqual(installed['client_id'], client_id)
        self.assertEqual(installed['client_secret'], client_secret)
        self.assertEqual(installed['project_id'], project_id)
    
    def test_setup_credentials_file_overwrites_existing(self):
        """Тест перезаписи существующего файла credentials."""
        # Создаем первый файл
        self.auth_helper.setup_credentials_file('old_id', 'old_secret', 'old_project')
        
        # Создаем новый файл
        new_client_id = 'new_client_id'
        new_client_secret = 'new_client_secret'
        new_project_id = 'new_project'
        
        self.auth_helper.setup_credentials_file(new_client_id, new_client_secret, new_project_id)
        
        # Проверяем, что файл обновлен
        with open(self.auth_helper.credentials_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        installed = data['installed']
        self.assertEqual(installed['client_id'], new_client_id)
        self.assertEqual(installed['client_secret'], new_client_secret)
        self.assertEqual(installed['project_id'], new_project_id)
    
    @patch('utils.auth_helper.pickle.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_existing_token_success(self, mock_file, mock_pickle_load):
        """Тест успешной загрузки существующего токена."""
        # Создаем мок токена
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_pickle_load.return_value = mock_credentials
        
        # Мокаем существование файла
        with patch.object(Path, 'exists', return_value=True):
            self.auth_helper._load_existing_token()
        
        self.assertEqual(self.auth_helper._credentials, mock_credentials)
        mock_file.assert_called_once_with(self.auth_helper.token_file, 'rb')
        mock_pickle_load.assert_called_once()
    
    @patch('utils.auth_helper.pickle.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_existing_token_file_not_exists(self, mock_file, mock_pickle_load):
        """Тест загрузки токена когда файл не существует."""
        with patch.object(Path, 'exists', return_value=False):
            self.auth_helper._load_existing_token()
        
        self.assertIsNone(self.auth_helper._credentials)
        mock_file.assert_not_called()
        mock_pickle_load.assert_not_called()
    
    @patch('utils.auth_helper.pickle.load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.auth_helper.logger')
    def test_load_existing_token_exception(self, mock_logger, mock_file, mock_pickle_load):
        """Тест загрузки токена с исключением."""
        mock_pickle_load.side_effect = Exception("Pickle error")
        
        with patch.object(Path, 'exists', return_value=True):
            self.auth_helper._load_existing_token()
        
        self.assertIsNone(self.auth_helper._credentials)
        mock_logger.warning.assert_called()
    
    @patch('utils.auth_helper.pickle.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_token_success(self, mock_file, mock_pickle_dump):
        """Тест успешного сохранения токена."""
        mock_credentials = Mock()
        self.auth_helper._credentials = mock_credentials
        
        self.auth_helper._save_token()
        
        mock_file.assert_called_once_with(self.auth_helper.token_file, 'wb')
        mock_pickle_dump.assert_called_once_with(mock_credentials, mock_file.return_value)
    
    @patch('utils.auth_helper.pickle.dump')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.auth_helper.logger')
    def test_save_token_exception(self, mock_logger, mock_file, mock_pickle_dump):
        """Тест сохранения токена с исключением."""
        mock_credentials = Mock()
        self.auth_helper._credentials = mock_credentials
        mock_pickle_dump.side_effect = Exception("Save error")
        
        self.auth_helper._save_token()
        
        mock_logger.error.assert_called()
    
    @patch('utils.auth_helper.InstalledAppFlow')
    def test_authenticate_no_credentials_file(self, mock_flow):
        """Тест аутентификации без файла credentials."""
        result = self.auth_helper.authenticate()
        
        self.assertFalse(result)
        mock_flow.assert_not_called()
    
    @patch('utils.auth_helper.InstalledAppFlow')
    def test_authenticate_success_new_token(self, mock_flow):
        """Тест успешной аутентификации с новым токеном."""
        # Создаем файл credentials
        self.auth_helper.setup_credentials_file('test_id', 'test_secret', 'test_project')
        
        # Настраиваем мок flow
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_flow_instance = Mock()
        mock_flow_instance.run_local_server.return_value = mock_credentials
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        
        # Мокаем методы сохранения и загрузки
        with patch.object(self.auth_helper, '_load_existing_token', return_value=None):
            with patch.object(self.auth_helper, '_save_token') as mock_save:
                result = self.auth_helper.authenticate()
        
        self.assertTrue(result)
        self.assertEqual(self.auth_helper._credentials, mock_credentials)
        mock_save.assert_called_once_with(mock_credentials)
    
    @patch('utils.auth_helper.InstalledAppFlow')
    def test_authenticate_success_existing_valid_token(self, mock_flow):
        """Тест успешной аутентификации с существующим валидным токеном."""
        # Создаем файл credentials
        self.auth_helper.setup_credentials_file('test_id', 'test_secret', 'test_project')
        
        # Настраиваем мок существующих credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        
        with patch.object(self.auth_helper, '_load_existing_token', return_value=mock_credentials):
            result = self.auth_helper.authenticate()
        
        self.assertTrue(result)
        self.assertEqual(self.auth_helper._credentials, mock_credentials)
        mock_flow.assert_not_called()  # Не должен создавать новый flow
    
    @patch('utils.auth_helper.InstalledAppFlow')
    @patch('utils.auth_helper.Request')
    def test_authenticate_refresh_expired_token(self, mock_request, mock_flow):
        """Тест аутентификации с обновлением истекшего токена."""
        # Создаем файл credentials
        self.auth_helper.setup_credentials_file('test_id', 'test_secret', 'test_project')
        
        # Настраиваем мок истекших credentials
        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = 'refresh_token'
        
        with patch.object(self.auth_helper, '_load_existing_token', return_value=mock_credentials):
            with patch.object(self.auth_helper, '_save_token') as mock_save:
                result = self.auth_helper.authenticate()
        
        self.assertTrue(result)
        mock_credentials.refresh.assert_called_once()
        mock_save.assert_called_once_with(mock_credentials)
    
    @patch('utils.auth_helper.InstalledAppFlow')
    def test_authenticate_force_reauth(self, mock_flow):
        """Тест принудительной повторной аутентификации."""
        # Создаем файл credentials
        self.auth_helper.setup_credentials_file('test_id', 'test_secret', 'test_project')
        
        # Настраиваем мок flow
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_flow_instance = Mock()
        mock_flow_instance.run_local_server.return_value = mock_credentials
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        
        # Настраиваем существующие credentials (должны быть проигнорированы)
        existing_credentials = Mock()
        existing_credentials.valid = True
        
        with patch.object(self.auth_helper, '_load_existing_token', return_value=existing_credentials):
            with patch.object(self.auth_helper, '_save_token') as mock_save:
                result = self.auth_helper.authenticate(force_reauth=True)
        
        self.assertTrue(result)
        self.assertEqual(self.auth_helper._credentials, mock_credentials)
        mock_save.assert_called_once_with(mock_credentials)
        mock_flow_instance.run_local_server.assert_called_once()
    
    @patch('utils.auth_helper.build')
    def test_get_sheets_service_success(self, mock_build):
        """Тест получения сервиса Google Sheets."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        self.auth_helper._credentials = mock_credentials
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = self.auth_helper.get_sheets_service()
        
        self.assertEqual(result, mock_service)
        mock_build.assert_called_once_with('sheets', 'v4', credentials=mock_credentials)
    
    def test_get_sheets_service_not_authenticated(self):
        """Тест получения сервиса без аутентификации."""
        with self.assertRaises(ValueError) as context:
            self.auth_helper.get_sheets_service()
        
        self.assertIn("не аутентифицирован", str(context.exception))
    
    @patch('utils.auth_helper.build')
    def test_get_drive_service_success(self, mock_build):
        """Тест получения сервиса Google Drive."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        self.auth_helper._credentials = mock_credentials
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = self.auth_helper.get_drive_service()
        
        self.assertEqual(result, mock_service)
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_credentials)
    
    @patch('utils.auth_helper.build')
    def test_get_people_service_success(self, mock_build):
        """Тест получения сервиса Google People."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        self.auth_helper._credentials = mock_credentials
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = self.auth_helper.get_people_service()
        
        self.assertEqual(result, mock_service)
        mock_build.assert_called_once_with('people', 'v1', credentials=mock_credentials)
    
    def test_revoke_credentials_not_authenticated(self):
        """Тест отзыва учетных данных без аутентификации."""
        result = self.auth_helper.revoke_credentials()
        
        self.assertFalse(result)
    
    @patch('google.auth.transport.requests.Request')
    def test_revoke_credentials_success(self, mock_request):
        """Тест успешного отзыва учетных данных."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = 'test_token'
        mock_credentials.revoke = Mock()
        self.auth_helper._credentials = mock_credentials
        
        with patch.object(Path, 'unlink') as mock_unlink:
            with patch.object(self.auth_helper.token_file, 'exists', return_value=True):
                result = self.auth_helper.revoke_credentials()
        
        self.assertTrue(result)
        self.assertIsNone(self.auth_helper._credentials)
        mock_credentials.revoke.assert_called_once()
        mock_unlink.assert_called_once()
    
    @patch('google.auth.transport.requests.Request')
    def test_revoke_credentials_failure(self, mock_request):
        """Тест неудачного отзыва учетных данных."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = 'test_token'
        mock_credentials.revoke = Mock(side_effect=Exception("Revoke error"))
        self.auth_helper._credentials = mock_credentials
        
        result = self.auth_helper.revoke_credentials()
        
        self.assertFalse(result)
        # Credentials должны быть очищены даже при ошибке
        self.assertIsNone(self.auth_helper._credentials)
    
    def test_test_connection_not_authenticated(self):
        """Тест проверки соединения без аутентификации."""
        result = self.auth_helper.test_connection()
        
        self.assertFalse(result)
    
    @patch('utils.auth_helper.build')
    def test_test_connection_success(self, mock_build):
        """Тест успешной проверки соединения."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        self.auth_helper._credentials = mock_credentials
        
        mock_service = Mock()
        mock_service.spreadsheets().create().execute.return_value = {
            'spreadsheetId': 'test_id'
        }
        mock_build.return_value = mock_service
        
        result = self.auth_helper.test_connection()
        
        self.assertTrue(result)
    
    @patch('utils.auth_helper.build')
    def test_test_connection_failure(self, mock_build):
        """Тест неудачной проверки соединения."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        self.auth_helper._credentials = mock_credentials
        
        mock_service = Mock()
        mock_service.spreadsheets().create().execute.side_effect = Exception("API Error")
        mock_build.return_value = mock_service
        
        result = self.auth_helper.test_connection()
        
        self.assertFalse(result)


class TestAuthHelperIntegration(unittest.TestCase):
    """Интеграционные тесты для AuthHelper."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_full_credentials_workflow(self):
        """Тест полного рабочего процесса с учетными данными."""
        auth_helper = AuthHelper(config_dir=str(self.config_dir))
        
        # 1. Создаем файл credentials
        client_id = 'test_client_id'
        client_secret = 'test_client_secret'
        project_id = 'test_project'
        
        auth_helper.setup_credentials_file(client_id, client_secret, project_id)
        
        # 2. Проверяем, что файл создан правильно
        self.assertTrue(auth_helper.credentials_file.exists())
        
        with open(auth_helper.credentials_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['installed']['client_id'], client_id)
        self.assertEqual(data['installed']['client_secret'], client_secret)
        self.assertEqual(data['installed']['project_id'], project_id)
        
        # 3. Проверяем, что изначально не аутентифицирован
        self.assertFalse(auth_helper.is_authenticated)
        self.assertIsNone(auth_helper.credentials)
    
    def test_token_persistence(self):
        """Тест сохранения и загрузки токена."""
        auth_helper = AuthHelper(config_dir=str(self.config_dir))
        
        # Создаем мок credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = 'test_token'
        
        # Устанавливаем credentials и сохраняем токен
        auth_helper._credentials = mock_credentials
        auth_helper._save_token()
        
        # Проверяем, что файл токена создан
        self.assertTrue(auth_helper.token_file.exists())
        
        # Создаем новый экземпляр и загружаем токен
        new_auth_helper = AuthHelper(config_dir=str(self.config_dir))
        new_auth_helper._load_existing_token()
        
        # Проверяем, что токен загружен правильно
        self.assertIsNotNone(new_auth_helper._credentials)
        self.assertEqual(new_auth_helper._credentials.token, 'test_token')


if __name__ == '__main__':
    # Настраиваем логирование для тестов
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Запускаем тесты
    unittest.main(verbosity=2)