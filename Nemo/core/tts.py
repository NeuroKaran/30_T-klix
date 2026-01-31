"""
Nemo - Text-to-Speech using Edge-TTS
High-quality, free TTS synthesis using Microsoft Edge's neural voices.
Optimized for low-latency real-time conversations.
"""

from __future__ import annotations

import os
import base64
import logging
import asyncio
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

import edge_tts
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Available voices for Shanaya
# Using Indian English voices for authentic feel
VOICE_OPTIONS = {
    # Female Indian English voices
    "shanaya_default": "en-IN-NeerjaNeural",  # Natural, warm
    "shanaya_expressive": "en-IN-NeerjaExpressiveNeural",  # More emotional
    
    # Female US English alternatives
    "aria": "en-US-AriaNeural",
    "jenny": "en-US-JennyNeural",
    "michelle": "en-US-MichelleNeural",
    
    # Female UK English
    "sonia": "en-GB-SoniaNeural",
    "libby": "en-GB-LibbyNeural",
    
    # Female Australian English
    "natasha": "en-AU-NatashaNeural",
}


@dataclass
class TTSResult:
    """Result of TTS synthesis."""
    audio_base64: str
    audio_bytes: bytes
    duration_ms: int = 0
    voice_used: str = ""
    text_length: int = 0


@dataclass
class TextToSpeech:
    """
    Edge-TTS wrapper for high-quality neural text-to-speech.
    
    Uses Microsoft Edge's online TTS service which provides:
    - High-quality neural voices
    - Multiple languages and accents
    - Free to use (no API key needed!)
    - Fast synthesis times
    
    Key Features:
    - Base64 audio output for WebSocket streaming
    - Configurable voice selection
    - Speech rate and pitch adjustment
    - SSML support for advanced control
    """
    
    # Configuration
    voice: str = field(default_factory=lambda: os.getenv("TTS_VOICE", "en-IN-NeerjaExpressiveNeural"))
    rate: str = field(default="+0%")  # Speed: -50% to +100%
    pitch: str = field(default="+0Hz")  # Pitch adjustment
    volume: str = field(default="+0%")  # Volume adjustment
    
    def __post_init__(self) -> None:
        """Initialize TTS configuration."""
        logger.info(f"🔊 TTS initialized with voice: {self.voice}")
    
    async def synthesize(self, text: str) -> str:
        """
        Synthesize text to speech and return as base64 audio.
        
        This is the main method for real-time voice synthesis.
        Returns MP3 audio encoded in base64 for easy WebSocket transmission.
        
        Args:
            text: The text to convert to speech
            
        Returns:
            Base64-encoded MP3 audio string
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return ""
        
        try:
            # Create the communicate object
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume
            )
            
            # Collect audio chunks
            audio_buffer = BytesIO()
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])
            
            # Convert to base64
            audio_bytes = audio_buffer.getvalue()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            logger.info(f"🔊 Synthesized {len(text)} chars -> {len(audio_bytes)} bytes")
            
            return audio_base64
            
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return ""
    
    async def synthesize_full(self, text: str) -> TTSResult:
        """
        Synthesize text with full result details.
        
        Args:
            text: The text to convert to speech
            
        Returns:
            TTSResult with audio and metadata
        """
        if not text or not text.strip():
            return TTSResult(
                audio_base64="",
                audio_bytes=b"",
                text_length=0,
                voice_used=self.voice
            )
        
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume
            )
            
            audio_buffer = BytesIO()
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])
            
            audio_bytes = audio_buffer.getvalue()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return TTSResult(
                audio_base64=audio_base64,
                audio_bytes=audio_bytes,
                text_length=len(text),
                voice_used=self.voice
            )
            
        except Exception as e:
            logger.error(f"Full TTS synthesis error: {e}")
            return TTSResult(
                audio_base64="",
                audio_bytes=b"",
                text_length=len(text),
                voice_used=self.voice
            )
    
    async def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """
        Synthesize text directly to an MP3 file.
        
        Args:
            text: The text to convert
            output_path: Path to save the MP3 file
            
        Returns:
            True if successful
        """
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume
            )
            
            await communicate.save(output_path)
            logger.info(f"🔊 Audio saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return False
    
    def set_voice(self, voice_name: str) -> None:
        """
        Change the TTS voice.
        
        Args:
            voice_name: Either a preset name (from VOICE_OPTIONS) or full voice ID
        """
        if voice_name in VOICE_OPTIONS:
            self.voice = VOICE_OPTIONS[voice_name]
        else:
            self.voice = voice_name
        logger.info(f"🔊 Voice changed to: {self.voice}")
    
    def set_rate(self, rate_percent: int) -> None:
        """
        Set speech rate.
        
        Args:
            rate_percent: -50 to +100 (0 is normal speed)
        """
        rate_percent = max(-50, min(100, rate_percent))
        self.rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"
    
    def set_pitch(self, pitch_hz: int) -> None:
        """
        Set pitch adjustment.
        
        Args:
            pitch_hz: Pitch shift in Hz (e.g., +50 for higher, -50 for lower)
        """
        self.pitch = f"+{pitch_hz}Hz" if pitch_hz >= 0 else f"{pitch_hz}Hz"
    
    @staticmethod
    async def list_voices(language_filter: str = "en") -> list[dict[str, str]]:
        """
        List available voices, optionally filtered by language.
        
        Args:
            language_filter: Language code prefix (e.g., "en" for English)
            
        Returns:
            List of voice information dicts
        """
        try:
            voices = await edge_tts.list_voices()
            
            if language_filter:
                voices = [
                    v for v in voices 
                    if v.get("Locale", "").lower().startswith(language_filter.lower())
                ]
            
            return [
                {
                    "name": v.get("ShortName", ""),
                    "locale": v.get("Locale", ""),
                    "gender": v.get("Gender", ""),
                    "friendly_name": v.get("FriendlyName", "")
                }
                for v in voices
            ]
            
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []


# =============================================================================
# Module-level singleton
# =============================================================================

_tts_service: TextToSpeech | None = None


def get_tts_service() -> TextToSpeech:
    """Get or create the global TTS service instance."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TextToSpeech()
    return _tts_service


def init_tts_service(
    voice: str | None = None,
    rate: str | None = None
) -> TextToSpeech:
    """
    Initialize TTS service with custom configuration.
    
    Args:
        voice: Voice name or ID
        rate: Speech rate (e.g., "+10%")
        
    Returns:
        Configured TextToSpeech instance
    """
    global _tts_service
    
    kwargs = {}
    if voice:
        kwargs['voice'] = voice if voice not in VOICE_OPTIONS else VOICE_OPTIONS[voice]
    if rate:
        kwargs['rate'] = rate
    
    _tts_service = TextToSpeech(**kwargs)
    return _tts_service
