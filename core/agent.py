"""
Klix Core - Agent Logic (The Soul)
Decoupled agent logic that processes inputs and emits events/responses.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Callable

from config import Config, get_config
from llm_client import LLMClient, LLMResponse, Message, get_client
from logging_config import get_logger
from mem_0 import MemoryService, get_memory_service
from reasoning_logger import get_reasoning_logger, ReasoningLogger

# Import from core modules
from core.tools import execute_tool_call, registry
from core.session import Session
from core.project_context import ProjectContext, get_project_context
from core.approval import ApprovalManager, get_approval_manager, RiskLevel

logger = get_logger(__name__)


class KlixAgent:
    """
    The 'Soul' of the agent.
    Manages the reasoning loop, tool execution, and memory integration.
    Decoupled from the UI/Runtime.
    """
    
    def __init__(
        self,
        config: Config | None = None,
        session: Session | None = None,
    ) -> None:
        self.config = config or get_config()
        self.session = session or Session(
            max_messages=self.config.max_context_messages,
            sliding_window_size=self.config.sliding_window_size
        )
        
        # Core components
        self.client: LLMClient = get_client(config=self.config)
        self.memory_service: MemoryService = get_memory_service(config=self.config)
        self.reasoning_logger: ReasoningLogger = get_reasoning_logger(config=self.config)
        self.project_context: ProjectContext = get_project_context(self.config.project_root)
        self.approval_manager: ApprovalManager = get_approval_manager()
        
        # Initialize logging session
        self.reasoning_logger.start_session(metadata={
            "user": self.config.user_name,
            "project": str(self.config.project_root),
            "session_id": self.session.id
        })
        
        # Initialization
        self._initialize_system_message()
    
    def _initialize_system_message(self) -> None:
        """Initialize the system prompt with project context and memory."""
        # Start with base system instruction
        system_content = self.client.system_instruction
        
        # Inject project context from KLIX.md files
        project_context = self.project_context.get_system_prompt_injection()
        if project_context:
            system_content += f"\n\n{project_context}"
            logger.info(f"Loaded project context: {self.project_context.get_summary()}")
        
        # Get persistent memory context
        memory_context = ""
        if self.memory_service.is_enabled:
            memory_context = self.memory_service.get_memory_context(
                query="user preferences and recent context",
                user_id=self.config.memory_user_id,
                max_memories=self.config.memory_search_limit,
            )
        
        # Add memory context
        if memory_context:
            system_content += f"\n\n## Your Memories About This User:\n{memory_context}\n\nUse these memories to provide personalized, context-aware assistance."
        
        system_msg = Message(role="system", content=system_content)
        self.session.add_message(system_msg)
    
    def reload_project_context(self) -> str:
        """Reload project context from KLIX.md files and reinitialize system prompt."""
        self.project_context.reload()
        
        # Clear existing system messages and reinitialize
        self.session.messages = [m for m in self.session.messages if m.role != "system"]
        self._initialize_system_message()
        
        return self.project_context.get_summary()
    
    def _is_trivial_query(self, user_input: str) -> bool:
        """Check if query is trivial (skip memory search/tools)."""
        normalized = user_input.strip().lower()
        
        trivial_patterns = {
            "hello", "hi", "hey", "hola", "greetings",
            "thanks", "thank you", "thx", "ty",
            "bye", "goodbye", "ok", "okay", "sure",
            "what's up", "sup", "how are you"
        }
        
        if normalized in trivial_patterns:
            return True
        
        if len(normalized) < 5:
            return True
            
        return False

    async def step(self, user_input: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Execute a single turn of the agent loop.
        Yields events: {type: str, data: Any}
        Types: 'thinking', 'response', 'tool_call', 'tool_result', 'error'
        """
        try:
            # 1. Add user message
            user_msg = Message(role="user", content=user_input)
            self.session.add_message(user_msg)
            self.reasoning_logger.log_user_message(user_input)
            
            # Check for compaction
            if len(self.session.messages) > self.session.max_messages:
                yield {"type": "thinking", "data": "Compacting conversation history..."}
                await self.session.compact_history(self.client)
            
            is_trivial = self._is_trivial_query(user_input)
            
            # 2. Prepare Context (Memory Search)
            yield {"type": "thinking", "data": "Checking memories..."}
            
            memory_context = ""
            if self.memory_service.is_enabled and not is_trivial:
                memory_context = self.memory_service.get_memory_context(
                    query=user_input,
                    user_id=self.config.memory_user_id,
                    max_memories=self.config.memory_search_limit,
                )
            
            # 3. Prepare Messages for LLM
            current_messages = self.session.get_messages()
            if memory_context and current_messages and current_messages[-1].role == "user":
                # Inject memory context into the last user message for the LLM call only
                last_msg = current_messages[-1]
                enhanced_content = f"{last_msg.content}\n\n[MEMORY CONTEXT]\n{memory_context}\n[/MEMORY CONTEXT]"
                current_messages = current_messages[:-1] + [Message(role="user", content=enhanced_content)]
            
            # 4. LLM Call
            tools = None if is_trivial else registry.get_tools_for_llm()
            
            yield {"type": "thinking", "data": "Reasoning..."}
            
            response: LLMResponse = await self.client.chat(
                current_messages,
                tools=tools,
                stream=False
            )
            
            # Log and update usage
            self.reasoning_logger.log_llm_response(
                content=response.content,
                tool_calls=response.tool_calls,
                usage=response.usage
            )
            if response.usage:
                self.session.update_token_usage(response.usage)
            
            # 5. Handle Response & Tools
            if response.tool_calls:
                # Add assistant message with tool calls
                assistant_msg = Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls
                )
                self.session.add_message(assistant_msg)
                
                # Emit tool call events
                for tc in response.tool_calls:
                    yield {"type": "tool_call", "data": tc}
                
                # Execute tools
                yield {"type": "thinking", "data": "Executing tools..."}
                
                tool_responses = []
                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_id = tc.get("id", f"call_{tool_name}")
                    tool_args = tc.get("arguments", {})
                    
                    # Check if approval is needed
                    needs_approval, risk_level, reason = self.approval_manager.needs_approval(
                        tool_name, tool_args
                    )
                    
                    if needs_approval:
                        # Emit approval request event
                        yield {
                            "type": "approval_needed",
                            "data": {
                                "name": tool_name,
                                "arguments": tool_args,
                                "risk_level": risk_level.value,
                                "reason": reason,
                            }
                        }
                        # For now, continue with execution (TUI will handle approval)
                        # In full implementation, this would await approval
                    
                    # Execute
                    result = execute_tool_call(tc)
                    
                    # Log and store result
                    self.reasoning_logger.log_tool_result(tool_name, tool_args, result)
                    yield {"type": "tool_result", "data": {"name": tool_name, "result": result}}
                    
                    tool_responses.append(Message(
                        role="tool",
                        content=result,
                        tool_call_id=tool_id,
                        name=tool_name
                    ))
                
                # Add tool responses to history
                for tr in tool_responses:
                    self.session.add_message(tr)
                
                # Follow-up LLM call
                yield {"type": "thinking", "data": "Synthesizing results..."}
                
                follow_up: LLMResponse = await self.client.chat(
                    self.session.get_messages(),
                    tools=tools,
                    stream=False
                )
                
                # Log follow-up
                self.reasoning_logger.log_llm_response(
                    content=follow_up.content,
                    tool_calls=follow_up.tool_calls,
                    usage=follow_up.usage
                )
                
                if follow_up.content:
                    self.session.add_message(Message(role="assistant", content=follow_up.content))
                    yield {"type": "response", "data": follow_up.content}
                    
            else:
                # Direct response
                if response.content:
                    self.session.add_message(Message(role="assistant", content=response.content))
                    yield {"type": "response", "data": response.content}

            # 6. Auto-Extract Memories
            if self.config.memory_auto_extract and self.memory_service.is_enabled:
                msgs = self.session.get_messages()
                last_assistant = next((m for m in reversed(msgs) if m.role == "assistant"), None)
                if last_assistant and last_assistant.content:
                     self.memory_service.extract_and_store(
                        user_input=user_input,
                        assistant_response=last_assistant.content,
                        user_id=self.config.memory_user_id,
                    )

        except Exception as e:
            logger.error(f"Agent step error: {e}", exc_info=True)
            yield {"type": "error", "data": str(e)}

    async def close(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.close()
        if self.memory_service:
            await self.memory_service.close()
