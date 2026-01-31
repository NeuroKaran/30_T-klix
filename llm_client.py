"""
Gemini Code - LLM Client Abstraction Layer
Provides abstract adapter pattern for Gemini and Ollama backends.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable

from google import genai
from google.genai import types
from google.genai import types
import ollama
import json

from config import Config, ModelProvider, get_config
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Message:
    """Represents a chat message."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None  # For tool responses


@dataclass
class ToolDefinition:
    """Definition of a tool for LLM function calling."""
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., str] | None = None
    
    def to_gemini_format(self) -> types.FunctionDeclaration:
        """Convert to Gemini function declaration format."""
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )
    
    def to_ollama_format(self) -> dict[str, Any]:
        """Convert to Ollama tools format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


@dataclass
class LLMResponse:
    """Standardized response from LLM."""
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: Any = None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self._system_instruction: str = ""
    
    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Send chat messages and get a response."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close any open connections or clients."""
        pass
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate a simple text response."""
        pass
    
    def set_system_instruction(self, instruction: str) -> None:
        """Set the system instruction for the model."""
        self._system_instruction = instruction
    
    @property
    def system_instruction(self) -> str:
        return self._system_instruction or self._default_system_instruction()
    
    def _default_system_instruction(self) -> str:
        """Default system instruction for Klix."""
        return """You are Klix, an expert AI coding assistant with persistent memory. You help developers with:
- Writing, debugging, and refactoring code
- Explaining complex concepts clearly
- Suggesting best practices and optimizations
- Navigating and understanding codebases

