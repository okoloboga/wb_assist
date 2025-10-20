"""
Full integration tests for complete notification flow
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.features.notifications.notification_service import NotificationService
from app.features.notifications.queue_manager import QueueManager
from app.features.notifications.retry_logic import RetryLogic, RetryConfig
from app.features.notifications.redis_integration import RedisIntegration, CacheConfig
from app.features.notifications.event_detector import EventDetector
from app.features.notifications.status_monitor import StatusChangeMonitor
from app.features.notifications.notification_generator import NotificationGenerator


class TestFullNotificationFlow:
    """Full integration tests for complete notification flow"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for integration testing"""
        redis = Mock()
        redis.lpush = Mock(return_value=1)
        redis.rpop = Mock(return_value=None)
        redis.llen = Mock(return_value=0)
        redis.lrange = Mock(return_value=[])
        redis.delete = Mock(return_value=1)
        redis.expire = Mock(return_value=True)
        redis.get = Mock(return_value=None)
        redis.set = Mock(return_value=True)
        redis.incr = Mock(return_value=1)
        redis.decr = Mock(return_value=0)
        return redis

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.query = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        return db

    @pytest.fixture
    def notification_service(self, mock_db, mock_redis):
        """NotificationService for integration testing"""
        return NotificationService(mock_db, mock_redis)

    @pytest.fixture
    def queue_manager(self, mock_redis):
        """QueueManager for integration testing"""
        return QueueManager(mock_redis)

    @pytest.fixture
    def retry_logic(self):
        """RetryLogic for integration testing"""
        config = RetryConfig(
            max_retries=3,
            base_delay=0.01,
            max_delay=0.1,
            backoff_multiplier=2.0,
            jitter=False
        )
        return RetryLogic(config)

    @pytest.fixture
    def redis_integration(self, mock_redis):
        """RedisIntegration for integration testing"""
        return RedisIntegration(mock_redis, CacheConfig())

    def test_complete_new_order_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow from new order to notification delivery"""
        # 1. Simulate new order data
        current_orders = [{
            "id": "order_123",
            "amount": 2500,
            "product_name": "Test Product",
            "status": "new",
            "created_at": datetime.now(timezone.utc)
        }]
        
        previous_orders = []
        
        # 2. Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                current_reviews=[],
                previous_reviews=[],
                current_stocks=[],
                previous_stocks=[],
                bot_webhook_url="http://test.com/webhook"
            ))
            
            # 4. Verify notification was processed
            assert result["notifications_sent"] == 1, "Should send 1 notification for new order"
            assert result["events_processed"] == 1, "Should process 1 event"
            
            print("✅ Complete new order flow: successful")

    def test_complete_order_status_change_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow from order status change to notification delivery"""
        # 1. Simulate order status change
        current_orders = [{
            "id": "order_123",
            "amount": 2500,
            "product_name": "Test Product",
            "status": "buyout",
            "updated_at": datetime.now(timezone.utc)
        }]
        
        previous_orders = [{
            "id": "order_123",
            "amount": 2500,
            "product_name": "Test Product",
            "status": "new",
            "updated_at": datetime.now(timezone.utc)
        }]
        
        # 2. Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.order_buyouts_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                current_reviews=[],
                previous_reviews=[],
                current_stocks=[],
                previous_stocks=[],
                bot_webhook_url="http://test.com/webhook"
            ))
            
            # 4. Verify notification was processed
            assert result["notifications_sent"] == 1, "Should send 1 notification for status change"
            assert result["events_processed"] == 1, "Should process 1 event"
            
            print("✅ Complete order status change flow: successful")

    def test_complete_negative_review_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow from negative review to notification delivery"""
        # 1. Simulate negative review
        current_reviews = [{
            "id": "review_123",
            "product_name": "Test Product",
            "rating": 2,
            "comment": "Bad product",
            "created_at": datetime.now(timezone.utc)
        }]
        
        previous_reviews = []
        
        # 2. Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.negative_reviews_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=[],
                previous_orders=[],
                current_reviews=current_reviews,
                previous_reviews=previous_reviews,
                current_stocks=[],
                previous_stocks=[],
                bot_webhook_url="http://test.com/webhook"
            ))
            
            # 4. Verify notification was processed
            assert result["notifications_sent"] == 1, "Should send 1 notification for negative review"
            assert result["events_processed"] == 1, "Should process 1 event"
            
            print("✅ Complete negative review flow: successful")

    def test_complete_critical_stocks_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow from critical stocks to notification delivery"""
        # 1. Simulate critical stocks
        current_stocks = [{
            "id": "stock_123",
            "product_name": "Test Product",
            "quantity": 5,
            "threshold": 10,
            "updated_at": datetime.now(timezone.utc)
        }]
        
        previous_stocks = [{
            "id": "stock_123",
            "product_name": "Test Product",
            "quantity": 15,
            "threshold": 10,
            "updated_at": datetime.now(timezone.utc)
        }]
        
        # 2. Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.critical_stocks_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=[],
                previous_orders=[],
                current_reviews=[],
                previous_reviews=[],
                current_stocks=current_stocks,
                previous_stocks=previous_stocks,
                bot_webhook_url="http://test.com/webhook"
            ))
            
            # 4. Verify notification was processed
            assert result["notifications_sent"] == 1, "Should send 1 notification for critical stocks"
            assert result["events_processed"] == 1, "Should process 1 event"
            
            print("✅ Complete critical stocks flow: successful")

    def test_complete_mixed_events_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow with mixed events"""
        # 1. Simulate mixed events
        current_orders = [{
            "id": "order_123",
            "amount": 2500,
            "product_name": "Test Product 1",
            "status": "new",
            "created_at": datetime.now(timezone.utc)
        }]
        
        previous_orders = []
        
        current_reviews = [{
            "id": "review_123",
            "product_name": "Test Product 2",
            "rating": 2,
            "comment": "Bad product",
            "created_at": datetime.now(timezone.utc)
        }]
        
        previous_reviews = []
        
        current_stocks = [{
            "id": "stock_123",
            "product_name": "Test Product 3",
            "quantity": 5,
            "threshold": 10,
            "updated_at": datetime.now(timezone.utc)
        }]
        
        previous_stocks = [{
            "id": "stock_123",
            "product_name": "Test Product 3",
            "quantity": 15,
            "threshold": 10,
            "updated_at": datetime.now(timezone.utc)
        }]
        
        # 2. Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.negative_reviews_enabled = True
        mock_settings.critical_stocks_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                current_reviews=current_reviews,
                previous_reviews=previous_reviews,
                current_stocks=current_stocks,
                previous_stocks=previous_stocks,
                bot_webhook_url="http://test.com/webhook"
            ))
            
            # 4. Verify notifications were processed
            assert result["notifications_sent"] == 3, "Should send 3 notifications for mixed events"
            assert result["events_processed"] == 3, "Should process 3 events"
            
            print("✅ Complete mixed events flow: successful")

    def test_complete_grouped_notifications_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow with grouped notifications"""
        # 1. Simulate multiple orders
        current_orders = [
            {
                "id": "order_123",
                "amount": 2500,
                "product_name": "Test Product 1",
                "status": "new",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": "order_124",
                "amount": 3000,
                "product_name": "Test Product 2",
                "status": "new",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": "order_125",
                "amount": 1500,
                "product_name": "Test Product 3",
                "status": "new",
                "created_at": datetime.now(timezone.utc)
            }
        ]
        
        previous_orders = []
        
        # 2. Mock user settings with grouping enabled
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = True
        mock_settings.max_group_size = 3
        mock_settings.group_timeout = 300  # 5 minutes
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                current_reviews=[],
                previous_reviews=[],
                current_stocks=[],
                previous_stocks=[],
                bot_webhook_url="http://test.com/webhook"
            ))
            
            # 4. Verify grouped notification was processed
            assert result["notifications_sent"] == 1, "Should send 1 grouped notification"
            assert result["events_processed"] == 3, "Should process 3 events"
            
            print("✅ Complete grouped notifications flow: successful")

    def test_complete_notification_disabled_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow with notifications disabled"""
        # 1. Simulate events
        current_orders = [{
            "id": "order_123",
            "amount": 2500,
            "product_name": "Test Product",
            "status": "new",
            "created_at": datetime.now(timezone.utc)
        }]
        
        previous_orders = []
        
        # 2. Mock user settings with notifications disabled
        mock_settings = Mock()
        mock_settings.notifications_enabled = False
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                current_reviews=[],
                previous_reviews=[],
                current_stocks=[],
                previous_stocks=[],
                bot_webhook_url="http://test.com/webhook"
            ))
            
            # 4. Verify no notifications were sent
            assert result["notifications_sent"] == 0, "Should send 0 notifications when disabled"
            assert result["events_processed"] == 0, "Should process 0 events when disabled"
            
            print("✅ Complete notification disabled flow: successful")

    def test_complete_error_handling_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow with error handling"""
        # 1. Simulate events with errors
        current_orders = [{
            "id": "order_123",
            "amount": 2500,
            "product_name": "Test Product",
            "status": "new",
            "created_at": datetime.now(timezone.utc)
        }]
        
        previous_orders = []
        
        # 2. Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Mock webhook failure
            with patch('app.features.notifications.notification_service.NotificationService._send_webhook_notification') as mock_webhook:
                mock_webhook.side_effect = Exception("Webhook failed")
                
                # 4. Process sync events
                result = asyncio.run(notification_service.process_sync_events(
                    user_id=1,
                    cabinet_id=1,
                    current_orders=current_orders,
                    previous_orders=previous_orders,
                    current_reviews=[],
                    previous_reviews=[],
                    current_stocks=[],
                    previous_stocks=[],
                    bot_webhook_url="http://test.com/webhook"
                ))
                
                # 5. Verify error handling
                assert result["notifications_sent"] == 0, "Should send 0 notifications when webhook fails"
                assert result["events_processed"] == 1, "Should process 1 event"
                assert result["errors"] == 1, "Should record 1 error"
                
                print("✅ Complete error handling flow: successful")

    def test_complete_performance_flow(self, notification_service, queue_manager, retry_logic, redis_integration):
        """Test complete flow performance"""
        import time
        
        # 1. Simulate large dataset
        current_orders = []
        for i in range(100):
            order = {
                "id": f"order_{i}",
                "amount": 1000 + i,
                "product_name": f"Test Product {i}",
                "status": "new",
                "created_at": datetime.now(timezone.utc)
            }
            current_orders.append(order)
        
        previous_orders = []
        
        # 2. Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = False
        
        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # 3. Process sync events and measure performance
            start_time = time.time()
            
            result = asyncio.run(notification_service.process_sync_events(
                user_id=1,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                current_reviews=[],
                previous_reviews=[],
                current_stocks=[],
                previous_stocks=[],
                bot_webhook_url="http://test.com/webhook"
            ))
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 4. Verify performance
            assert processing_time < 5.0, f"Processing took {processing_time:.2f}s, should be < 5s"
            assert result["notifications_sent"] == 100, "Should send 100 notifications"
            assert result["events_processed"] == 100, "Should process 100 events"
            
            print(f"✅ Complete performance flow: {processing_time:.2f}s for 100 notifications")
            print(f"✅ Throughput: {100/processing_time:.0f} notifications/second")
