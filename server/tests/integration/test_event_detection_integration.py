"""
Интеграционные тесты для Event Detection системы уведомлений S3
"""

import pytest
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock

from app.features.notifications.event_detector import EventDetector
from app.features.notifications.status_monitor import StatusChangeMonitor
from app.features.notifications.crud import (
    NotificationSettingsCRUD,
    NotificationHistoryCRUD,
    OrderStatusHistoryCRUD
)


class TestEventDetectionIntegration:
    """Интеграционные тесты для Event Detection"""
    
    def test_full_event_detection_flow(self, db_session):
        """Тест полного потока обнаружения событий"""
        # Инициализируем компоненты
        event_detector = EventDetector()
        status_monitor = StatusChangeMonitor()
        settings_crud = NotificationSettingsCRUD()
        history_crud = NotificationHistoryCRUD()
        order_crud = OrderStatusHistoryCRUD()
        
        user_id = 123456789
        
        # Создаем настройки пользователя
        settings = settings_crud.create_default_settings(db_session, user_id)
        assert settings is not None
        
        # Предыдущие данные (состояние до синхронизации)
        previous_orders = [
            {"order_id": 1, "status": "active", "amount": 1000, "product_name": "Товар 1"},
            {"order_id": 2, "status": "active", "amount": 1500, "product_name": "Товар 2"}
        ]
        previous_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!", "product_name": "Товар 1"}
        ]
        previous_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 10, "M": 5, "L": 3}}
        ]
        
        # Текущие данные (состояние после синхронизации)
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000, "product_name": "Товар 1"},  # статус изменился
            {"order_id": 2, "status": "active", "amount": 1500, "product_name": "Товар 2"},
            {"order_id": 3, "status": "active", "amount": 2000, "product_name": "Товар 3"}   # новый заказ
        ]
        current_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!", "product_name": "Товар 1"},
            {"id": 2, "rating": 2, "text": "Плохо", "product_name": "Товар 2"}  # негативный отзыв
        ]
        current_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 1, "M": 0, "L": 0}}  # критичные остатки
        ]
        
        # Мокаем Redis для Status Change Monitor
        mock_redis = Mock()
        mock_redis.get.return_value = None  # Нет предыдущего состояния
        
        # 1. Обнаруживаем новые заказы
        new_order_events = event_detector.detect_new_orders(user_id, current_orders, previous_orders)
        assert len(new_order_events) == 1
        assert new_order_events[0]["type"] == "new_order"
        assert new_order_events[0]["order_id"] == 3
        
        # 2. Обнаруживаем изменения статуса
        status_change_events = event_detector.detect_status_changes(user_id, current_orders, previous_orders)
        assert len(status_change_events) == 1
        assert status_change_events[0]["type"] == "order_buyout"
        assert status_change_events[0]["order_id"] == 1
        
        # 3. Обнаруживаем негативные отзывы
        negative_review_events = event_detector.detect_negative_reviews(user_id, current_reviews, previous_reviews)
        assert len(negative_review_events) == 1
        assert negative_review_events[0]["type"] == "negative_review"
        assert negative_review_events[0]["rating"] == 2
        
        # 4. Обнаруживаем критичные остатки
        critical_stocks_events = event_detector.detect_critical_stocks(user_id, current_stocks, previous_stocks)
        assert len(critical_stocks_events) == 1
        assert critical_stocks_events[0]["type"] == "critical_stocks"
        assert critical_stocks_events[0]["nm_id"] == 1
        
        # 5. Отслеживаем изменения через Status Change Monitor
        order_changes = status_monitor.track_order_changes(user_id, current_orders, mock_redis)
        assert len(order_changes) == 3  # Все заказы (включая новые)
        
        # 6. Записываем изменения статуса в БД
        for change in order_changes:
            if change.get("previous_status") != change.get("current_status"):
                order_crud.track_status_change(
                    db_session,
                    user_id,
                    change["order_id"],
                    change.get("previous_status"),
                    change.get("current_status")
                )
        
        # 7. Создаем записи в истории уведомлений
        all_events = new_order_events + status_change_events + negative_review_events + critical_stocks_events
        
        for event in all_events:
            notification_data = {
                "id": f"notif_{event['type']}_{event.get('order_id', event.get('review_id', event.get('nm_id', 'unknown')))}",
                "user_id": user_id,
                "notification_type": event["type"],
                "priority": "HIGH",
                "title": f"Уведомление: {event['type']}",
                "content": f"Событие обнаружено: {event}",
                "sent_at": datetime.now(timezone.utc)
            }
            history_crud.create_notification(db_session, notification_data)
        
        # 8. Проверяем, что все записи созданы
        history = history_crud.get_user_history(db_session, user_id, {})
        assert len(history) == 4  # 4 типа событий
        
        # Проверяем типы уведомлений
        notification_types = [n.notification_type for n in history]
        assert "new_order" in notification_types
        assert "order_buyout" in notification_types
        assert "negative_review" in notification_types
        assert "critical_stocks" in notification_types
    
    def test_event_detection_with_user_settings(self, db_session):
        """Тест обнаружения событий с учетом настроек пользователя"""
        # Инициализируем компоненты
        event_detector = EventDetector()
        settings_crud = NotificationSettingsCRUD()
        
        user_id = 987654321
        
        # Создаем настройки с отключенными уведомлениями о новых заказах
        settings = settings_crud.create_default_settings(db_session, user_id)
        settings_crud.update_settings(db_session, user_id, {
            "new_orders_enabled": False,
            "negative_reviews_enabled": False
        })
        
        # Обновляем настройки
        updated_settings = settings_crud.get_user_settings(db_session, user_id)
        assert updated_settings.new_orders_enabled is False
        assert updated_settings.negative_reviews_enabled is False
        
        # Данные для тестирования
        previous_orders = [{"order_id": 1, "status": "active", "amount": 1000}]
        current_orders = [
            {"order_id": 1, "status": "active", "amount": 1000},
            {"order_id": 2, "status": "active", "amount": 2000}  # новый заказ
        ]
        
        previous_reviews = []
        current_reviews = [
            {"id": 1, "rating": 2, "text": "Плохо", "product_name": "Товар 1"}  # негативный отзыв
        ]
        
        # Обнаруживаем события
        new_order_events = event_detector.detect_new_orders(user_id, current_orders, previous_orders)
        negative_review_events = event_detector.detect_negative_reviews(user_id, current_reviews, previous_reviews)
        
        # События должны быть обнаружены (детектор не знает о настройках)
        assert len(new_order_events) == 1
        assert len(negative_review_events) == 1
        
        # Но в реальной системе здесь должна быть проверка настроек пользователя
        # и фильтрация событий на основе этих настроек
    
    def test_status_monitor_with_redis_integration(self, db_session):
        """Тест интеграции Status Change Monitor с Redis"""
        status_monitor = StatusChangeMonitor()
        order_crud = OrderStatusHistoryCRUD()
        
        user_id = 555666777
        
        # Мокаем Redis с предыдущим состоянием
        mock_redis = Mock()
        previous_state = {"1": "active", "2": "active"}
        mock_redis.get.return_value = previous_state
        
        # Текущие заказы с изменениями
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000},  # active -> buyout
            {"order_id": 2, "status": "cancelled", "amount": 1500},  # active -> cancelled
            {"order_id": 3, "status": "active", "amount": 2000}  # новый заказ
        ]
        
        # Отслеживаем изменения
        changes = status_monitor.track_order_changes(user_id, current_orders, mock_redis)
        
        # Должны быть обнаружены изменения
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
        
        # Записываем изменения в БД
        for change in changes:
            if change.get("previous_status") != change.get("current_status"):
                order_crud.track_status_change(
                    db_session,
                    user_id,
                    change["order_id"],
                    change.get("previous_status"),
                    change.get("current_status")
                )
        
        # Проверяем, что записи созданы в БД
        pending_changes = order_crud.get_pending_changes(db_session, user_id)
        assert len(pending_changes) == 3
        
        # Проверяем Redis вызовы
        mock_redis.get.assert_called_with(f"notifications:order_status:{user_id}")
        mock_redis.set.assert_called_once()
        
        # Проверяем, что текущее состояние сохранено
        saved_state = json.loads(mock_redis.set.call_args[0][1])
        assert saved_state["1"] == "buyout"
        assert saved_state["2"] == "cancelled"
        assert saved_state["3"] == "active"
    
    def test_no_events_detected(self, db_session):
        """Тест отсутствия событий"""
        event_detector = EventDetector()
        status_monitor = StatusChangeMonitor()
        
        user_id = 111222333
        
        # Одинаковые данные (нет изменений)
        orders = [{"order_id": 1, "status": "active", "amount": 1000}]
        reviews = [{"id": 1, "rating": 5, "text": "Отлично!"}]
        stocks = [{"nm_id": 1, "name": "Товар 1", "stocks": {"S": 10, "M": 5}}]
        
        # Мокаем Redis
        mock_redis = Mock()
        mock_redis.get.return_value = {"1": "active"}
        
        # Не должно быть событий
        new_order_events = event_detector.detect_new_orders(user_id, orders, orders)
        status_change_events = event_detector.detect_status_changes(user_id, orders, orders)
        negative_review_events = event_detector.detect_negative_reviews(user_id, reviews, reviews)
        critical_stocks_events = event_detector.detect_critical_stocks(user_id, stocks, stocks)
        order_changes = status_monitor.track_order_changes(user_id, orders, mock_redis)
        
        assert len(new_order_events) == 0
        assert len(status_change_events) == 0
        assert len(negative_review_events) == 0
        assert len(critical_stocks_events) == 0
        assert len(order_changes) == 0
