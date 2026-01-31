"""
Nemo Core - Real-time AI Companion Backend
Core modules for memory, LLM, and text-to-speech.
"""

from .llm import GeminiClient, LLMResponse, get_gemini_client
from .tts import TextToSpeech

__all__ = [
    "GeminiClient",
    "get_gemini_client",
    "LLMResponse",
    "TextToSpeech",
]
