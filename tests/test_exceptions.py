"""
Tests for the exceptions module.
"""

import pytest
from exceptions import (
    KlixError,
    ToolError,
    ToolNotFoundError,
    ToolExecutionError,
    LLMError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
    MemoryServiceError,
    MemorySearchError,
    MemoryStorageError,
    ConfigError,
    ConfigValidationError,
    MissingConfigError,
    FileOperationError,
    FileNotFoundError_,
    FilePermissionError,
)


class TestKlixError:
    """Tests for the base KlixError class."""
    
    def test_basic_message(self):
        """Test error with just a message."""
        error = KlixError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}
        assert error.cause is None
    
    def test_with_details(self):
        """Test error with details dictionary."""
        error = KlixError("Failed", details={"code": 500, "retry": True})
        assert "code=500" in str(error)
        assert "retry=True" in str(error)
        assert error.details["code"] == 500
    
    def test_with_cause(self):
        """Test error with a cause exception."""
        original = ValueError("Original error")
        error = KlixError("Wrapper error", cause=original)
        assert error.cause is original
    
    def test_inheritance(self):
        """Test that KlixError is an Exception."""
        error = KlixError("Test")
        assert isinstance(error, Exception)


class TestToolErrors:
    """Tests for tool-related exceptions."""
    
    def test_tool_error_basic(self):
        """Test basic ToolError."""
        error = ToolError("Tool failed")
        assert str(error) == "Tool failed"
        assert error.tool_name is None
    
    def test_tool_error_with_name(self):
        """Test ToolError with tool name."""
        error = ToolError("Failed", tool_name="read_file")
        assert error.tool_name == "read_file"
        assert error.details["tool_name"] == "read_file"
    
    def test_tool_not_found_error(self):
        """Test ToolNotFoundError."""
        error = ToolNotFoundError("unknown_tool")
        assert "unknown_tool" in str(error)
        assert "not found" in str(error).lower()
        assert error.tool_name == "unknown_tool"
    
    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        error = ToolExecutionError("write_file", "Permission denied")
        assert "write_file" in str(error)
        assert "Permission denied" in str(error)
        assert error.tool_name == "write_file"


