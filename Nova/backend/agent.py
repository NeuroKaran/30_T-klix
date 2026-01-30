"""
Nova - Web Agent Adapter
Adapts Klix's AgentLoop for web/API access with streaming support.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

# Add parent directory to path to import Klix modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config, get_config
from llm_client import LLMClient, LLMResponse, Message, ToolDefinition, get_client
from mem_0 import MemoryService, get_memory_service
from tools import registry, execute_tool_call, get_tool_descriptions

# Handle imports for both module and direct execution
try:
    from .models import (
        ChatMessage,
        ChatResponse,
        Memory,
        MemoryType,
        StreamEvent,
        StreamEventType,
    )
except ImportError:
    from models import (
        ChatMessage,
        ChatResponse,
        Memory,
        MemoryType,
        StreamEvent,
        StreamEventType,
    )


# =============================================================================
# Web Agent
# =============================================================================

@dataclass
class WebAgent:
    """
    Web-adapted agent that wraps Klix's LLM client and tools.
    
    Designed for async API usage with streaming support.
    """
    
    config: Config = field(default_factory=get_config)
    _client: LLMClient | None = field(default=None, init=False)
    _memory_service: MemoryService | None = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)
    
    def __post_init__(self) -> None:
        """Initialize on first use."""
        pass
    
    async def initialize(self) -> None:
        """
        Initialize the agent services.
        Call this before using the agent.
        """
        if self._initialized:
            return
        
        # Initialize LLM client
        self._client = get_client(config=self.config)
        
        # Initialize memory service
        self._memory_service = get_memory_service(config=self.config)
        
        self._initialized = True
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.close()
        if self._memory_service:
            await self._memory_service.close()
        self._initialized = False
    
    @property
    def client(self) -> LLMClient:
        """Get the LLM client."""
        if not self._client:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        return self._client
    
    @property
    def memory_service(self) -> MemoryService:
        """Get the memory service."""
        if not self._memory_service:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        return self._memory_service
    
    def _build_system_message(self, memory_context: str = "") -> Message:
        """Build the system message with optional memory context."""
        base_instruction = self.client.system_instruction
        
        if memory_context:
            base_instruction += (
                f"\n\n## Your Memories About This User:\n{memory_context}\n\n"
                "Use these memories to provide personalized, context-aware assistance."
            )
        
        return Message(role="system", content=base_instruction)
    
    async def chat(
        self,
        user_input: str,
        history: list[ChatMessage] | None = None,
        user_id: str | None = None,
    ) -> ChatResponse:
        """
        Process a chat message and return the response.
        
        This is the non-streaming version for simple requests.
        
        Args:
            user_input: The user's message
            history: Previous messages in the conversation
            user_id: Optional user identifier for memory
            
        Returns:
            ChatResponse with the assistant's reply
        """
        await self.initialize()
        
        # Get memory context
        memory_context = ""
        if self.memory_service.is_enabled:
            memory_context = self.memory_service.get_memory_context(
                query=user_input,
                user_id=user_id or self.config.memory_user_id,
                max_memories=5,
            )
        
        # Build messages
        messages = [self._build_system_message(memory_context)]
        
        # Add history
        if history:
            for msg in history:
                messages.append(Message(
                    role=msg.role.value,
                    content=msg.content,
                    tool_calls=msg.tool_calls,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                ))
        
        # Add user message
        messages.append(Message(role="user", content=user_input))
        
        # Get tools
        tools = registry.get_tools_for_llm()
        
        # Get response
        response: LLMResponse = await self.client.chat(
            messages=messages,
            tools=tools,
            stream=False,
        )
        
        # Handle tool calls
        final_content = response.content
        if response.tool_calls:
            # Process tools
            for tc in response.tool_calls:
                result = execute_tool_call(tc)
                messages.append(Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                ))
                messages.append(Message(
                    role="tool",
                    content=result,
                    tool_call_id=tc.get("id", ""),
                    name=tc.get("name", ""),
                ))
            
            # Get follow-up
            follow_up: LLMResponse = await self.client.chat(
                messages=messages,
                tools=tools,
                stream=False,
            )
            final_content = follow_up.content
        
        # Extract and store memories
        if self.config.memory_auto_extract and self.memory_service.is_enabled:
            self.memory_service.extract_and_store(
                user_input=user_input,
                assistant_response=final_content,
                user_id=user_id or self.config.memory_user_id,
            )
        
        return ChatResponse(
            text=final_content,
            thread_id=str(uuid.uuid4()),  # Will be set by caller
            message_id=str(uuid.uuid4()),
            tool_calls=response.tool_calls,
        )
    
    async def chat_stream(
        self,
        user_input: str,
        history: list[ChatMessage] | None = None,
        user_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Process a chat message with streaming response.
        
        Yields StreamEvent objects for real-time updates.
        
        Args:
            user_input: The user's message
            history: Previous messages in the conversation
            user_id: Optional user identifier for memory
            
        Yields:
            StreamEvent for each update
        """
        await self.initialize()
        
        # Start thinking
        yield StreamEvent(type=StreamEventType.THINKING, content="Processing...")
        
        # Get memory context
        memory_context = ""
        if self.memory_service.is_enabled:
            memory_context = self.memory_service.get_memory_context(
                query=user_input,
                user_id=user_id or self.config.memory_user_id,
                max_memories=5,
            )
        
        # Build messages
        messages = [self._build_system_message(memory_context)]
        
        # Add history
        if history:
            for msg in history:
                messages.append(Message(
                    role=msg.role.value,
                    content=msg.content,
                    tool_calls=msg.tool_calls,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                ))
        
        # Add user message
        messages.append(Message(role="user", content=user_input))
        
        # Get tools
        tools = registry.get_tools_for_llm()
        
        try:
            # Get response (non-streaming for now, can be enhanced later)
            response: LLMResponse = await self.client.chat(
                messages=messages,
                tools=tools,
                stream=False,
            )
            
            # Handle tool calls
            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    tool_args = tc.get("arguments", {})
                    
                    # Emit tool call event
                    yield StreamEvent(
                        type=StreamEventType.TOOL_CALL,
                        content=f"Using {tool_name}...",
                        tool_name=tool_name,
                        tool_args=tool_args,
                    )
                    
                    # Execute tool
                    result = execute_tool_call(tc)
                    
                    # Emit tool result
                    yield StreamEvent(
                        type=StreamEventType.TOOL_RESULT,
                        content=result[:500] if len(result) > 500 else result,
                        tool_name=tool_name,
                    )
                    
                    # Add to messages
                    messages.append(Message(
                        role="assistant",
                        content=response.content,
                        tool_calls=response.tool_calls,
                    ))
                    messages.append(Message(
                        role="tool",
                        content=result,
                        tool_call_id=tc.get("id", ""),
                        name=tool_name,
                    ))
                
                # Get follow-up
                yield StreamEvent(type=StreamEventType.THINKING, content="Analyzing results...")
                
                follow_up: LLMResponse = await self.client.chat(
                    messages=messages,
                    tools=tools,
                    stream=False,
                )
                
                # Stream the response text
                yield StreamEvent(
                    type=StreamEventType.TEXT,
                    content=follow_up.content,
                )
                final_content = follow_up.content
            else:
                # Stream the response text
                yield StreamEvent(
                    type=StreamEventType.TEXT,
                    content=response.content,
                )
                final_content = response.content
            
            # Extract and store memories
            if self.config.memory_auto_extract and self.memory_service.is_enabled:
                self.memory_service.extract_and_store(
                    user_input=user_input,
                    assistant_response=final_content,
                    user_id=user_id or self.config.memory_user_id,
                )
            
            # Done
            yield StreamEvent(type=StreamEventType.DONE, content="")
            
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=str(e),
            )
    
    # =========================================================================
    # Memory Methods
    # =========================================================================
    
    def search_memories(
        self,
        query: str,
        user_id: str | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """Search memories by query."""
        if not self.memory_service.is_enabled:
            return []
        
        results = self.memory_service.search(
            query=query,
            user_id=user_id or self.config.memory_user_id,
            limit=limit,
        )
        
        return [
            Memory(
                id=m.id,
                content=m.content,
                memory_type=MemoryType(m.memory_type.value),
                created_at=m.created_at,
                metadata=m.metadata,
            )
            for m in results
        ]
    
    def get_all_memories(
        self,
        user_id: str | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """Get all memories for a user."""
        if not self.memory_service.is_enabled:
            return []
        
        results = self.memory_service.get_all(
            user_id=user_id or self.config.memory_user_id,
            limit=limit,
        )
        
        return [
            Memory(
                id=m.id,
                content=m.content,
                memory_type=MemoryType(m.memory_type.value),
                created_at=m.created_at,
                metadata=m.metadata,
            )
            for m in results
        ]
    
    def save_memory(
        self,
        text: str,
        user_id: str | None = None,
        memory_type: MemoryType = MemoryType.SEMANTIC,
    ) -> bool:
        """Save a text memory."""
        if not self.memory_service.is_enabled:
            return False
        
        from mem_0 import MemoryType as M0MemoryType
        return self.memory_service.add_text(
            text=text,
            user_id=user_id or self.config.memory_user_id,
            memory_type=M0MemoryType(memory_type.value),
        )
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        if not self.memory_service.is_enabled:
            return False
        return self.memory_service.delete(memory_id)
    
    def get_memory_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Get memory statistics."""
        if not self.memory_service.is_enabled:
            return {"enabled": False}
        
        stats = self.memory_service.get_stats(
            user_id=user_id or self.config.memory_user_id
        )
        stats["enabled"] = True
        return stats


# =============================================================================
# Global Agent Instance
# =============================================================================

_agent: WebAgent | None = None


def get_agent() -> WebAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        _agent = WebAgent()
    return _agent


async def init_agent() -> WebAgent:
    """Initialize and return the global agent."""
    agent = get_agent()
    await agent.initialize()
    return agent


async def close_agent() -> None:
    """Close the global agent."""
    global _agent
    if _agent:
        await _agent.close()
        _agent = None
