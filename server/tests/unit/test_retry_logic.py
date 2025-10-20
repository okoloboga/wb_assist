"""
Unit tests for Retry Logic with exponential backoff
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.features.notifications.retry_logic import RetryLogic, RetryConfig


@pytest.fixture
def retry_config():
    """Retry configuration"""
    return RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_multiplier=2.0,
        jitter=True
    )


@pytest.fixture
def retry_logic(retry_config):
    """RetryLogic instance"""
    return RetryLogic(retry_config)


@pytest.fixture
def mock_async_function():
    """Mock async function"""
    return AsyncMock()


class TestRetryLogic:
    """Test Retry Logic functionality"""

    def test_retry_logic_initialization(self, retry_logic, retry_config):
        """Test RetryLogic initialization"""
        assert retry_logic.config == retry_config
        assert retry_logic.config.max_retries == 3
        assert retry_logic.config.base_delay == 1.0
        assert retry_logic.config.max_delay == 60.0
        assert retry_logic.config.backoff_multiplier == 2.0
        assert retry_logic.config.jitter is True

    def test_retry_config_defaults(self):
        """Test RetryConfig default values"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True

    def test_calculate_delay_no_jitter(self):
        """Test delay calculation without jitter"""
        config = RetryConfig(jitter=False, base_delay=1.0, backoff_multiplier=2.0)
        retry_logic = RetryLogic(config)
        
        # First retry: 1.0 * 2^0 = 1.0
        delay1 = retry_logic._calculate_delay(0)
        assert delay1 == 1.0
        
        # Second retry: 1.0 * 2^1 = 2.0
        delay2 = retry_logic._calculate_delay(1)
        assert delay2 == 2.0
        
        # Third retry: 1.0 * 2^2 = 4.0
        delay3 = retry_logic._calculate_delay(2)
        assert delay3 == 4.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter"""
        config = RetryConfig(jitter=True, base_delay=1.0, backoff_multiplier=2.0)
        retry_logic = RetryLogic(config)
        
        # With jitter, delay should be between 0.5 and 1.5 times the base delay
        delay = retry_logic._calculate_delay(0)
        assert 0.5 <= delay <= 1.5

    def test_calculate_delay_max_delay_limit(self):
        """Test delay calculation with max delay limit"""
        config = RetryConfig(base_delay=1.0, backoff_multiplier=2.0, max_delay=5.0)
        retry_logic = RetryLogic(config)
        
        # Without max limit: 1.0 * 2^3 = 8.0
        # With max limit: should be capped at 5.0
        delay = retry_logic._calculate_delay(3)
        assert delay <= 5.0

    def test_calculate_delay_max_delay_with_jitter(self):
        """Test delay calculation with max delay and jitter"""
        config = RetryConfig(
            base_delay=1.0, 
            backoff_multiplier=2.0, 
            max_delay=5.0,
            jitter=True
        )
        retry_logic = RetryLogic(config)
        
        delay = retry_logic._calculate_delay(3)
        # Should be capped at max_delay even with jitter
        assert delay <= 5.0

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self, retry_logic, mock_async_function):
        """Test successful execution on first attempt"""
        mock_async_function.return_value = "success"
        
        result = await retry_logic.execute_with_retry(mock_async_function)
        
        assert result == "success"
        assert mock_async_function.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self, retry_logic, mock_async_function):
        """Test successful execution after retries"""
        mock_async_function.side_effect = [Exception("Error 1"), Exception("Error 2"), "success"]
        
        result = await retry_logic.execute_with_retry(mock_async_function)
        
        assert result == "success"
        assert mock_async_function.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_max_retries_exceeded(self, retry_logic, mock_async_function):
        """Test failure after max retries exceeded"""
        mock_async_function.side_effect = Exception("Persistent error")
        
        with pytest.raises(Exception, match="Persistent error"):
            await retry_logic.execute_with_retry(mock_async_function)
        
        assert mock_async_function.call_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_execute_with_retry_custom_exception_handler(self, retry_logic, mock_async_function):
        """Test retry with custom exception handler"""
        def should_retry(exception):
            return isinstance(exception, ValueError)
        
        mock_async_function.side_effect = [ValueError("Retryable"), "success"]
        
        result = await retry_logic.execute_with_retry(
            mock_async_function, 
            should_retry=should_retry
        )
        
        assert result == "success"
        assert mock_async_function.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_non_retryable_exception(self, retry_logic, mock_async_function):
        """Test non-retryable exception"""
        def should_retry(exception):
            return isinstance(exception, ValueError)
        
        mock_async_function.side_effect = TypeError("Non-retryable error")
        
        with pytest.raises(TypeError, match="Non-retryable error"):
            await retry_logic.execute_with_retry(
                mock_async_function, 
                should_retry=should_retry
            )
        
        assert mock_async_function.call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_execute_with_retry_delay_timing(self, retry_logic, mock_async_function):
        """Test that retry delays are applied correctly"""
        config = RetryConfig(
            max_retries=2,
            base_delay=0.1,  # 100ms
            backoff_multiplier=2.0,
            jitter=False
        )
        retry_logic = RetryLogic(config)
        
        mock_async_function.side_effect = [Exception("Error 1"), Exception("Error 2"), "success"]
        
        start_time = time.time()
        result = await retry_logic.execute_with_retry(mock_async_function)
        end_time = time.time()
        
        assert result == "success"
        # Should have delays: 0.1s + 0.2s = 0.3s minimum
        assert end_time - start_time >= 0.3

    @pytest.mark.asyncio
    async def test_execute_with_retry_callback(self, retry_logic, mock_async_function):
        """Test retry with callback function"""
        callback_calls = []
        
        def retry_callback(attempt, exception, delay):
            callback_calls.append((attempt, str(exception), delay))
        
        mock_async_function.side_effect = [Exception("Error 1"), "success"]
        
        result = await retry_logic.execute_with_retry(
            mock_async_function,
            retry_callback=retry_callback
        )
        
        assert result == "success"
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1  # First retry attempt
        assert "Error 1" in callback_calls[0][1]
        assert callback_calls[0][2] > 0  # Delay should be positive

    @pytest.mark.asyncio
    async def test_execute_with_retry_context_manager(self, retry_logic, mock_async_function):
        """Test retry with context manager"""
        mock_async_function.side_effect = [Exception("Error 1"), "success"]
        
        async with retry_logic.retry_context() as retry:
            result = await retry(mock_async_function)
        
        assert result == "success"
        assert mock_async_function.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_context_manager_failure(self, retry_logic, mock_async_function):
        """Test retry context manager with failure"""
        mock_async_function.side_effect = Exception("Persistent error")
        
        with pytest.raises(Exception, match="Persistent error"):
            async with retry_logic.retry_context() as retry:
                await retry(mock_async_function)

    def test_retry_config_validation(self):
        """Test RetryConfig validation"""
        # Valid config
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            backoff_multiplier=1.5,
            jitter=False
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.backoff_multiplier == 1.5
        assert config.jitter is False

    def test_retry_config_edge_cases(self):
        """Test RetryConfig edge cases"""
        # Zero retries
        config = RetryConfig(max_retries=0)
        assert config.max_retries == 0
        
        # Very small delays
        config = RetryConfig(base_delay=0.001, max_delay=0.01)
        assert config.base_delay == 0.001
        assert config.max_delay == 0.01
        
        # Large backoff multiplier
        config = RetryConfig(backoff_multiplier=10.0)
        assert config.backoff_multiplier == 10.0

    @pytest.mark.asyncio
    async def test_execute_with_retry_different_retry_counts(self, mock_async_function):
        """Test retry with different retry counts"""
        # Test with 1 retry
        config1 = RetryConfig(max_retries=1)
        retry_logic1 = RetryLogic(config1)
        
        mock_async_function.side_effect = [Exception("Error 1"), "success"]
        result = await retry_logic1.execute_with_retry(mock_async_function)
        assert result == "success"
        assert mock_async_function.call_count == 2
        
        # Reset mock
        mock_async_function.reset_mock()
        
        # Test with 0 retries
        config0 = RetryConfig(max_retries=0)
        retry_logic0 = RetryLogic(config0)
        
        mock_async_function.side_effect = Exception("Error")
        with pytest.raises(Exception):
            await retry_logic0.execute_with_retry(mock_async_function)
        assert mock_async_function.call_count == 1
