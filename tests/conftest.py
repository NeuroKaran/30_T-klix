"""
Pytest fixtures and configuration for Klix tests.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_env() -> Generator[dict[str, str], None, None]:
    """
    Mock environment variables for testing.
    Restores original environment after test.
    """
    original_env = os.environ.copy()
    test_env: dict[str, str] = {}
    
    with patch.dict(os.environ, test_env, clear=False):
        yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """
    Run test with a clean environment (key Klix vars removed).
    """
    keys_to_remove = [
        "GOOGLE_API_KEY",
        "OLLAMA_HOST",
        "GEMINI_MODEL",
        "OLLAMA_MODEL",
        "DEFAULT_MODEL",
        "USER_NAME",
        "ORG_NAME",
        "MEM0_API_KEY",
        "MEMORY_ENABLED",
        "LOG_LEVEL",
    ]
    
    original_values = {}
    for key in keys_to_remove:
        if key in os.environ:
            original_values[key] = os.environ.pop(key)
    
    yield
    
    # Restore original values
    for key, value in original_values.items():
        os.environ[key] = value


@pytest.fixture
def reset_logging() -> Generator[None, None, None]:
    """Reset logging configuration between tests."""
    import logging
    import logging_config
    
    # Store original state
    original_configured = logging_config._configured
    original_log_dir = logging_config._log_dir
    
    # Reset state
    logging_config._configured = False
    logging_config._log_dir = None
    
    yield
    
    # Restore state
    logging_config._configured = original_configured
    logging_config._log_dir = original_log_dir
    
    # Clear handlers added during test
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)
