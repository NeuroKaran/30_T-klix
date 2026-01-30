
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from main import AgentLoop
from config import Config, ModelProvider
from llm_client import Message, LLMResponse

@pytest.mark.asyncio
async def test_memory_context_injection():
    """Test that memory context is retrieved and injected into the user message."""
    
    # Mock config
    mock_config = MagicMock(spec=Config)
    mock_config.memory_enabled = True
    mock_config.memory_user_id = "test_user"
    mock_config.memory_search_limit = 5
    mock_config.max_context_messages = 10
    mock_config.sliding_window_size = 5
    mock_config.default_provider = ModelProvider.GEMINI
    mock_config.memory_auto_extract = False
    mock_config.memory_auto_extract = False
    mock_config.user_name = "test_user"
    mock_config.org_name = "test_org"
    mock_config.project_root = "c:/test/project"
    mock_config.validate.return_value = []

    # Mock dependencies
    with patch('main.get_config', return_value=mock_config), \
         patch('main.create_tui') as mock_tui_factory, \
         patch('main.get_client') as mock_client_factory, \
         patch('main.get_memory_service') as mock_memory_factory, \
         patch('main.get_reasoning_logger') as mock_logger_factory:
        
        # Setup TUI mock
        mock_tui = MagicMock()
        mock_tui.state = MagicMock()
        mock_tui.show_thinking = AsyncMock()
        mock_tui_factory.return_value = mock_tui
        
        # Setup Client mock
        mock_client = AsyncMock()
        mock_client.system_instruction = "System prompt"
        mock_client.chat.return_value = LLMResponse(content="Response", usage={})
        mock_client_factory.return_value = mock_client
        
        # Setup Memory Service mock
        mock_memory_service = MagicMock()
        mock_memory_service.is_enabled = True
        # Make get_memory_context return a specific string that we look for
        mock_memory_service.get_memory_context.return_value = "RELEVANT_MEMORY_CONTEXT"
        mock_memory_factory.return_value = mock_memory_service

        # Initialize Agent
        agent = AgentLoop(config=mock_config)
        
        # Simulate chat
        user_input = "Hello test"
        await agent._chat(user_input)
        
        # Verify get_memory_context was called with user input
        mock_memory_service.get_memory_context.assert_called_with(
            query=user_input,
            user_id="test_user",
            max_memories=5
        )
        
        # Verify client.chat was called with the injected context
        call_args = mock_client.chat.call_args
        assert call_args is not None
        messages_arg = call_args[0][0] # First arg conforms to list[Message]
        
        # The last message should correspond to the user input
        last_message = messages_arg[-1]
        assert last_message.role == "user"
        
        # Check that the original content AND the memory context are present
        assert "Hello test" in last_message.content
        assert "RELEVANT_MEMORY_CONTEXT" in last_message.content
        assert "[MEMORY CONTEXT]" in last_message.content
