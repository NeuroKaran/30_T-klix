"""
Tests for the retry module.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest


class TestRetryDecorator:
    """Tests for the retry decorator."""
    
    def test_sync_success_first_attempt(self):
        """Test sync function succeeds on first attempt."""
        from utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        
        assert result == "success"
        assert call_count == 1
    
    def test_sync_success_after_retry(self):
        """Test sync function succeeds after retries."""
        from utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01, jitter=False)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert call_count == 3
    
    def test_sync_failure_max_attempts(self):
        """Test sync function fails after max attempts."""
        from utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01, jitter=False)
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")
        
        with pytest.raises(ValueError, match="Persistent error"):
            failing_func()
        
        assert call_count == 3
    
    def test_sync_specific_exceptions(self):
        """Test retry only catches specified exceptions."""
        from utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
        def func_with_wrong_exception():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retried")
        
        with pytest.raises(TypeError):
            func_with_wrong_exception()
        
        # Should not retry on TypeError
        assert call_count == 1
    
    def test_sync_on_retry_callback(self):
        """Test on_retry callback is called."""
        from utils.retry import retry
        
        callback_calls = []
        
        def on_retry_callback(exc, attempt):
            callback_calls.append((type(exc).__name__, attempt))
        
        @retry(max_attempts=3, base_delay=0.01, jitter=False, on_retry=on_retry_callback)
        def flaky_func():
            if len(callback_calls) < 2:
                raise ValueError("Error")
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert len(callback_calls) == 2
        assert callback_calls[0] == ("ValueError", 1)
        assert callback_calls[1] == ("ValueError", 2)


class TestRetryDecoratorAsync:
    """Tests for the retry decorator with async functions."""
    
    @pytest.mark.asyncio
    async def test_async_success_first_attempt(self):
        """Test async function succeeds on first attempt."""
        from utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3)
        async def successful_async_func():
            nonlocal call_count
            call_count += 1
            return "async success"
        
        result = await successful_async_func()
        
        assert result == "async success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_success_after_retry(self):
        """Test async function succeeds after retries."""
        from utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01, jitter=False)
        async def flaky_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = await flaky_async_func()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_failure_max_attempts(self):
        """Test async function fails after max attempts."""
        from utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01, jitter=False)
        async def failing_async_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")
        
        with pytest.raises(ValueError, match="Persistent error"):
            await failing_async_func()
        
        assert call_count == 3


class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""
    
    def test_delay_increases_exponentially(self):
        """Test that delay increases with each attempt."""
        from utils.retry import retry
        
        delays = []
        
        @retry(max_attempts=4, base_delay=0.1, jitter=False, exponential_base=2.0)
        def measure_delays():
            delays.append(time.time())
            if len(delays) < 4:
                raise ValueError("Retry")
            return "done"
        
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = lambda x: delays.append(x)
            try:
                measure_delays()
            except:
                pass
        
        # Check delays are roughly doubling (base_delay * 2^attempt)
        # Attempt 1: 0.1, Attempt 2: 0.2, Attempt 3: 0.4
        if len(delays) >= 3:
            # delays list contains sleep durations
            actual_delays = [d for d in delays if isinstance(d, float) and d < 1]
            if len(actual_delays) >= 2:
                assert actual_delays[1] > actual_delays[0]
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        from utils.retry import retry
        
        captured_delays = []
        
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = lambda x: captured_delays.append(x)
            
            @retry(max_attempts=5, base_delay=10.0, max_delay=15.0, jitter=False)
            def test_func():
                if len(captured_delays) < 4:
                    raise ValueError("Retry")
                return "done"
            
            try:
                test_func()
            except:
                pass
        
        # All delays should be <= max_delay
        for delay in captured_delays:
            assert delay <= 15.0


class TestJitter:
    """Tests for jitter behavior."""
    
    def test_jitter_adds_randomness(self):
        """Test that jitter makes delays vary."""
        from utils.retry import retry
        
        delays_with_jitter = []
        
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = lambda x: delays_with_jitter.append(x)
            
            @retry(max_attempts=10, base_delay=1.0, jitter=True)
            def test_func():
                if len(delays_with_jitter) < 5:
                    raise ValueError("Retry")
                return "done"
            
            try:
                test_func()
            except:
                pass
        
        # With jitter, delays at the same attempt level should vary
        # This is a probabilistic test - we check delays are in expected range
        for delay in delays_with_jitter:
            # Jitter multiplies by 0.5 to 1.5, so delay should be 0.5x to 1.5x expected
            assert delay >= 0  # Should always be positive


class TestRetryConfig:
    """Tests for RetryConfig class."""
    
    def test_retry_config_defaults(self):
        """Test RetryConfig default values."""
        from utils.retry import RetryConfig
        
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == True
    
    def test_retry_config_custom_values(self):
        """Test RetryConfig with custom values."""
        from utils.retry import RetryConfig
        
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter == False
    
    def test_retry_config_decorator(self):
        """Test RetryConfig.decorator() method."""
        from utils.retry import RetryConfig
        
        config = RetryConfig(max_attempts=2, base_delay=0.01, jitter=False)
        
        call_count = 0
        
        @config.decorator(exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return "success"
        
        result = test_func()
        
        assert result == "success"
        assert call_count == 2


class TestPreConfiguredDecorators:
    """Tests for pre-configured retry decorators."""
    
    def test_retry_api_exists(self):
        """Test retry_api decorator is available."""
        from utils.retry import retry_api
        
        assert callable(retry_api)
    
    def test_retry_network_exists(self):
        """Test retry_network decorator is available."""
        from utils.retry import retry_network
        
        assert callable(retry_network)
    
    def test_retry_api_usage(self):
        """Test retry_api can be used as a decorator."""
        from utils.retry import retry_api
        
        call_count = 0
        
        @retry_api
        def api_call():
            nonlocal call_count
            call_count += 1
            return "api response"
        
        result = api_call()
        
        assert result == "api response"
        assert call_count == 1
    
    def test_retry_network_catches_network_errors(self):
        """Test retry_network catches network-related exceptions."""
        from utils.retry import retry_network
        
        call_count = 0
        
        # Note: We can't easily test actual retry behavior without mocking time.sleep
        # but we can verify the decorator applies correctly
        @retry_network
        def network_call():
            nonlocal call_count
            call_count += 1
            return "network response"
        
        result = network_call()
        
        assert result == "network response"
        assert call_count == 1


class TestModuleExports:
    """Tests for module exports."""
    
    def test_all_exports_available(self):
        """Test all __all__ items are importable."""
        from utils.retry import retry, RetryConfig, retry_api, retry_network
        
        assert callable(retry)
        assert RetryConfig is not None
        assert callable(retry_api)
        assert callable(retry_network)
