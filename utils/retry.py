"""
Klix - Retry Utilities
Provides retry decorator with exponential backoff for resilient operations.
"""

from __future__ import annotations

import asyncio
import functools
import random
import time
from typing import Any, Callable, Type, TypeVar

from logging_config import get_logger

logger = get_logger(__name__)

# Type variables
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable[[F], F]:
    """
    Decorator that retries a function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first try).
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        exceptions: Tuple of exception types to retry on.
        on_retry: Optional callback called on each retry with (exception, attempt).
    
    Usage:
        @retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
        def call_api():
            ...
        
        @retry(max_attempts=5, base_delay=0.5)
        async def async_call_api():
            ...
    """
    def decorator(func: F) -> F:
        # Check if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay,
                    )
                    
                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    await asyncio.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay,
                    )
                    
                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return async_wrapper if is_async else sync_wrapper  # type: ignore
    
    return decorator


class RetryConfig:
    """Configuration object for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def decorator(
        self,
        exceptions: tuple[Type[Exception], ...] = (Exception,),
    ) -> Callable[[F], F]:
        """Create a retry decorator from this config."""
        return retry(
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential_base=self.exponential_base,
            jitter=self.jitter,
            exceptions=exceptions,
        )


# Pre-configured retry decorators for common use cases
retry_api = retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exceptions=(Exception,),
)

retry_network = retry(
    max_attempts=5,
    base_delay=0.5,
    max_delay=60.0,
    exceptions=(ConnectionError, TimeoutError, OSError),
)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "retry",
    "RetryConfig",
    "retry_api",
    "retry_network",
]
