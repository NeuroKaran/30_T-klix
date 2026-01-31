"""
Tests for the logging_config module.
"""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestColoredFormatter:
    """Tests for ColoredFormatter class."""
    
    def test_format_with_colors_enabled(self):
        """Test formatting with colors enabled (TTY)."""
        from logging_config import ColoredFormatter
        
        formatter = ColoredFormatter("%(levelname)s | %(message)s", use_colors=True)
        
        # Create a mock record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        # When TTY is available, colors should be applied
        with patch.object(sys, 'stderr') as mock_stderr:
            mock_stderr.isatty.return_value = True
            formatter.use_colors = True
            result = formatter.format(record)
            
            assert "Test message" in result
    
    def test_format_without_colors(self):
        """Test formatting with colors disabled."""
        from logging_config import ColoredFormatter
        
        formatter = ColoredFormatter("%(levelname)s | %(message)s", use_colors=False)
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        
        assert "ERROR" in result
        assert "Error message" in result
    
    def test_colors_dict_contains_all_levels(self):
        """Test that COLORS dict has all standard levels."""
        from logging_config import ColoredFormatter
        
        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in expected_levels:
            assert level in ColoredFormatter.COLORS


class TestLogDir:
    """Tests for log directory functions."""
    
    def test_get_log_dir_default(self, reset_logging):
        """Test get_log_dir returns default path."""
        from logging_config import get_log_dir
        
        log_dir = get_log_dir()
        
        assert isinstance(log_dir, Path)
        assert ".klix" in str(log_dir)
        assert "logs" in str(log_dir)
    
    def test_set_log_dir(self, reset_logging, temp_dir):
        """Test set_log_dir changes the log directory."""
        from logging_config import set_log_dir, get_log_dir
        
        custom_path = temp_dir / "custom_logs"
        set_log_dir(custom_path)
        
        assert get_log_dir() == custom_path
    
    def test_set_log_dir_string(self, reset_logging, temp_dir):
        """Test set_log_dir accepts string path."""
        from logging_config import set_log_dir, get_log_dir
        
        custom_path = str(temp_dir / "string_logs")
        set_log_dir(custom_path)
        
        assert get_log_dir() == Path(custom_path)


class TestSetupLogging:
    """Tests for setup_logging function."""
    
    def test_setup_logging_configures_once(self, reset_logging):
        """Test that setup_logging only configures once."""
        import logging_config
        from logging_config import setup_logging
        
        assert logging_config._configured == False
        
        setup_logging(console=True, log_file=False)
        
        assert logging_config._configured == True
        
        # Second call should not reconfigure
        setup_logging(console=True, log_file=False)
    
    def test_setup_logging_console_handler(self, reset_logging):
        """Test setup_logging adds console handler."""
        from logging_config import setup_logging
        
        setup_logging(console=True, log_file=False)
        
        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        
        assert "StreamHandler" in handler_types
    
    def test_setup_logging_file_handler(self, temp_dir, reset_logging):
        """Test setup_logging adds file handler."""
        from logging_config import setup_logging, set_log_dir
        
        set_log_dir(temp_dir)
        setup_logging(console=False, log_file=True)
        
        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        
        assert "RotatingFileHandler" in handler_types
    
    def test_setup_logging_with_level_string(self, reset_logging):
        """Test setup_logging accepts string log level."""
        from logging_config import setup_logging
        
        setup_logging(level="DEBUG", console=True, log_file=False)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_setup_logging_with_level_int(self, reset_logging):
        """Test setup_logging accepts integer log level."""
        from logging_config import setup_logging
        
        setup_logging(level=logging.WARNING, console=True, log_file=False)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
    
    def test_setup_logging_from_env(self, reset_logging):
        """Test setup_logging reads LOG_LEVEL from environment."""
        from logging_config import setup_logging
        
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            setup_logging(console=True, log_file=False)
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.ERROR


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_get_logger_returns_logger(self, reset_logging):
        """Test get_logger returns a Logger instance."""
        from logging_config import get_logger
        
        logger = get_logger("test.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
    
    def test_get_logger_auto_configures(self, reset_logging):
        """Test get_logger calls setup_logging if not configured."""
        import logging_config
        from logging_config import get_logger
        
        assert logging_config._configured == False
        
        logger = get_logger("test")
        
        assert logging_config._configured == True


class TestSetLevel:
    """Tests for set_level function."""
    
    def test_set_level_string(self, reset_logging):
        """Test set_level with string level."""
        from logging_config import setup_logging, set_level
        
        setup_logging(console=True, log_file=False)
        set_level("WARNING")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
    
    def test_set_level_int(self, reset_logging):
        """Test set_level with integer level."""
        from logging_config import setup_logging, set_level
        
        setup_logging(console=True, log_file=False)
        set_level(logging.DEBUG)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_set_level_updates_handlers(self, reset_logging):
        """Test set_level updates all handler levels."""
        from logging_config import setup_logging, set_level
        
        setup_logging(console=True, log_file=False)
        set_level("ERROR")
        
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            assert handler.level == logging.ERROR


class TestLogException:
    """Tests for log_exception function."""
    
    def test_log_exception_with_exc(self, reset_logging):
        """Test log_exception with exception object."""
        from logging_config import log_exception, get_logger
        
        logger = get_logger("test")
        mock_log = MagicMock()
        logger.log = mock_log
        
        exc = ValueError("test error")
        log_exception(logger, "Operation failed", exc)
        
        mock_log.assert_called_once()
        args = mock_log.call_args
        assert args[0][0] == logging.ERROR
        assert "Operation failed" in args[0][1]
        assert "ValueError" in args[0][1]
    
    def test_log_exception_without_exc(self, reset_logging):
        """Test log_exception without exception object (uses exc_info)."""
        from logging_config import log_exception, get_logger
        
        logger = get_logger("test")
        mock_log = MagicMock()
        logger.log = mock_log
        
        log_exception(logger, "Operation failed")
        
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert kwargs.get("exc_info") == True


class TestLogOperation:
    """Tests for log_operation function."""
    
    def test_log_operation_success(self, reset_logging):
        """Test log_operation for successful operation."""
        from logging_config import log_operation, get_logger
        
        logger = get_logger("test")
        mock_log = MagicMock()
        logger.log = mock_log
        
        log_operation(logger, "File save", success=True)
        
        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[0] == logging.INFO
        assert "File save" in args[1]
        assert "completed" in args[1]
    
    def test_log_operation_failure(self, reset_logging):
        """Test log_operation for failed operation."""
        from logging_config import log_operation, get_logger
        
        logger = get_logger("test")
        mock_log = MagicMock()
        logger.log = mock_log
        
        log_operation(logger, "Database query", success=False)
        
        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[0] == logging.ERROR
        assert "Database query" in args[1]
        assert "failed" in args[1]
    
    def test_log_operation_with_details(self, reset_logging):
        """Test log_operation with details dict."""
        from logging_config import log_operation, get_logger
        
        logger = get_logger("test")
        mock_log = MagicMock()
        logger.log = mock_log
        
        log_operation(
            logger,
            "API call",
            success=True,
            details={"status": 200, "duration": "50ms"}
        )
        
        args = mock_log.call_args[0]
        assert "status=200" in args[1]
        assert "duration=50ms" in args[1]
