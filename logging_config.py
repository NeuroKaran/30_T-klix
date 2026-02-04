"""
Klix - Logging Configuration
Centralized logging setup with console and file handlers.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


# =============================================================================
# Custom Formatter with Colors
# =============================================================================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    DIM = "\033[2m"
    
    def __init__(self, fmt: str | None = None, use_colors: bool = True) -> None:
        super().__init__(fmt)
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        # Save original values
        original_levelname = record.levelname
        original_msg = record.msg
        
        if self.use_colors:
            color = self.COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            
            # Dim the timestamp and logger name
            record.name = f"{self.DIM}{record.name}{self.RESET}"
        
        result = super().format(record)
        
        # Restore original values
        record.levelname = original_levelname
        record.msg = original_msg
        
        return result


# =============================================================================
# Logger Configuration
# =============================================================================

# Default log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_FORMAT_SIMPLE = "%(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global state
_configured = False
_log_dir: Path | None = None


def get_log_dir() -> Path:
    """Get the log directory path."""
    global _log_dir
    if _log_dir is None:
        _log_dir = Path.home() / ".klix" / "logs"
    return _log_dir


def set_log_dir(path: Path | str) -> None:
    """Set a custom log directory path."""
    global _log_dir
    _log_dir = Path(path)


def setup_logging(
    level: str | int | None = None,
    log_file: bool = True,
    console: bool = True,
    log_format: str = LOG_FORMAT,
    verbose: bool = False,
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to LOG_LEVEL env var or INFO.
        log_file: Whether to enable file logging.
        console: Whether to enable console logging.
        log_format: Format string for log messages.
        verbose: If True, sets level to DEBUG (unless level is explicit).
    """
    global _configured
    
    if _configured:
        return
    
    # Determine log level
    if level is None:
        if verbose:
            level = logging.DEBUG
        else:
            level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    if isinstance(level, str):
        level = getattr(logging, level, logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(log_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_dir = get_log_dir()
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "klix.log"
            
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(log_format, datefmt=DATE_FORMAT)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # If we can't create log file, just warn and continue
            if console:
                root_logger.warning(f"Could not create log file: {e}")
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Usage:
        from logging_config import get_logger
        logger = get_logger(__name__)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message", exc_info=True)
    """
    # Ensure logging is configured
    if not _configured:
        setup_logging()
    
    return logging.getLogger(name)


def set_level(level: str | int) -> None:
    """Change the log level at runtime."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    for handler in root_logger.handlers:
        handler.setLevel(level)


# =============================================================================
# Convenience Functions
# =============================================================================

def log_exception(
    logger: logging.Logger,
    message: str,
    exc: Exception | None = None,
    level: int = logging.ERROR,
) -> None:
    """
    Log an exception with consistent formatting.
    
    Args:
        logger: Logger instance
        message: Description of what failed
        exc: The exception (if not using exc_info=True)
        level: Log level
    """
    if exc:
        logger.log(level, f"{message}: {type(exc).__name__}: {exc}")
    else:
        logger.log(level, message, exc_info=True)


def log_operation(
    logger: logging.Logger,
    operation: str,
    success: bool,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log an operation result.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        success: Whether it succeeded
        details: Additional details
    """
    status = "completed" if success else "failed"
    level = logging.INFO if success else logging.ERROR
    
    if details:
        details_str = ", ".join(f"{k}={v}" for k, v in details.items())
        logger.log(level, f"{operation} {status}: {details_str}")
    else:
        logger.log(level, f"{operation} {status}")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "setup_logging",
    "get_logger",
    "set_level",
    "set_log_dir",
    "get_log_dir",
    "log_exception",
    "log_operation",
    "ColoredFormatter",
]
