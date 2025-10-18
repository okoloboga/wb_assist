"""
Retry Logic with exponential backoff
"""
import asyncio
import random
import logging
from typing import Callable, Optional, Any, Awaitable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """
    Configuration for retry logic
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


class RetryLogic:
    """
    Retry logic with exponential backoff and jitter
    """
    
    def __init__(self, config: RetryConfig):
        """
        Initialize retry logic
        
        Args:
            config: Retry configuration
        """
        self.config = config
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Calculate exponential backoff
        delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
        
        # Apply jitter if enabled (before max delay limit)
        if self.config.jitter:
            # Add random jitter between 0.5 and 1.5 times the calculated delay
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor
        
        # Apply max delay limit (after jitter)
        delay = min(delay, self.config.max_delay)
        
        return delay
    
    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[Any]],
        should_retry: Optional[Callable[[Exception], bool]] = None,
        retry_callback: Optional[Callable[[int, Exception, float], None]] = None
    ) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Async function to execute
            should_retry: Optional function to determine if exception should be retried
            retry_callback: Optional callback called on each retry
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries failed
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func()
                if attempt > 0:
                    logger.info(f"Function succeeded after {attempt} retries")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception
                if should_retry and not should_retry(e):
                    logger.info(f"Exception not retryable: {e}")
                    raise e
                
                # Check if we've exhausted retries
                if attempt >= self.config.max_retries:
                    logger.error(f"All {self.config.max_retries} retries exhausted")
                    break
                
                # Calculate delay for next retry
                delay = self._calculate_delay(attempt)
                
                # Call retry callback if provided
                if retry_callback:
                    try:
                        retry_callback(attempt + 1, e, delay)
                    except Exception as callback_error:
                        logger.error(f"Retry callback failed: {callback_error}")
                
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        logger.error(f"Function failed after {self.config.max_retries} retries")
        raise last_exception
    
    def retry_context(self):
        """
        Context manager for retry logic
        
        Returns:
            Retry context manager
        """
        return RetryContext(self)


class RetryContext:
    """
    Context manager for retry logic
    """
    
    def __init__(self, retry_logic: RetryLogic):
        """
        Initialize retry context
        
        Args:
            retry_logic: RetryLogic instance
        """
        self.retry_logic = retry_logic
        self.retry_func = None
    
    async def __aenter__(self):
        """
        Enter retry context
        
        Returns:
            Retry function
        """
        return self._retry
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit retry context
        """
        pass
    
    async def _retry(
        self,
        func: Callable[[], Awaitable[Any]],
        should_retry: Optional[Callable[[Exception], bool]] = None,
        retry_callback: Optional[Callable[[int, Exception, float], None]] = None
    ) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Async function to execute
            should_retry: Optional function to determine if exception should be retried
            retry_callback: Optional callback called on each retry
            
        Returns:
            Function result
        """
        return await self.retry_logic.execute_with_retry(
            func, should_retry, retry_callback
        )


# Convenience functions for common retry scenarios

async def retry_webhook_delivery(
    webhook_func: Callable[[], Awaitable[Any]],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Any:
    """
    Retry webhook delivery with appropriate configuration
    
    Args:
        webhook_func: Function to deliver webhook
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        
    Returns:
        Function result
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=30.0,  # Max 30 seconds for webhooks
        backoff_multiplier=2.0,
        jitter=True
    )
    
    retry_logic = RetryLogic(config)
    
    def should_retry_webhook(exception: Exception) -> bool:
        """Determine if webhook exception should be retried"""
        # Retry on network errors, timeouts, and 5xx HTTP errors
        error_str = str(exception).lower()
        return any(keyword in error_str for keyword in [
            "timeout", "connection", "network", "500", "502", "503", "504"
        ])
    
    return await retry_logic.execute_with_retry(
        webhook_func,
        should_retry=should_retry_webhook
    )


async def retry_database_operation(
    db_func: Callable[[], Awaitable[Any]],
    max_retries: int = 3,
    base_delay: float = 0.5
) -> Any:
    """
    Retry database operation with appropriate configuration
    
    Args:
        db_func: Database function to execute
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        
    Returns:
        Function result
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=10.0,  # Max 10 seconds for DB operations
        backoff_multiplier=1.5,
        jitter=True
    )
    
    retry_logic = RetryLogic(config)
    
    def should_retry_db(exception: Exception) -> bool:
        """Determine if database exception should be retried"""
        # Retry on connection errors and deadlocks
        error_str = str(exception).lower()
        return any(keyword in error_str for keyword in [
            "connection", "deadlock", "timeout", "locked"
        ])
    
    return await retry_logic.execute_with_retry(
        db_func,
        should_retry=should_retry_db
    )


async def retry_external_api_call(
    api_func: Callable[[], Awaitable[Any]],
    max_retries: int = 5,
    base_delay: float = 2.0
) -> Any:
    """
    Retry external API call with appropriate configuration
    
    Args:
        api_func: API function to execute
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        
    Returns:
        Function result
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=120.0,  # Max 2 minutes for API calls
        backoff_multiplier=2.0,
        jitter=True
    )
    
    retry_logic = RetryLogic(config)
    
    def should_retry_api(exception: Exception) -> bool:
        """Determine if API exception should be retried"""
        # Retry on network errors, timeouts, and rate limiting
        error_str = str(exception).lower()
        return any(keyword in error_str for keyword in [
            "timeout", "connection", "network", "rate", "limit", "429", "500", "502", "503", "504"
        ])
    
    return await retry_logic.execute_with_retry(
        api_func,
        should_retry=should_retry_api
    )