class TestLLMErrors:
    """Tests for LLM-related exceptions."""
    
    def test_llm_error_basic(self):
        """Test basic LLMError."""
        error = LLMError("API error")
        assert str(error) == "API error"
        assert error.provider is None
        assert error.model is None
    
    def test_llm_error_with_provider_and_model(self):
        """Test LLMError with provider and model."""
        error = LLMError("Failed", provider="gemini", model="gemini-2.5-flash")
        assert error.provider == "gemini"
        assert error.model == "gemini-2.5-flash"
        assert "provider=gemini" in str(error)
        assert "model=gemini-2.5-flash" in str(error)
    
    def test_llm_connection_error(self):
        """Test LLMConnectionError is LLMError subclass."""
        error = LLMConnectionError("Connection refused")
        assert isinstance(error, LLMError)
        assert isinstance(error, KlixError)
    
    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError with retry_after."""
        error = LLMRateLimitError(retry_after=30.0)
        assert error.retry_after == 30.0
        assert error.details["retry_after"] == 30.0
    
    def test_llm_rate_limit_error_default_message(self):
        """Test LLMRateLimitError default message."""
        error = LLMRateLimitError()
        assert "rate limit" in str(error).lower()
    
    def test_llm_response_error(self):
        """Test LLMResponseError is LLMError subclass."""
        error = LLMResponseError("Invalid response format")
        assert isinstance(error, LLMError)


class TestMemoryErrors:
    """Tests for memory service exceptions."""
    
    def test_memory_service_error_basic(self):
        """Test basic MemoryServiceError."""
        error = MemoryServiceError("Memory error")
        assert str(error) == "Memory error"
        assert error.operation is None
    
    def test_memory_service_error_with_operation(self):
        """Test MemoryServiceError with operation."""
        error = MemoryServiceError("Failed", operation="search")
        assert error.operation == "search"
        assert error.details["operation"] == "search"
    
    def test_memory_search_error(self):
        """Test MemorySearchError."""
        error = MemorySearchError("Query timeout")
        assert "search" in str(error).lower()
        assert "Query timeout" in str(error)
        assert error.operation == "search"
    
    def test_memory_storage_error(self):
        """Test MemoryStorageError."""
        error = MemoryStorageError("Disk full")
        assert "storage" in str(error).lower()
        assert "Disk full" in str(error)
        assert error.operation == "store"


class TestConfigErrors:
    """Tests for configuration exceptions."""
    
    def test_config_error_basic(self):
        """Test basic ConfigError."""
        error = ConfigError("Invalid config")
        assert str(error) == "Invalid config"
        assert error.config_key is None
    
    def test_config_error_with_key(self):
        """Test ConfigError with config key."""
        error = ConfigError("Invalid value", config_key="max_tokens")
        assert error.config_key == "max_tokens"
        assert error.details["config_key"] == "max_tokens"
    
    def test_config_validation_error(self):
        """Test ConfigValidationError is ConfigError subclass."""
        error = ConfigValidationError("Schema mismatch")
        assert isinstance(error, ConfigError)
        assert isinstance(error, KlixError)
    
    def test_missing_config_error(self):
        """Test MissingConfigError."""
        error = MissingConfigError("GOOGLE_API_KEY")
        assert "GOOGLE_API_KEY" in str(error)
        assert "missing" in str(error).lower()
        assert error.config_key == "GOOGLE_API_KEY"


class TestFileOperationErrors:
    """Tests for file operation exceptions."""
    
    def test_file_operation_error_basic(self):
        """Test basic FileOperationError."""
        error = FileOperationError("File error")
        assert error.tool_name == "file_operation"
        assert error.filepath is None
    
    def test_file_operation_error_with_path(self):
        """Test FileOperationError with filepath."""
        error = FileOperationError("Error", filepath="/path/to/file.txt")
        assert error.filepath == "/path/to/file.txt"
        assert error.details["filepath"] == "/path/to/file.txt"
    
    def test_file_not_found_error(self):
        """Test FileNotFoundError_ (custom)."""
        error = FileNotFoundError_("/missing/file.py")
        assert "/missing/file.py" in str(error)
        assert "not found" in str(error).lower()
        assert error.filepath == "/missing/file.py"
    
    def test_file_permission_error(self):
        """Test FilePermissionError."""
        error = FilePermissionError("/protected/file.txt", operation="write")
        assert "Permission denied" in str(error)
        assert "write" in str(error)
        assert "/protected/file.txt" in str(error)
    
    def test_file_permission_error_default_operation(self):
        """Test FilePermissionError with default operation."""
        error = FilePermissionError("/file.txt")
        assert "access" in str(error)


class TestExceptionHierarchy:
    """Tests for the exception inheritance hierarchy."""
    
    def test_all_inherit_from_klix_error(self):
        """Test that all custom exceptions inherit from KlixError."""
        exceptions = [
            ToolError("test"),
            ToolNotFoundError("test"),
            ToolExecutionError("test", "reason"),
            LLMError("test"),
            LLMConnectionError("test"),
            LLMRateLimitError(),
            LLMResponseError("test"),
            MemoryServiceError("test"),
            MemorySearchError("test"),
            MemoryStorageError("test"),
            ConfigError("test"),
            ConfigValidationError("test"),
            MissingConfigError("test"),
            FileOperationError("test"),
            FileNotFoundError_("test"),
            FilePermissionError("test"),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, KlixError), f"{type(exc).__name__} should inherit from KlixError"
            assert isinstance(exc, Exception), f"{type(exc).__name__} should be an Exception"
    
    def test_tool_errors_inherit_from_tool_error(self):
        """Test tool error inheritance."""
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)
        assert issubclass(FileOperationError, ToolError)
    
    def test_llm_errors_inherit_from_llm_error(self):
        """Test LLM error inheritance."""
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMResponseError, LLMError)
    
    def test_memory_errors_inherit_from_memory_service_error(self):
        """Test memory error inheritance."""
        assert issubclass(MemorySearchError, MemoryServiceError)
        assert issubclass(MemoryStorageError, MemoryServiceError)
    
    def test_config_errors_inherit_from_config_error(self):
        """Test config error inheritance."""
        assert issubclass(ConfigValidationError, ConfigError)
        assert issubclass(MissingConfigError, ConfigError)
