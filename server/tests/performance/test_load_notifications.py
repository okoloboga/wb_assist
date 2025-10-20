"""
Load tests for notification system performance
"""
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.features.notifications.notification_service import NotificationService
from app.features.notifications.queue_manager import QueueManager
from app.features.notifications.retry_logic import RetryLogic, RetryConfig


class TestNotificationSystemLoad:
    """Load tests for notification system"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for load testing"""
        redis = Mock()
        redis.lpush = Mock()
        redis.rpop = Mock()
        redis.llen = Mock()
        redis.lrange = Mock()
        redis.delete = Mock()
        redis.expire = Mock()
        redis.get = Mock()
        redis.set = Mock()
        redis.incr = Mock()
        redis.decr = Mock()
        return redis

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def notification_service(self, mock_db, mock_redis):
        """NotificationService for load testing"""
        return NotificationService(mock_db, mock_redis)

    @pytest.fixture
    def queue_manager(self, mock_redis):
        """QueueManager for load testing"""
        return QueueManager(mock_redis)

    def test_notification_service_high_volume_orders(self, notification_service, mock_db, mock_redis):
        """Test notification service with high volume of orders"""
        # Generate 1000 orders
        orders = []
        for i in range(1000):
            order = {
                "id": f"order_{i}",
                "amount": 1000 + i,
                "product_name": f"Product {i}",
                "status": "new"
            }
            orders.append(order)

        # Mock user settings
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.new_orders_enabled = True
        mock_settings.grouping_enabled = False

        with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
            mock_crud.return_value.get_user_settings.return_value = mock_settings
            
            start_time = time.time()
            
            # Process notifications
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
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Performance assertions
            assert processing_time < 5.0, f"Processing 1000 orders took {processing_time:.2f}s, should be < 5s"
            assert result["notifications_sent"] == 1000, "All orders should generate notifications"
            
            print(f"✅ Processed 1000 orders in {processing_time:.2f}s")
            print(f"✅ Throughput: {1000/processing_time:.0f} notifications/second")

    def test_queue_manager_high_volume_throughput(self, queue_manager, mock_redis):
        """Test queue manager with high volume throughput"""
        notifications = []
        for i in range(1000):
            notification = {
                "id": f"notif_{i}",
                "user_id": 1,
                "type": "new_order",
                "priority": "HIGH",
                "content": f"Notification {i}",
                "webhook_url": "http://test.com/webhook"
            }
            notifications.append(notification)

        start_time = time.time()
        
        # Add all notifications to queue
        for notification in notifications:
            queue_manager.add_notification_to_queue(notification)
        
        # Get all notifications from queue
        retrieved_notifications = []
        for _ in range(1000):
            notification = queue_manager.get_next_notification()
            if notification:
                retrieved_notifications.append(notification)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 2.0, f"Queue operations took {processing_time:.2f}s, should be < 2s"
        assert len(retrieved_notifications) == 1000, "All notifications should be retrieved"
        
        print(f"✅ Processed 1000 queue operations in {processing_time:.2f}s")
        print(f"✅ Throughput: {2000/processing_time:.0f} operations/second")

    def test_retry_logic_performance(self):
        """Test retry logic performance under load"""
        config = RetryConfig(
            max_retries=3,
            base_delay=0.01,  # 10ms for fast testing
            max_delay=0.1,
            backoff_multiplier=2.0,
            jitter=False
        )
        retry_logic = RetryLogic(config)

        async def failing_function():
            raise Exception("Test error")

        async def run_retry_tests():
            start_time = time.time()
            
            # Test 100 retry operations
            tasks = []
            for _ in range(100):
                task = retry_logic.execute_with_retry(failing_function)
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Performance assertions
            assert processing_time < 3.0, f"Retry logic took {processing_time:.2f}s, should be < 3s"
            assert len(results) == 100, "All retry operations should complete"
            
            print(f"✅ Processed 100 retry operations in {processing_time:.2f}s")
            print(f"✅ Throughput: {100/processing_time:.0f} retry operations/second")
        
        # Run the async test
        asyncio.run(run_retry_tests())

    def test_concurrent_notification_processing(self, notification_service, mock_db, mock_redis):
        """Test concurrent notification processing"""
        def process_notifications_batch(batch_id):
            """Process a batch of notifications"""
            orders = []
            for i in range(100):
                order = {
                    "id": f"order_{batch_id}_{i}",
                    "amount": 1000 + i,
                    "product_name": f"Product {batch_id}_{i}",
                    "status": "new"
                }
                orders.append(order)

            # Mock user settings
            mock_settings = Mock()
            mock_settings.notifications_enabled = True
            mock_settings.new_orders_enabled = True
            mock_settings.grouping_enabled = False

            with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
                mock_crud.return_value.get_user_settings.return_value = mock_settings
                
                result = asyncio.run(notification_service.process_sync_events(
                    user_id=batch_id,
                    cabinet_id=batch_id,
                    current_orders=orders,
                    previous_orders=[],
                    current_reviews=[],
                    previous_reviews=[],
                    current_stocks=[],
                    previous_stocks=[],
                    bot_webhook_url="http://test.com/webhook"
                ))
                
                return result["notifications_sent"]

        start_time = time.time()
        
        # Process 10 batches concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_notifications_batch, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 10.0, f"Concurrent processing took {processing_time:.2f}s, should be < 10s"
        assert sum(results) == 1000, "All notifications should be processed"
        
        print(f"✅ Processed 1000 notifications concurrently in {processing_time:.2f}s")
        print(f"✅ Throughput: {1000/processing_time:.0f} notifications/second")

    def test_memory_usage_under_load(self, queue_manager, mock_redis):
        """Test memory usage under high load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate 10000 notifications
        notifications = []
        for i in range(10000):
            notification = {
                "id": f"notif_{i}",
                "user_id": 1,
                "type": "new_order",
                "priority": "HIGH",
                "content": f"Notification {i}" * 100,  # Large content
                "webhook_url": "http://test.com/webhook"
            }
            notifications.append(notification)
        
        # Add all notifications to queue
        for notification in notifications:
            queue_manager.add_notification_to_queue(notification)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage assertions
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB, should be < 100MB"
        
        print(f"✅ Memory usage: {memory_increase:.1f}MB for 10000 notifications")
        print(f"✅ Memory per notification: {memory_increase/10000:.3f}MB")

    def test_redis_operations_performance(self, mock_redis):
        """Test Redis operations performance"""
        from app.features.notifications.redis_integration import RedisIntegration, CacheConfig
        
        redis_integration = RedisIntegration(mock_redis, CacheConfig())
        
        start_time = time.time()
        
        # Test 1000 cache operations
        for i in range(1000):
            key = f"test_key_{i}"
            value = {"data": f"test_value_{i}", "timestamp": time.time()}
            redis_integration.set_cache(key, value)
            
            retrieved_value = redis_integration.get_cache(key)
            assert retrieved_value == value
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 1.0, f"Redis operations took {processing_time:.2f}s, should be < 1s"
        
        print(f"✅ Processed 1000 Redis operations in {processing_time:.2f}s")
        print(f"✅ Throughput: {2000/processing_time:.0f} operations/second")

    def test_notification_throughput_benchmark(self, notification_service, mock_db, mock_redis):
        """Benchmark notification throughput"""
        # Test different batch sizes
        batch_sizes = [10, 50, 100, 500, 1000]
        throughput_results = []
        
        for batch_size in batch_sizes:
            orders = []
            for i in range(batch_size):
                order = {
                    "id": f"order_{i}",
                    "amount": 1000 + i,
                    "product_name": f"Product {i}",
                    "status": "new"
                }
                orders.append(order)

            # Mock user settings
            mock_settings = Mock()
            mock_settings.notifications_enabled = True
            mock_settings.new_orders_enabled = True
            mock_settings.grouping_enabled = False

            with patch('app.features.notifications.notification_service.NotificationSettingsCRUD') as mock_crud:
                mock_crud.return_value.get_user_settings.return_value = mock_settings
                
                start_time = time.time()
                
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
                
                end_time = time.time()
                processing_time = end_time - start_time
                throughput = batch_size / processing_time
                throughput_results.append(throughput)
                
                print(f"✅ Batch size {batch_size}: {throughput:.0f} notifications/second")
        
        # Calculate average throughput
        avg_throughput = statistics.mean(throughput_results)
        min_throughput = min(throughput_results)
        
        # Performance assertions
        assert avg_throughput > 100, f"Average throughput {avg_throughput:.0f} should be > 100 notifications/second"
        assert min_throughput > 50, f"Minimum throughput {min_throughput:.0f} should be > 50 notifications/second"
        
        print(f"✅ Average throughput: {avg_throughput:.0f} notifications/second")
        print(f"✅ Minimum throughput: {min_throughput:.0f} notifications/second")
