
import pytest
import json
from unittest.mock import MagicMock
from llm_client import OllamaClient, Message, ToolDefinition
from config import Config

@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.ollama_host = "http://localhost:11434"
    config.ollama_model = "qwen2.5-coder:3b"
    return config

@pytest.fixture
def client(mock_config):
    return OllamaClient(mock_config)

def test_parse_response_normal_text(client):
    """Test that normal text is not parsed as a tool call."""
    response = {
        "message": {
            "content": "Hello! How can I help you today?",
            "role": "assistant"
        }
    }
    parsed = client._parse_response(response)
    assert parsed.content == "Hello! How can I help you today?"
    assert parsed.tool_calls == []

def test_parse_response_json_but_not_tool(client):
    """Test that JSON that is not a tool call is kept as content."""
    json_content = json.dumps({"status": "ok", "message": "Operation completed"})
    response = {
        "message": {
            "content": json_content,
            "role": "assistant"
        }
    }
    parsed = client._parse_response(response)
    # Current behavior might try to parse this if it had 'name' and 'arguments'
    # But this one doesn't, so it should be fine.
    assert parsed.content == json_content
    assert parsed.tool_calls == []

def test_parse_response_aggressive_json_extraction_fix(client):
    """
    Test that the aggressive JSON extraction is tempered.
    This test verifies that only valid tools in the registry are parsed.
    """
    from tools import registry, Tool, ToolParameter
    
    # Register a temporary test tool
    @registry.register("test_tool", "A test tool", [ToolParameter("arg1", "string", "an argument")])
    def test_tool(arg1: str) -> str:
        return f"result: {arg1}"
    
    # Case 1: JSON for a non-existent tool
    json_content_invalid = json.dumps({"name": "non_existent_tool", "arguments": {"foo": "bar"}})
    response_invalid = {
        "message": {
            "content": json_content_invalid,
            "role": "assistant"
        }
    }
    parsed_invalid = client._parse_response(response_invalid)
    assert parsed_invalid.tool_calls == []
    assert parsed_invalid.content == json_content_invalid

    # Case 2: JSON for a VALID tool
    json_content_valid = json.dumps({"name": "test_tool", "arguments": {"arg1": "hello"}})
    response_valid = {
        "message": {
            "content": json_content_valid,
            "role": "assistant"
        }
    }
    parsed_valid = client._parse_response(response_valid)
    assert len(parsed_valid.tool_calls) == 1
    assert parsed_valid.tool_calls[0]["name"] == "test_tool"
    assert parsed_valid.tool_calls[0]["arguments"] == {"arg1": "hello"}
    assert parsed_valid.content == ""

    if "test_tool" in registry._tools:
        del registry._tools["test_tool"]

def test_parse_response_markdown_json(client):
    """Test that JSON wrapped in markdown backticks is correctly parsed."""
    from tools import registry, Tool, ToolParameter
    
    # Register a temporary test tool
    if "test_tool_md" not in registry._tools:
        @registry.register("test_tool_md", "A test tool", [ToolParameter("arg1", "string", "an argument")])
        def test_tool_md(arg1: str) -> str:
            return f"result: {arg1}"
    
    content = "Here is the tool call you requested:\n\n```json\n{\"name\": \"test_tool_md\", \"arguments\": {\"arg1\": \"hello\"}}\n```\n\nHope this helps!"
    response = {
        "message": {
            "content": content,
            "role": "assistant"
        }
    }
    parsed = client._parse_response(response)
    
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0]["name"] == "test_tool_md"
    assert parsed.tool_calls[0]["arguments"] == {"arg1": "hello"}
    # Content should have the JSON block removed
    assert "Here is the tool call you requested:" in parsed.content
    assert "Hope this helps!" in parsed.content
    assert "```json" not in parsed.content

    # Clean up
    if "test_tool_md" in registry._tools:
        del registry._tools["test_tool_md"]

