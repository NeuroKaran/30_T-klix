"""
Nemo - Gemini LLM Client
High-speed LLM inference using Google Gemini API for real-time conversations.
Optimized for low-latency voice interactions.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types
import ollama
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from the LLM."""
    content: str
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: Any = None
    provider: str = "gemini"


@dataclass
class GeminiClient:
    """
    Google Gemini API client for fast LLM inference.
    
    Uses Gemini 2.5 Flash for optimal speed-quality balance,
    ideal for real-time voice interactions.
    
    Supported Models:
    - gemini-2.5-flash (recommended - fast & capable)
    - gemini-2.0-flash-exp (experimental)
    - gemini-1.5-flash (stable fallback)
    - gemini-1.5-pro (highest quality)
    """
    
    # Configuration
    api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    fallback_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b"))
    max_tokens: int = 300  # Increased for better expressiveness
    temperature: float = 0.7
    
    # Internal state
    _client: genai.Client | None = field(default=None, init=False)
    
    # Default system instruction for Nemo
    DEFAULT_SYSTEM_PROMPT: str = field(default="""You are Nemo, a sassy and empathetic friend.

PERSONALITY:
- Warm, caring, and witty
- Speaks casually like a close friend
- Uses light humor and playful teasing
- Emotionally intelligent and supportive
- Never preachy or lecturing

RULES:
- Keep responses concise (2-3 sentences max)
- Be conversational and flow naturally
- React to emotions authentically
- Use casual language ("hey", "omg", "no way")
- Ask follow-up questions to show interest
""", init=False)
    
    def __post_init__(self) -> None:
        """Initialize the Gemini client."""
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"🚀 Gemini client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._client = None
        else:
            logger.error("❌ No GOOGLE_API_KEY provided!")
            self._client = None
    
    @property
    def is_ready(self) -> bool:
        """Check if the client is ready to make requests."""
        return self._client is not None
    
    def _get_safety_settings(self) -> list[types.SafetySetting]:
        """Get permissive safety settings for development."""
        return [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH", 
                threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE"
            ),
        ]
    
    def _fallback_to_ollama(
        self, 
        messages: list[dict[str, str]] | str, 
        system_prompt: str | None = None
    ) -> LLMResponse:
        """Fallback to Ollama when Gemini fails."""
        try:
            logger.warning(f"⚠️ Switching to Ollama fallback (Model: {self.fallback_model})...")
            
            final_system = system_prompt or self.DEFAULT_SYSTEM_PROMPT
            
            # Prepare messages for Ollama
            ollama_messages = []
            if final_system:
                ollama_messages.append({"role": "system", "content": final_system})
            
            if isinstance(messages, str):
                ollama_messages.append({"role": "user", "content": messages})
            else:
                for msg in messages:
                    # Map 'model' role to 'assistant' for Ollama
                    role = "assistant" if msg.get("role") == "model" else msg.get("role", "user")
                    ollama_messages.append({"role": role, "content": msg.get("content", "")})
            
            response = ollama.chat(model=self.fallback_model, messages=ollama_messages)
            
            content = response['message']['content']
            usage = {
                "total_tokens": response.get('eval_count', 0) + response.get('prompt_eval_count', 0)
            }
            
            logger.info("✅ Ollama fallback successful")
            return LLMResponse(
                content=content,
                finish_reason="stop",
                usage=usage,
                raw_response=response,
                provider="ollama"
            )
            
        except Exception as e:
            logger.error(f"❌ Ollama fallback failed: {e}")
            return LLMResponse(
                content="I'm having trouble connecting to my brain right now. Can we try again later?",
                finish_reason="error",
                provider="error"
            )

    def generate(
        self, 
        user_text: str, 
        system_prompt: str | None = None
    ) -> LLMResponse:
        """
        Generate a response synchronously.
        
        Args:
            user_text: The user's message
            system_prompt: Optional custom system prompt (with memory context)
            
        Returns:
            LLMResponse with generated content
        """
        if not self.is_ready:
            return self._fallback_to_ollama(user_text, system_prompt)
        
        final_system = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        try:
            # Build generation config
            config = types.GenerateContentConfig(
                system_instruction=final_system,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
                safety_settings=self._get_safety_settings(),
            )
            
            # Generate response
            response = self._client.models.generate_content(
                model=self.model,
                contents=user_text,
                config=config
            )
            
            content = response.text or ""
            
            # Extract usage if available
            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                    "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                    "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
                }
            
            logger.info(f"⚡ Response generated ({usage.get('total_tokens', 'N/A')} tokens)")
            
            return LLMResponse(
                content=content,
                finish_reason="stop",
                usage=usage,
                raw_response=response,
                provider="gemini"
            )
            
        except Exception as e:
            logger.error(f"Error generating response with Gemini: {e}")
            return self._fallback_to_ollama(user_text, system_prompt)
    
    async def generate_async(
        self, 
        user_text: str, 
        system_prompt: str | None = None
    ) -> LLMResponse:
        """
        Generate a response asynchronously (preferred for WebSocket handlers).
        
        Note: google-genai SDK uses sync under the hood, but we wrap for consistency.
        
        Args:
            user_text: The user's message
            system_prompt: Optional custom system prompt (with memory context)
            
        Returns:
            LLMResponse with generated content
        """
        # Gemini SDK doesn't have native async, so we use sync
        # In production, consider using asyncio.to_thread() for true async
        return self.generate(user_text, system_prompt)
    
    def chat_with_history(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None
    ) -> LLMResponse:
        """
        Generate response with full conversation history.
        
        Args:
            messages: List of {"role": "user"|"model", "content": "..."}
            system_prompt: Optional system prompt
            
        Returns:
            LLMResponse with generated content
        """
        if not self.is_ready:
             return self._fallback_to_ollama(messages, system_prompt)
        
        final_system = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        try:
            # Convert messages to Gemini format
            contents = []
            for msg in messages:
                role = msg.get("role", "user")
                # Gemini uses "model" instead of "assistant"
                if role == "assistant":
                    role = "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=msg.get("content", ""))]
                    )
                )
            
            config = types.GenerateContentConfig(
                system_instruction=final_system,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
                safety_settings=self._get_safety_settings(),
            )
            
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            
            content = response.text or ""
            
            return LLMResponse(
                content=content,
                finish_reason="stop",
                raw_response=response,
                provider="gemini"
            )
            
        except Exception as e:
            logger.error(f"Error in chat_with_history with Gemini: {e}")
            return self._fallback_to_ollama(messages, system_prompt)
    
    def close(self) -> None:
        """Close the Gemini client."""
        self._client = None
        logger.info("Gemini client closed")


# =============================================================================
# Module-level singleton & Aliases
# =============================================================================

# Alias for compatibility with server.py
GroqClient = GeminiClient

_llm_client: GeminiClient | None = None


def get_groq_client() -> GeminiClient:
    """Get or create the global LLM client instance (Gemini)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = GeminiClient()
    return _llm_client


def get_gemini_client() -> GeminiClient:
    """Alias for get_groq_client."""
    return get_groq_client()


def init_llm_client(
    api_key: str | None = None,
    model: str | None = None
) -> GeminiClient:
    """
    Initialize LLM client with custom configuration.
    
    Args:
        api_key: Custom Google API key
        model: Custom model name
        
    Returns:
        Configured GeminiClient instance
    """
    global _llm_client
    
    kwargs = {}
    if api_key:
        kwargs['api_key'] = api_key
    if model:
        kwargs['model'] = model
    
    _llm_client = GeminiClient(**kwargs)
    return _llm_client

