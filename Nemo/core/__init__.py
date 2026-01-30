"""
Nemo Core - Real-time AI Companion Backend
Core modules for memory, LLM, and text-to-speech.
"""

from .llm import GroqClient, LLMResponse
from .tts import TextToSpeech

__all__ = [
    "GroqClient",
    "LLMResponse",
    "TextToSpeech",
]