You have access to tools for file operations and web search.
CRITICAL: ONLY use tools when they are strictly necessary to answer the user's request.
If you can answer based on your knowledge or the provided memory context (which will be clearly marked), do so directly WITHOUT calling any tools.
NEVER call `read_file` or `ls` if you already have the necessary information in your memory context.
When you do use a tool, do not provide any explanation before the tool call.
Always be concise, accurate, and helpful. Format code with proper syntax highlighting.
When making changes to files, explain what you're doing and why.
You remember past conversations and user preferences - use this context to personalize your assistance."""


class GeminiClient(LLMClient):
    """Google Gemini API client using the new google-genai SDK."""
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        
        # Configure the Gemini client
        self.client = genai.Client(api_key=config.google_api_key)
        self.model_name = config.gemini_model
        
        # Safety settings - set to BLOCK_NONE for developer freedom
        self.safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="OFF",
            ),
        ]
    
    def _convert_messages_to_gemini(self, messages: list[Message]) -> list[types.Content]:
        """Convert messages to Gemini format."""
        gemini_messages = []
        
        for msg in messages:
            if msg.role == "system":
                continue  # System handled via system_instruction
            
            role = "user" if msg.role == "user" else "model"
            
            if msg.tool_calls:
                # Handle function calls
                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))
                for tc in msg.tool_calls:
                    parts.append(types.Part.from_function_call(
                        name=tc["name"],
                        args=tc.get("arguments", {}),
                    ))
                gemini_messages.append(types.Content(role=role, parts=parts))
            elif msg.role == "tool":
                # Tool response
                gemini_messages.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=msg.name,
                        response={"result": msg.content},
                    )]
                ))
            else:
                gemini_messages.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.content)]
                ))
        
        return gemini_messages
    
    def _create_tools_config(self, tools: list[ToolDefinition]) -> list[types.Tool]:
        """Create Gemini tools configuration."""
        if not tools:
            return []
        
        function_declarations = [tool.to_gemini_format() for tool in tools]
        return [types.Tool(function_declarations=function_declarations)]
    
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Send chat messages to Gemini."""
        logger.debug(f"Gemini chat: {len(messages)} messages, tools={bool(tools)}, stream={stream}")
        
        # Extract system instruction from messages (includes memory context)
        system_content = self.system_instruction
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
                break
        
        gemini_messages = self._convert_messages_to_gemini(messages)
        tools_config = self._create_tools_config(tools) if tools else None
        
        # Build generation config with the system content from messages
        generate_config = types.GenerateContentConfig(
            system_instruction=system_content,
            safety_settings=self.safety_settings,
            tools=tools_config,
        )
        
        if stream:
            return self._stream_response(gemini_messages, generate_config)
        
        # Non-streaming response
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=gemini_messages,
                config=generate_config,
            )
            logger.debug(f"Gemini response received, parsing...")
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise

    async def close(self) -> None:
        """Close the Gemini client."""
        # The genai client doesn't have an explicit close in the current version,
        # but we provide the interface for future-proofing.
        logger.debug("Closing Gemini client")
        pass
    
    async def _stream_response(
        self,
        messages: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> AsyncGenerator[str, None]:
        """Stream response from Gemini."""
        response_stream = await asyncio.to_thread(
            self.client.models.generate_content_stream,
            model=self.model_name,
            contents=messages,
            config=config,
        )
        
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse Gemini response to standardized format."""
        content = ""
        tool_calls = []
        
        if response.candidates:
            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    content += part.text
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_calls.append({
                        "id": f"call_{fc.name}",
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    })
        
        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(um, "prompt_token_count", 0),
                "completion_tokens": getattr(um, "candidates_token_count", 0),
                "total_tokens": getattr(um, "total_token_count", 0),
            }
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
            usage=usage,
            raw_response=response,
        )
    
    async def generate(self, prompt: str) -> str:
        """Generate a simple text response."""
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                safety_settings=self.safety_settings,
            ),
        )
        return response.text if response.text else ""


class OllamaClient(LLMClient):
    """Ollama local LLM client."""
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.client = ollama.Client(host=config.ollama_host)
        self.model_name = config.ollama_model
    
    def _convert_messages_to_ollama(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert messages to Ollama format."""
        ollama_messages = []
        
        # Extract system message from the passed messages (includes memory context)
        system_content = self.system_instruction
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
                break
        
        # Add system message with memory context
        if system_content:
            ollama_messages.append({
                "role": "system",
                "content": system_content,
            })
        
        for msg in messages:
            if msg.role == "system":
                continue  # Already handled above
            
            message_dict: dict[str, Any] = {
                "role": msg.role if msg.role != "tool" else "tool",
                "content": msg.content,
            }
            
            if msg.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc.get("arguments", {}),
                        }
                    }
                    for tc in msg.tool_calls
                ]
            
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            
            ollama_messages.append(message_dict)
        
        return ollama_messages
    
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Send chat messages to Ollama."""
        
        ollama_messages = self._convert_messages_to_ollama(messages)
        ollama_tools = [tool.to_ollama_format() for tool in tools] if tools else None
        
        if stream:
            return self._stream_response(ollama_messages, ollama_tools)
        
        # Non-streaming response
        response = await asyncio.to_thread(
            self.client.chat,
            model=self.model_name,
            messages=ollama_messages,
            tools=ollama_tools,
        )
        
        return self._parse_response(response)

    async def close(self) -> None:
        """Close the Ollama client."""
        logger.debug("Closing Ollama client")
        pass
    
    async def _stream_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama."""
        stream = await asyncio.to_thread(
            self.client.chat,
            model=self.model_name,
            messages=messages,
            tools=tools,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.get("message", {}).get("content"):
                yield chunk["message"]["content"]
    
    def _parse_response(self, response: dict[str, Any]) -> LLMResponse:
        """Parse Ollama response to standardized format."""
        message = response.get("message", {})
        content = message.get("content", "")
        
        tool_calls = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                tool_calls.append({
                    "id": tc.get("id", f"call_{func.get('name', 'unknown')}"),
                    "name": func.get("name", ""),
                    "arguments": func.get("arguments", {}),
                })
        
        if not tool_calls:
            # More robust JSON extraction for models that wrap it in backticks or include text
            import re
            
            def find_balanced_json(text):
                """Find first valid JSON object in text by balancing braces."""
                start_idx = text.find('{')
                if start_idx == -1:
                    return None, None
                
                stack = 0
                for i in range(start_idx, len(text)):
                    if text[i] == '{':
                        stack += 1
                    elif text[i] == '}':
                        stack -= 1
                        if stack == 0:
                            # Found a balanced block
                            json_str = text[start_idx:i+1]
                            return json_str, (start_idx, i+1)
                return None, None

            # Try to find JSON in markdown blocks first
            json_str = None
            full_match_text = None
            
            # Simple check for markdown block first
            md_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if md_match:
                json_str, _ = find_balanced_json(md_match.group(1))
                if json_str:
                    full_match_text = md_match.group(0)
            
            if not json_str:
                # Try anywhere in the content
                json_str, span = find_balanced_json(content)
                if json_str:
                    full_match_text = json_str

            if json_str:
                try:
                    parsed = json.loads(json_str)
                    candidates = [parsed] if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
                    
                    extracted_calls = []
                    is_fake_tool_call = False
                    
                    for candidate in candidates:
                        if isinstance(candidate, dict) and "name" in candidate and "arguments" in candidate:
                            tool_name = candidate['name']
                            tool_args = candidate['arguments']
                            
                            # Handle fake tool calls where model wraps response in JSON
                            # e.g., {"name":"None","arguments":{"message":"Hello!"}} or {"name":"none","arguments":{}}
                            if tool_name in ("None", "none", None, ""):
                                is_fake_tool_call = True
                                # Extract the actual message from arguments if present
                                if isinstance(tool_args, dict) and tool_args:
                                    # Try common keys for the message content
                                    actual_message = (
                                        tool_args.get("message") or 
                                        tool_args.get("response") or 
                                        tool_args.get("content") or
                                        tool_args.get("text") or
                                        ""
                                    )
                                    if actual_message:
                                        # Replace JSON with the extracted message
                                        content = content.replace(full_match_text, actual_message).strip()
                                    else:
                                        # Empty arguments - just strip the JSON
                                        content = content.replace(full_match_text, "").strip()
                                else:
                                    # No arguments or empty dict - strip the JSON
                                    content = content.replace(full_match_text, "").strip()
                                continue  # Don't add as a tool call
                            
                            extracted_calls.append({
                                "id": f"call_{tool_name}",
                                "name": tool_name,
                                "arguments": tool_args,
                            })
                    
                    if extracted_calls:
                        from tools import registry
                        valid_tools = [t.name for t in registry.list_tools()]
                        filtered_calls = [tc for tc in extracted_calls if tc["name"] in valid_tools]
                        
                        if filtered_calls:
                            tool_calls = filtered_calls
                            # If we extracted JSON, remove the specific block from content.
                            content = content.replace(full_match_text, "").strip()
                        else:
                            # Model tried to call invalid tools - try to extract message from args
                            for ec in extracted_calls:
                                args = ec.get("arguments", {})
                                if isinstance(args, dict):
                                    actual_message = (
                                        args.get("message") or 
                                        args.get("response") or 
                                        args.get("content") or
                                        args.get("text") or
                                        ""
                                    )
                                    if actual_message:
                                        content = content.replace(full_match_text, actual_message).strip()
                                        break
                            else:
                                # No message found - just strip the invalid JSON
                                content = content.replace(full_match_text, "").strip()
                    
                    # If we had a fake tool call and content is now empty, provide a fallback
                    if is_fake_tool_call and not content.strip():
                        content = "Hello! How can I help you today?"
                        
                except json.JSONDecodeError:
                    pass

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
            usage={
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0),
                "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
            },
            raw_response=response,
        )
    
    async def generate(self, prompt: str) -> str:
        """Generate a simple text response."""
        response = await asyncio.to_thread(
            self.client.generate,
            model=self.model_name,
            prompt=f"{self.system_instruction}\n\n{prompt}" if self.system_instruction else prompt,
        )
        return response.get("response", "")


def get_client(provider: ModelProvider | str | None = None, config: Config | None = None) -> LLMClient:
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        provider: The provider to use (gemini or ollama). If None, uses config default.
        config: Configuration object. If None, uses global config.
    
    Returns:
        An instance of the appropriate LLM client.
    """
    config = config or get_config()
    
    if provider is None:
        provider = config.default_provider
    elif isinstance(provider, str):
        provider = ModelProvider(provider.lower())
    
    if provider == ModelProvider.GEMINI:
        return GeminiClient(config)
    else:
        return OllamaClient(config)


def get_gemini_client(config: Config | None = None) -> GeminiClient:
    """Get a Gemini client instance."""
    return GeminiClient(config or get_config())


def get_ollama_client(config: Config | None = None) -> OllamaClient:
    """Get an Ollama client instance."""
    return OllamaClient(config or get_config())
