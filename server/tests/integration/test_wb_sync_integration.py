"""
Интеграционные тесты для интеграции Event Detection с WBSyncService
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.features.wb_api.sync_service import WBSyncService
from app.features.wb_api.models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview
from app.features.user.models import User
from app.features.notifications.event_detector import EventDetector
from app.features.notifications.status_monitor import StatusChangeMonitor
from app.features.notifications.crud import NotificationSettingsCRUD


class TestWBSyncIntegration:
    """Интеграционные тесты для WBSyncService с Event Detection"""
    
    def test_sync_orders_with_event_detection(self, db_session: Session):
        """Тест синхронизации заказов с обнаружением событий"""
        # Создаем пользователя и кабинет
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        cabinet = WBCabinet(
            user_id=user.id,
            name="Test Cabinet",
            api_key="test_key"
        )
        db_session.add(cabinet)
        db_session.commit()
        db_session.refresh(cabinet)
        
        # Создаем настройки уведомлений
        settings_crud = NotificationSettingsCRUD()
        settings = settings_crud.create_default_settings(db_session, user.id)
        
        # Мокаем WBAPIClient
        mock_client = AsyncMock()
        mock_client.get_orders.return_value = [
            {
                "gNumber": 1,
                "nmId": 1001,
                "status": "active",
                "totalPrice": 1000,
                "brand": "Test Brand",
                "productName": "Test Product"
            },
            {
                "gNumber": 2,
                "nmId": 1002,
                "status": "buyout",
                "totalPrice": 1500,
                "brand": "Test Brand 2",
                "productName": "Test Product 2"
            }
        ]
        mock_client.get_commissions.return_value = []
        
        # Создаем WBSyncService
        sync_service = WBSyncService(db_session)
        
        # Мокаем Event Detector и Status Monitor
        event_detector = EventDetector()
        status_monitor = StatusChangeMonitor()
        
        # Предыдущие заказы (для сравнения)
        previous_orders = [
            {"order_id": 1, "status": "active", "amount": 1000, "product_name": "Test Product"},
            {"order_id": 2, "status": "active", "amount": 1500, "product_name": "Test Product 2"}
        ]
        
        # Текущие заказы (после синхронизации)
        current_orders = [
            {"order_id": 1, "status": "active", "amount": 1000, "product_name": "Test Product"},
            {"order_id": 2, "status": "buyout", "amount": 1500, "product_name": "Test Product 2"},  # статус изменился
            {"order_id": 3, "status": "active", "amount": 2000, "product_name": "Test Product 3"}   # новый заказ
        ]
        
        # Обнаруживаем события
        new_order_events = event_detector.detect_new_orders(user.id, current_orders, previous_orders)
        status_change_events = event_detector.detect_status_changes(user.id, current_orders, previous_orders)
        
        # Проверяем обнаруженные события
        assert len(new_order_events) == 1
        assert new_order_events[0]["type"] == "new_order"
        assert new_order_events[0]["order_id"] == 3
        
        assert len(status_change_events) == 1
        assert status_change_events[0]["type"] == "order_buyout"
        assert status_change_events[0]["order_id"] == 2
        assert status_change_events[0]["previous_status"] == "active"
        assert status_change_events[0]["current_status"] == "buyout"
    
    def test_sync_reviews_with_negative_detection(self, db_session: Session):
        """Тест синхронизации отзывов с обнаружением негативных"""
        # Создаем пользователя и кабинет
        user = User(
            telegram_id=987654321,
            username="test_user_2",
            first_name="Test 2",
            last_name="User 2"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки уведомлений
        settings_crud = NotificationSettingsCRUD()
        settings = settings_crud.create_default_settings(db_session, user.id)
        
        event_detector = EventDetector()
        
        # Предыдущие отзывы
        previous_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!", "product_name": "Товар 1"}
        ]
        
        # Текущие отзывы (добавился негативный)
        current_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!", "product_name": "Товар 1"},
            {"id": 2, "rating": 2, "text": "Плохо", "product_name": "Товар 2"},  # негативный отзыв
            {"id": 3, "rating": 1, "text": "Ужасно", "product_name": "Товар 3"}  # негативный отзыв
        ]
        
        # Обнаруживаем негативные отзывы
        negative_review_events = event_detector.detect_negative_reviews(user.id, current_reviews, previous_reviews)
        
        # Проверяем обнаруженные события
        assert len(negative_review_events) == 2
        assert all(event["type"] == "negative_review" for event in negative_review_events)
        assert any(event["rating"] == 2 for event in negative_review_events)
        assert any(event["rating"] == 1 for event in negative_review_events)
    
    def test_sync_stocks_with_critical_detection(self, db_session: Session):
        """Тест синхронизации остатков с обнаружением критичных"""
        # Создаем пользователя и кабинет
        user = User(
            telegram_id=555666777,
            username="test_user_3",
            first_name="Test 3",
            last_name="User 3"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки уведомлений
        settings_crud = NotificationSettingsCRUD()
        settings = settings_crud.create_default_settings(db_session, user.id)
        
        event_detector = EventDetector()
        
        # Предыдущие остатки
        previous_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 10, "M": 5, "L": 3}},
            {"nm_id": 2, "name": "Товар 2", "stocks": {"S": 8, "M": 6, "L": 4}}
        ]
        
        # Текущие остатки (стали критичными)
        current_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 1, "M": 0, "L": 0}},  # критично
            {"nm_id": 2, "name": "Товар 2", "stocks": {"S": 2, "M": 1, "L": 0}}   # критично
        ]
        
        # Обнаруживаем критичные остатки
        critical_stocks_events = event_detector.detect_critical_stocks(user.id, current_stocks, previous_stocks)
        
        # Проверяем обнаруженные события
        assert len(critical_stocks_events) == 2
        assert all(event["type"] == "critical_stocks" for event in critical_stocks_events)
        assert any(event["nm_id"] == 1 for event in critical_stocks_events)
        assert any(event["nm_id"] == 2 for event in critical_stocks_events)
    
    def test_status_monitor_integration_with_sync(self, db_session: Session):
        """Тест интеграции Status Change Monitor с синхронизацией"""
        # Создаем пользователя
        user = User(
            telegram_id=111222333,
            username="test_user_4",
            first_name="Test 4",
            last_name="User 4"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        status_monitor = StatusChangeMonitor()
        
        # Мокаем Redis
        mock_redis = Mock()
        previous_state = {"1": "active", "2": "active"}
        mock_redis.get.return_value = previous_state
        
        # Текущие заказы с изменениями
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000, "product_name": "Товар 1"},
            {"order_id": 2, "status": "cancelled", "amount": 1500, "product_name": "Товар 2"},
            {"order_id": 3, "status": "active", "amount": 2000, "product_name": "Товар 3"}
        ]
        
        # Отслеживаем изменения
        changes = status_monitor.track_order_changes(user.id, current_orders, mock_redis)
        
        # Проверяем обнаруженные изменения
        assert len(changes) == 3
        
        # Проверяем конкретные изменения
        buyout_change = next(c for c in changes if c["order_id"] == 1)
        assert buyout_change["previous_status"] == "active"
        assert buyout_change["current_status"] == "buyout"
        
        cancellation_change = next(c for c in changes if c["order_id"] == 2)
        assert cancellation_change["previous_status"] == "active"
        assert cancellation_change["current_status"] == "cancelled"
        
        new_order_change = next(c for c in changes if c["order_id"] == 3)
        assert new_order_change["previous_status"] is None
        assert new_order_change["current_status"] == "active"
    
    def test_user_settings_filtering(self, db_session: Session):
        """Тест фильтрации событий на основе настроек пользователя"""
        # Создаем пользователя
        user = User(
            telegram_id=444555666,
            username="test_user_5",
            first_name="Test 5",
            last_name="User 5"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки с отключенными уведомлениями
        settings_crud = NotificationSettingsCRUD()
        settings = settings_crud.create_default_settings(db_session, user.id)
        settings_crud.update_settings(db_session, user.id, {
            "new_orders_enabled": False,
            "negative_reviews_enabled": False,
            "critical_stocks_enabled": False
        })
        
        # Получаем обновленные настройки
        updated_settings = settings_crud.get_user_settings(db_session, user.id)
        
        # Проверяем, что настройки применились
        assert updated_settings.new_orders_enabled is False
        assert updated_settings.negative_reviews_enabled is False
        assert updated_settings.critical_stocks_enabled is False
        
        # В реальной системе здесь должна быть логика фильтрации событий
        # на основе этих настроек перед отправкой уведомлений
