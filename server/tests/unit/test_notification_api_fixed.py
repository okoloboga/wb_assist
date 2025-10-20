"""
Unit tests for notification API endpoints (fixed version)
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException

from app.features.notifications.api.settings import router as settings_router
from app.features.notifications.api.test import router as test_router
from app.features.notifications.schemas import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    TestNotificationData,
    TestNotificationResponse
)


@pytest.fixture
def app():
    """Create FastAPI app for testing"""
    app = FastAPI()
    app.include_router(settings_router, prefix="/notifications")
    app.include_router(test_router, prefix="/notifications")
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    return Mock()


@pytest.fixture
def mock_user():
    """Mock user"""
    user = Mock()
    user.id = 1
    user.telegram_id = 12345
    user.bot_webhook_url = "http://test.com/webhook"
    return user


@pytest.fixture
def mock_notification_settings():
    """Mock notification settings"""
    settings = Mock()
    settings.user_id = 1
    settings.notifications_enabled = True
    settings.new_orders_enabled = True
    settings.order_buyouts_enabled = True
    settings.order_cancellations_enabled = False
    settings.order_returns_enabled = False
    settings.negative_reviews_enabled = True
    settings.critical_stocks_enabled = True
    settings.grouping_enabled = True
    settings.max_group_size = 5
    settings.group_timeout = 60
    return settings


class TestSettingsAPI:
    """Test Settings API endpoints"""

    def test_get_settings_success(self, client, mock_db, mock_user, mock_notification_settings):
        """Test successful retrieval of notification settings"""
        with patch('app.features.notifications.api.settings.UserCRUD') as mock_user_crud_class, \
             patch('app.features.notifications.api.settings.NotificationSettingsCRUD') as mock_crud_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            mock_crud = Mock()
            mock_crud.get_user_settings.return_value = mock_notification_settings
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/notifications/settings?telegram_id=12345")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["user_id"] == 1
            assert data["data"]["notifications_enabled"] is True
            assert data["data"]["new_orders_enabled"] is True

    def test_get_settings_user_not_found(self, client, mock_db):
        """Test retrieval when user not found"""
        with patch('app.features.notifications.api.settings.UserCRUD') as mock_user_crud_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = None
            mock_user_crud_class.return_value = mock_user_crud
            
            response = client.get("/notifications/settings?telegram_id=12345")
            
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert "User not found" in data["message"]

    def test_get_settings_not_found(self, client, mock_db, mock_user):
        """Test retrieval when settings not found"""
        with patch('app.features.notifications.api.settings.UserCRUD') as mock_user_crud_class, \
             patch('app.features.notifications.api.settings.NotificationSettingsCRUD') as mock_crud_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            mock_crud = Mock()
            mock_crud.get_user_settings.return_value = None
            mock_crud_class.return_value = mock_crud
            
            response = client.get("/notifications/settings?telegram_id=12345")
            
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert "Settings not found" in data["message"]

    def test_update_settings_success(self, client, mock_db, mock_user, mock_notification_settings):
        """Test successful update of notification settings"""
        update_data = {
            "new_orders_enabled": False,
            "negative_reviews_enabled": False
        }
        
        with patch('app.features.notifications.api.settings.UserCRUD') as mock_user_crud_class, \
             patch('app.features.notifications.api.settings.NotificationSettingsCRUD') as mock_crud_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            mock_crud = Mock()
            mock_crud.get_user_settings.return_value = mock_notification_settings
            mock_crud.update_settings.return_value = mock_notification_settings
            mock_crud_class.return_value = mock_crud
            
            response = client.post("/notifications/settings?telegram_id=12345", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Settings updated successfully" in data["message"]

    def test_update_settings_validation_error(self, client, mock_db, mock_user):
        """Test update with validation error"""
        invalid_data = {
            "max_group_size": 100,  # Invalid: should be <= 50
            "group_timeout": 500    # Invalid: should be <= 300
        }
        
        with patch('app.features.notifications.api.settings.UserCRUD') as mock_user_crud_class:
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            response = client.post("/notifications/settings?telegram_id=12345", json=invalid_data)
            
            assert response.status_code == 422  # Validation error

    def test_update_settings_user_not_found(self, client, mock_db):
        """Test update when user not found"""
        update_data = {"new_orders_enabled": False}
        
        with patch('app.features.notifications.api.settings.UserCRUD') as mock_user_crud_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = None
            mock_user_crud_class.return_value = mock_user_crud
            
            response = client.post("/notifications/settings?telegram_id=12345", json=update_data)
            
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert "User not found" in data["message"]


class TestTestAPI:
    """Test Test API endpoints"""

    def test_send_test_notification_success(self, client, mock_db, mock_user):
        """Test successful sending of test notification"""
        test_data = {
            "notification_type": "new_order",
            "test_data": {
                "order_id": "12345",
                "amount": 1500,
                "product_name": "Test Product"
            }
        }
        
        with patch('app.features.notifications.api.test.UserCRUD') as mock_user_crud_class, \
             patch('app.features.notifications.api.test.NotificationService') as mock_service_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            mock_service = Mock()
            mock_service.send_test_notification.return_value = {
                "success": True,
                "message": "Test notification sent successfully"
            }
            mock_service_class.return_value = mock_service
            
            response = client.post("/notifications/test?telegram_id=12345", json=test_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["notification_sent"] is True
            assert "Test notification sent successfully" in data["message"]

    def test_send_test_notification_invalid_type(self, client, mock_db, mock_user):
        """Test sending test notification with invalid type"""
        test_data = {
            "notification_type": "invalid_type",
            "test_data": {}
        }
        
        with patch('app.features.notifications.api.test.UserCRUD') as mock_user_crud_class:
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            response = client.post("/notifications/test?telegram_id=12345", json=test_data)
            
            assert response.status_code == 422  # Validation error

    def test_send_test_notification_user_not_found(self, client, mock_db):
        """Test sending test notification when user not found"""
        test_data = {
            "notification_type": "new_order",
            "test_data": {}
        }
        
        with patch('app.features.notifications.api.test.UserCRUD') as mock_user_crud_class:
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = None
            mock_user_crud_class.return_value = mock_user_crud
            
            response = client.post("/notifications/test?telegram_id=12345", json=test_data)
            
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert "User not found" in data["message"]

    def test_send_test_notification_no_webhook(self, client, mock_db, mock_user):
        """Test sending test notification when user has no webhook URL"""
        mock_user.bot_webhook_url = None
        
        test_data = {
            "notification_type": "new_order",
            "test_data": {}
        }
        
        with patch('app.features.notifications.api.test.UserCRUD') as mock_user_crud_class:
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            response = client.post("/notifications/test?telegram_id=12345", json=test_data)
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "Bot webhook URL not found" in data["message"]

    def test_send_test_notification_service_error(self, client, mock_db, mock_user):
        """Test sending test notification when service fails"""
        test_data = {
            "notification_type": "new_order",
            "test_data": {}
        }
        
        with patch('app.features.notifications.api.test.UserCRUD') as mock_user_crud_class, \
             patch('app.features.notifications.api.test.NotificationService') as mock_service_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            mock_service = Mock()
            mock_service.send_test_notification.side_effect = Exception("Service error")
            mock_service_class.return_value = mock_service
            
            response = client.post("/notifications/test?telegram_id=12345", json=test_data)
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert "Internal server error" in data["message"]

    def test_send_test_notification_negative_review(self, client, mock_db, mock_user):
        """Test sending negative review test notification"""
        test_data = {
            "notification_type": "negative_review",
            "test_data": {
                "review_id": "67890",
                "rating": 2,
                "product_name": "Test Product",
                "comment": "Bad quality"
            }
        }
        
        with patch('app.features.notifications.api.test.UserCRUD') as mock_user_crud_class, \
             patch('app.features.notifications.api.test.NotificationService') as mock_service_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            mock_service = Mock()
            mock_service.send_test_notification.return_value = {
                "success": True,
                "message": "Test notification sent successfully"
            }
            mock_service_class.return_value = mock_service
            
            response = client.post("/notifications/test?telegram_id=12345", json=test_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["notification_sent"] is True

    def test_send_test_notification_critical_stocks(self, client, mock_db, mock_user):
        """Test sending critical stocks test notification"""
        test_data = {
            "notification_type": "critical_stocks",
            "test_data": {
                "products": [
                    {"nm_id": "12345", "name": "Product 1", "stock": 2},
                    {"nm_id": "67890", "name": "Product 2", "stock": 1}
                ]
            }
        }
        
        with patch('app.features.notifications.api.test.UserCRUD') as mock_user_crud_class, \
             patch('app.features.notifications.api.test.NotificationService') as mock_service_class:
            
            mock_user_crud = Mock()
            mock_user_crud.get_user_by_telegram_id.return_value = mock_user
            mock_user_crud_class.return_value = mock_user_crud
            
            mock_service = Mock()
            mock_service.send_test_notification.return_value = {
                "success": True,
                "message": "Test notification sent successfully"
            }
            mock_service_class.return_value = mock_service
            
            response = client.post("/notifications/test?telegram_id=12345", json=test_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["notification_sent"] is True
