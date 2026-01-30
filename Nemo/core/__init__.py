"""
Nemo Core - Real-time AI Companion Backend
Core modules for memory, LLM, and text-to-speech.
"""

from .memory import MemoryService, get_memory_service
from .llm import GroqClient, LLMResponse
from .tts import TextToSpeech

__all__ = [
    "MemoryService",
    "get_memory_service",
    "GroqClient",
    "LLMResponse",
    "TextToSpeech",
]
