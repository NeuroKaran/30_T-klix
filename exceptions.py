"""
Klix - Custom Exception Hierarchy
Provides domain-specific exceptions for better error handling and debugging.
"""

from __future__ import annotations

from typing import Any


class KlixError(Exception):
    """
    Base exception for all Klix errors.
    
    Provides a consistent interface for error handling across the application.
    """
    
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# =============================================================================
# Tool Errors
# =============================================================================

class ToolError(KlixError):
    """Errors from tool execution."""
    
    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        if tool_name:
            self.details["tool_name"] = tool_name


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered."""
    
    def __init__(self, tool_name: str, **kwargs: Any) -> None:
        super().__init__(
            f"Tool '{tool_name}' not found",
            tool_name=tool_name,
            **kwargs,
        )


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""
    
    def __init__(
        self,
        tool_name: str,
        reason: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            f"Tool '{tool_name}' failed: {reason}",
            tool_name=tool_name,
            **kwargs,
        )


# =============================================================================
# LLM Errors
# =============================================================================

class LLMError(KlixError):
    """Base error for LLM API operations."""
    
    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.provider = provider
        self.model = model
        if provider:
            self.details["provider"] = provider
        if model:
            self.details["model"] = model


class LLMConnectionError(LLMError):
    """Raised when connection to LLM API fails."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


class LLMResponseError(LLMError):
    """Raised when LLM response is invalid or unexpected."""
    pass


# =============================================================================
# Memory Errors
# =============================================================================

class MemoryServiceError(KlixError):
    """Base error for memory service operations."""
    
    def __init__(
        self,
        message: str,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.operation = operation
        if operation:
            self.details["operation"] = operation


class MemorySearchError(MemoryServiceError):
    """Raised when memory search fails."""
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(
            f"Memory search failed: {reason}",
            operation="search",
            **kwargs,
        )


class MemoryStorageError(MemoryServiceError):
    """Raised when storing memory fails."""
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(
            f"Memory storage failed: {reason}",
            operation="store",
            **kwargs,
        )


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigError(KlixError):
    """Configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.config_key = config_key
        if config_key:
            self.details["config_key"] = config_key


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""
    pass


class MissingConfigError(ConfigError):
    """Raised when required configuration is missing."""
    
    def __init__(self, config_key: str, **kwargs: Any) -> None:
        super().__init__(
            f"Required configuration missing: {config_key}",
            config_key=config_key,
            **kwargs,
        )


# =============================================================================
# File Operation Errors
# =============================================================================

class FileOperationError(ToolError):
    """Errors from file operations."""
    
    def __init__(
        self,
        message: str,
        filepath: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, tool_name="file_operation", **kwargs)
        self.filepath = filepath
        if filepath:
            self.details["filepath"] = filepath


class FileNotFoundError_(FileOperationError):
    """Raised when a file is not found (custom, to avoid shadowing builtin)."""
    
    def __init__(self, filepath: str, **kwargs: Any) -> None:
        super().__init__(
            f"File not found: {filepath}",
            filepath=filepath,
            **kwargs,
        )


class FilePermissionError(FileOperationError):
    """Raised when file permission is denied."""
    
    def __init__(self, filepath: str, operation: str = "access", **kwargs: Any) -> None:
        super().__init__(
            f"Permission denied to {operation} '{filepath}'",
            filepath=filepath,
            **kwargs,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base
    "KlixError",
    # Tool errors
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    # LLM errors
    "LLMError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMResponseError",
    # Memory errors
    "MemoryServiceError",
    "MemorySearchError",
    "MemoryStorageError",
    # Config errors
    "ConfigError",
    "ConfigValidationError",
    "MissingConfigError",
    # File errors
    "FileOperationError",
    "FileNotFoundError_",
    "FilePermissionError",
]
