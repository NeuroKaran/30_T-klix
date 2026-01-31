"""
Nemo - Real-time AI Companion Backend
FastAPI + WebSocket server for low-latency voice conversations.

Architecture:
- WebSocket endpoint for real-time bidirectional communication
- Memory injection for personalized context
- Background memory saving for zero-latency responses
- Edge-TTS streaming for voice synthesis
"""

from __future__ import annotations

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import sys
from pathlib import Path

# Add project root to path to allow importing shared modules
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.append(project_root)

# Import core services
from core.memory import NemoMemoryService, get_nemo_memory_service  # Use Nemo's own memory
from core.llm import GeminiClient, get_gemini_client
from core.tts import TextToSpeech, get_tts_service, VOICE_OPTIONS

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Configuration
# =============================================================================

class AppConfig:
    """Application configuration."""
    APP_NAME = "Nemo"
    VERSION = "1.0.0"
    DESCRIPTION = "Real-time AI Companion Backend"
    
    # CORS settings for frontend
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # WebSocket settings
    WS_HEARTBEAT_INTERVAL = 30  # seconds


# =============================================================================
# Request/Response Models
# =============================================================================

class TextMessage(BaseModel):
    """Text message request model."""
    text: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""
    text: str
    audio: str | None = None
    visemes: list[Any] = []
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    services: dict[str, bool]


class MemoryRequest(BaseModel):
    """Request to save a memory."""
    text: str
    user_id: str | None = None


# =============================================================================
# Service Initialization
# =============================================================================

