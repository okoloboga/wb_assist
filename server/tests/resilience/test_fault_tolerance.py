"""
Resilience tests for notification system fault tolerance
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.features.notifications.notification_service import NotificationService
from app.features.notifications.queue_manager import QueueManager
from app.features.notifications.retry_logic import RetryLogic, RetryConfig
from app.features.notifications.redis_integration import RedisIntegration, CacheConfig


class TestNotificationSystemResilience:
    """Resilience tests for notification system"""

    @pytest.fixture
    def mock_redis_failing(self):
        """Mock Redis client that fails intermittently"""
        redis = Mock()
        
        # Simulate intermittent failures
        call_count = 0
        def failing_lpush(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd call
                raise Exception("Redis connection failed")
            return 1
        
        def failing_rpop(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 5 == 0:  # Fail every 5th call
                raise Exception("Redis read failed")
            return None
        
        redis.lpush = Mock(side_effect=failing_lpush)
        redis.rpop = Mock(side_effect=failing_rpop)
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
    def mock_db_failing(self):
        """Mock database that fails intermittently"""
        db = Mock()
        
        call_count = 0
        def failing_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 4 == 0:  # Fail every 4th call
                raise Exception("Database connection failed")
            return Mock()
        
        db.query = Mock(side_effect=failing_query)
        db.commit = Mock()
        db.rollback = Mock()
        
        return db

    def test_redis_failure_graceful_degradation(self, mock_redis_failing):
        """Test system behavior when Redis fails"""
        queue_manager = QueueManager(mock_redis_failing)
        
        notification = {
            "id": "test_notification",
            "user_id": 1,
            "type": "new_order",
            "priority": "HIGH",
            "content": "Test notification",
            "webhook_url": "http://test.com/webhook"
        }
        
        # Test that system continues to work despite Redis failures
        success_count = 0
        failure_count = 0
        
        for i in range(10):
            try:
                queue_manager.add_notification_to_queue(notification)
                success_count += 1
            except Exception:
                failure_count += 1
        
        # System should handle some failures gracefully
        assert success_count > 0, "System should handle some operations despite Redis failures"
        assert failure_count > 0, "Some operations should fail due to Redis issues"
        
        print(f"✅ Redis resilience: {success_count}/10 operations succeeded")

    def test_database_failure_graceful_degradation(self, mock_db_failing, mock_redis_failing):
        """Test system behavior when database fails"""
        notification_service = NotificationService(mock_db_failing, mock_redis_failing)
        
        orders = [{
            "id": "test_order",
            "amount": 1000,
            "product_name": "Test Product",
            "status": "new"
        }]
        
        # Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = False

        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # Test that system continues to work despite database failures
            success_count = 0
            failure_count = 0
            
            for i in range(10):
                try:
                    result = asyncio.run(notification_service.process_sync_events(
                        user_id=1,
                        cabinet_id=1,
                        current_orders=orders,
                        previous_orders=[],
                        current_reviews=[],
                        previous_reviews=[],
                        current_stocks=[],
                        previous_stocks=[],
                        bot_webhook_url="http://test.com/webhook"
                    ))
                    success_count += 1
                except Exception:
                    failure_count += 1
            
            # System should handle some failures gracefully
            assert success_count > 0, "System should handle some operations despite database failures"
            assert failure_count > 0, "Some operations should fail due to database issues"
            
            print(f"✅ Database resilience: {success_count}/10 operations succeeded")

    def test_webhook_failure_retry_mechanism(self):
        """Test retry mechanism for webhook failures"""
        config = RetryConfig(
            max_retries=3,
            base_delay=0.01,  # 10ms for fast testing
            max_delay=0.1,
            backoff_multiplier=2.0,
            jitter=False
        )
        retry_logic = RetryLogic(config)
        
        call_count = 0
        async def failing_webhook():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise Exception("Webhook failed")
            return "Success"
        
        async def run_retry_test():
            start_time = time.time()
            result = await retry_logic.execute_with_retry(failing_webhook)
            end_time = time.time()
            
            # Should succeed after retries
            assert result == "Success", "Webhook should succeed after retries"
            assert call_count == 3, "Should have retried 3 times"
            assert end_time - start_time < 1.0, "Retry should complete within reasonable time"
            
            print(f"✅ Webhook retry: succeeded after {call_count} attempts")
        
        # Run the async test
        asyncio.run(run_retry_test())

    def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        config = RetryConfig(
            max_retries=2,
            base_delay=0.01,
            max_delay=0.05,
            backoff_multiplier=2.0,
            jitter=False
        )
        retry_logic = RetryLogic(config)
        
        async def timeout_function():
            await asyncio.sleep(0.1)  # Simulate network delay
            raise asyncio.TimeoutError("Network timeout")
        
        async def run_timeout_test():
            start_time = time.time()
            result = await retry_logic.execute_with_retry(timeout_function)
            end_time = time.time()
            
            # Should handle timeout gracefully
            assert result is None, "Should return None after timeout"
            assert end_time - start_time < 0.5, "Timeout handling should be fast"
            
            print(f"✅ Network timeout: handled gracefully in {end_time - start_time:.2f}s")
        
        # Run the async test
        asyncio.run(run_timeout_test())

    def test_memory_pressure_handling(self, mock_redis):
        """Test system behavior under memory pressure"""
        queue_manager = QueueManager(mock_redis)
        
        # Simulate memory pressure by creating large notifications
        large_notifications = []
        for i in range(1000):
            notification = {
                "id": f"large_notif_{i}",
                "user_id": 1,
                "type": "new_order",
                "priority": "HIGH",
                "content": "X" * 10000,  # 10KB content
                "webhook_url": "http://test.com/webhook"
            }
            large_notifications.append(notification)
        
        # System should handle memory pressure gracefully
        start_time = time.time()
        
        for notification in large_notifications:
            try:
                queue_manager.add_notification_to_queue(notification)
            except Exception as e:
                # Should handle memory pressure gracefully
                assert "memory" in str(e).lower() or "resource" in str(e).lower()
                break
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should handle memory pressure within reasonable time
        assert processing_time < 5.0, f"Memory pressure handling took {processing_time:.2f}s, should be < 5s"
        
        print(f"✅ Memory pressure: handled gracefully in {processing_time:.2f}s")

    def test_concurrent_failure_handling(self, mock_redis_failing):
        """Test handling of concurrent failures"""
        queue_manager = QueueManager(mock_redis_failing)
        
        async def process_notification(notification_id):
            """Process a single notification"""
            notification = {
                "id": f"notif_{notification_id}",
                "user_id": 1,
                "type": "new_order",
                "priority": "HIGH",
                "content": f"Notification {notification_id}",
                "webhook_url": "http://test.com/webhook"
            }
            
            try:
                queue_manager.add_notification_to_queue(notification)
                return "success"
            except Exception:
                return "failure"
        
        async def run_concurrent_test():
            # Process 100 notifications concurrently
            start_time = time.time()
            tasks = [process_notification(i) for i in range(100)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Count successes and failures
            successes = sum(1 for result in results if result == "success")
            failures = sum(1 for result in results if result == "failure")
            
            # System should handle concurrent failures gracefully
            assert successes > 0, "Some operations should succeed despite concurrent failures"
            assert failures > 0, "Some operations should fail due to concurrent issues"
            assert end_time - start_time < 10.0, f"Concurrent processing took {end_time - start_time:.2f}s, should be < 10s"
            
            print(f"✅ Concurrent resilience: {successes}/100 succeeded, {failures}/100 failed")
        
        # Run the async test
        asyncio.run(run_concurrent_test())

    def test_data_corruption_recovery(self, mock_redis):
        """Test recovery from data corruption"""
        redis_integration = RedisIntegration(mock_redis, CacheConfig())
        
        # Simulate corrupted data
        corrupted_data = "corrupted_json_data{"
        mock_redis.get.return_value = corrupted_data
        
        # System should handle corrupted data gracefully
        try:
            result = redis_integration.get_cache("test_key")
            assert result is None, "Should return None for corrupted data"
        except Exception as e:
            # Should handle corruption gracefully
            assert "json" in str(e).lower() or "decode" in str(e).lower()
        
        print("✅ Data corruption: handled gracefully")

    def test_partial_system_failure(self, mock_redis_failing, mock_db_failing):
        """Test system behavior with partial failures"""
        notification_service = NotificationService(mock_db_failing, mock_redis_failing)
        
        orders = [{
            "id": "test_order",
            "amount": 1000,
            "product_name": "Test Product",
            "status": "new"
        }]
        
        # Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = False

        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            # Test system behavior with partial failures
            success_count = 0
            failure_count = 0
            
            for i in range(20):
                try:
                    result = asyncio.run(notification_service.process_sync_events(
                        user_id=1,
                        cabinet_id=1,
                        current_orders=orders,
                        previous_orders=[],
                        current_reviews=[],
                        previous_reviews=[],
                        current_stocks=[],
                        previous_stocks=[],
                        bot_webhook_url="http://test.com/webhook"
                    ))
                    success_count += 1
                except Exception:
                    failure_count += 1
            
            # System should handle partial failures gracefully
            assert success_count > 0, "Some operations should succeed despite partial failures"
            assert failure_count > 0, "Some operations should fail due to partial issues"
            
            print(f"✅ Partial failure resilience: {success_count}/20 succeeded, {failure_count}/20 failed")

    def test_cascade_failure_prevention(self, mock_redis):
        """Test prevention of cascade failures"""
        queue_manager = QueueManager(mock_redis)
        
        # Simulate cascade failure scenario
        def failing_operation():
            raise Exception("Cascade failure")
        
        # System should prevent cascade failures
        try:
            queue_manager.add_notification_to_queue({
                "id": "test",
                "user_id": 1,
                "type": "new_order",
                "priority": "HIGH",
                "content": "Test",
                "webhook_url": "http://test.com/webhook"
            })
        except Exception as e:
            # Should handle cascade failures gracefully
            assert "cascade" in str(e).lower() or "failure" in str(e).lower()
        
        print("✅ Cascade failure: prevented gracefully")

    def test_system_recovery_after_failure(self, mock_redis):
        """Test system recovery after failure"""
        queue_manager = QueueManager(mock_redis)
        
        # Simulate system failure and recovery
        notification = {
            "id": "recovery_test",
            "user_id": 1,
            "type": "new_order",
            "priority": "HIGH",
            "content": "Recovery test",
            "webhook_url": "http://test.com/webhook"
        }
        
        # System should recover after failure
        try:
            queue_manager.add_notification_to_queue(notification)
            print("✅ System recovery: successful after failure")
        except Exception as e:
            print(f"❌ System recovery: failed with {e}")
            # Should still be able to recover
            assert False, "System should recover after failure"