# Global service instances
memory_service: NemoMemoryService | None = None
llm_client: GeminiClient | None = None
tts_service: TextToSpeech | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global memory_service, llm_client, tts_service
    
    logger.info("🚀 Starting Nemo services...")
    
    # Initialize services
    memory_service = get_nemo_memory_service()
    llm_client = get_gemini_client()
    tts_service = get_tts_service()
    
    # Log service status
    logger.info(f"🧠 Memory: {'✓ Enabled' if memory_service and memory_service.is_enabled else '✗ Disabled'}")
    logger.info(f"⚡ LLM: {'✓ Ready' if llm_client and llm_client.is_ready else '✗ Not Ready'}")
    if tts_service:
        logger.info(f"🔊 TTS: Initialized with voice {tts_service.voice}")
    else:
        logger.warning("🔊 TTS: Not Initialized")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down Nemo services...")
    if memory_service:
        await memory_service.close()
    if llm_client:
        await llm_client.close()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title=AppConfig.APP_NAME,
    description=AppConfig.DESCRIPTION,
    version=AppConfig.VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API info."""
    return {
        "name": AppConfig.APP_NAME,
        "version": AppConfig.VERSION,
        "description": AppConfig.DESCRIPTION,
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "websocket": "/talk",
            "voices": "/voices"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=AppConfig.VERSION,
        services={
            "memory": memory_service.is_enabled if memory_service else False,
            "llm": llm_client.is_ready if llm_client else False,
            "tts": tts_service is not None
        }
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: TextMessage):
    """
    REST endpoint for chat (alternative to WebSocket).
    Includes text response and optional audio.
    """
    if not llm_client or not llm_client.is_ready:
        raise HTTPException(status_code=503, detail="LLM service not available")
    
    user_text = message.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message")
    
    # Get memory context
    past_context = ""
    if memory_service and memory_service.is_enabled:
        past_context = memory_service.get_memory_context(user_text, user_id=message.user_id)
        if past_context:
            logger.info(f"🧠 Recalled context for request")
    
    # Build system prompt with memory
    # Use request user_id or fall back to configured default
    target_user = message.user_id or AppConfig.APP_NAME  # Fallback to AppName if no user? Better to use configured ID.
    # Actually, let's use the same logic as memory service default or just pass what we have
    # The MemoryService has a default user_id. 
    # Let's get the default from environment if message.user_id is None
    effective_user_id = message.user_id or os.getenv("NEMO_USER_ID", "Friend")
    
    system_prompt = build_system_prompt(past_context, user_id=effective_user_id)
    
    # Generate response
    response = await llm_client.generate_async(user_text, system_prompt)
    response_text = response.content
    
    # Generate audio
    audio_base64 = ""
    if tts_service and response_text:
        audio_base64 = await tts_service.synthesize(response_text)
    
    # Save to memory (background task)
    if memory_service and memory_service.is_enabled:
        asyncio.create_task(
            async_save_memory(user_text, response_text, message.user_id)
        )
    
    return ChatResponse(
        text=response_text,
        audio=audio_base64 if audio_base64 else None,
        visemes=[],
        timestamp=datetime.now().isoformat()
    )


@app.get("/voices")
async def list_voices():
    """List available TTS voices."""
    voices = await TextToSpeech.list_voices("en")
    return {
        "presets": VOICE_OPTIONS,
        "all_voices": voices[:20]  # Limit to first 20
    }


@app.post("/memory")
async def save_memory(request: MemoryRequest):
    """Explicitly save a memory."""
    if not memory_service or not memory_service.is_enabled:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    success = memory_service.add_text(request.text, user_id=request.user_id)
    return {"success": success}


@app.delete("/memory")
async def clear_memory(user_id: str | None = None):
    """Clear all memories for a user."""
    if not memory_service or not memory_service.is_enabled:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    success = memory_service.delete_all(user_id)
    return {"success": success}


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@app.websocket("/talk")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for voice conversations.
    
    Protocol:
    - Client sends: {"text": "user message", "user_id": "optional"}
    - Server responds: {"audio": "base64", "text": "response", "visemes": []}
    """
    await websocket.accept()
    logger.info("🔌 WebSocket client connected")
    
    try:
        while True:
            # 1. Receive message from client
            data = await websocket.receive_json()
            user_text = data.get('text', '').strip()
            user_id = data.get('user_id')
            
            if not user_text:
                await websocket.send_json({
                    "error": "Empty message",
                    "text": "",
                    "audio": ""
                })
                continue
            
            logger.info(f"📥 Received: {user_text[:50]}...")
            
            # 2. Retrieve Memory Context (The "Context Injection")
            past_context = ""
            if memory_service and memory_service.is_enabled:
                past_context = memory_service.get_memory_context(user_text, user_id=user_id)
                if past_context:
                    logger.info(f"🧠 Recalled memories:\n{past_context}")
            
            # 3. Construct System Prompt with Memory
            effective_user_id = user_id or os.getenv("NEMO_USER_ID", "Friend")
            system_prompt = build_system_prompt(past_context, user_id=effective_user_id)
            
            # 4. Generate Response (Groq - ultra fast!)
            if llm_client and llm_client.is_ready:
                response = await llm_client.generate_async(user_text, system_prompt)
                response_text = response.content
            else:
                response_text = "I'm having trouble thinking right now. Give me a sec?"
            
            logger.info(f"📤 Response: {response_text[:50]}...")
            
            # 5. Stream Audio (Edge-TTS) & Send to Client
            audio_base64 = ""
            if tts_service and response_text:
                audio_base64 = await tts_service.synthesize(response_text)
            
            # Send response to client
            await websocket.send_json({
                "audio": audio_base64,
                "text": response_text,
                "visemes": []  # Optional: for lip sync
            })
            
            # 6. Save to Memory (Async - NON-BLOCKING)
            # This ensures the user doesn't wait for the DB write
            if memory_service and memory_service.is_enabled:
                asyncio.create_task(
                    async_save_memory(user_text, response_text, user_id)
                )
    
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "error": str(e),
                "text": "Oops, something went wrong!",
                "audio": ""
            })
        except:
            pass


# =============================================================================
# Helper Functions
# =============================================================================

def build_system_prompt(memory_context: str = "", user_id: str = "Friend") -> str:
    """
    Build the system prompt for Nemo with optional memory context.
    
    Args:
        memory_context: Formatted string of relevant memories
        user_id: The name/ID of the user interacting with Nemo
        
    Returns:
        Complete system prompt
    """
    base_prompt = f"""You are Nemo, a sassy and empathetic friend. You are talking to {user_id}.

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
- Use casual language ("hey", "omg", "no way", "ugh")
- Ask follow-up questions to show interest
- Remember personal details the user shares"""

    if memory_context:
        return f"""{base_prompt}

RELEVANT MEMORIES (Use these to personalize the chat):
{memory_context}

Use these memories naturally in conversation - don't explicitly mention you're using memory."""
    
    return base_prompt


async def async_save_memory(
    user_text: str, 
    agent_text: str, 
    user_id: str | None = None
) -> None:
    """
    Save conversation to memory asynchronously.
    
    This runs in the background after the response is sent,
    ensuring zero added latency for the user.
    """
    if memory_service and memory_service.is_enabled:
        logger.info("💾 Saving memory in background...")
        # Use extract_and_store which mimics the interaction saving logic
        memory_service.extract_and_store(user_text, agent_text, user_id=user_id)
    else:
        logger.debug("💾 Memory disabled, skipping background save.")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting Nemo on {host}:{port}")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
