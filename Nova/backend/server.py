"""
Nova - FastAPI Server
Main API server that wraps Klix's backend for web access.

Endpoints:
- POST /api/chat - Send a message
- GET /api/status - System status
- GET /api/threads - List threads
- POST /api/threads - Create thread
- GET /api/memories - List/search memories
- POST /api/memories - Save memory
- WS /ws - WebSocket for real-time streaming
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path to import Klix modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Handle imports for both module and direct execution
try:
    from .agent import WebAgent, get_agent, init_agent, close_agent
    from .models import (
        ChatRequest,
        ChatResponse,
        ErrorResponse,
        Memory,
        MemoryList,
        MemoryRequest,
        MemorySearchRequest,
        MemoryType,
        ServiceStatus,
        StatusResponse,
        StreamEvent,
        StreamEventType,
        Thread,
        ThreadCreate,
        ThreadList,
        ChatMessage,
        MessageRole,
    )
    from .db.database import get_db, init_db, close_db
    from .db.db_models import ThreadModel, MessageModel
except ImportError:
    from agent import WebAgent, get_agent, init_agent, close_agent
    from models import (
        ChatRequest,
        ChatResponse,
        ErrorResponse,
        Memory,
        MemoryList,
        MemoryRequest,
        MemorySearchRequest,
        MemoryType,
        ServiceStatus,
        StatusResponse,
        StreamEvent,
        StreamEventType,
        Thread,
        ThreadCreate,
        ThreadList,
        ChatMessage,
        MessageRole,
    )
    from db.database import get_db, init_db, close_db
    from db.db_models import ThreadModel, MessageModel

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class ServerConfig:
    """Server configuration."""
    APP_NAME = "Nova"
    VERSION = "0.1.0"
    DESCRIPTION = "AI Assistant Web Interface - Powered by Klix"
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    WS_HEARTBEAT_INTERVAL = 30


# Track server start time
_start_time = time.time()


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    logger.info(f"🚀 Starting {ServerConfig.APP_NAME} v{ServerConfig.VERSION}")
    
    # Initialize database
    await init_db()
    logger.info("✓ Database initialized")
    
    # Initialize agent
    await init_agent()
    logger.info("✓ Agent initialized")
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")
    await close_agent()
    await close_db()
    logger.info("Goodbye! 👋")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title=ServerConfig.APP_NAME,
    version=ServerConfig.VERSION,
    description=ServerConfig.DESCRIPTION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ServerConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": ServerConfig.APP_NAME,
        "version": ServerConfig.VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get system status."""
    agent = get_agent()
    
    # Build service status
    services = []
    
    # LLM service
    services.append(ServiceStatus(
        name="LLM",
        enabled=agent._client is not None,
        details=f"{agent.config.default_provider.value}: {agent.config.current_model}"
    ))
    
    # Memory service
    memory_enabled = agent._memory_service is not None and agent._memory_service.is_enabled
    services.append(ServiceStatus(
        name="Memory (Mem0)",
        enabled=memory_enabled,
        details="Connected" if memory_enabled else "Disabled"
    ))
    
    return StatusResponse(
        status="ok",
        version=ServerConfig.VERSION,
        model=agent.config.current_model,
        provider=agent.config.default_provider.value,
        services=services,
        uptime_seconds=time.time() - _start_time,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a chat message and get a response.
    
    For streaming responses, use the WebSocket endpoint instead.
    """
    agent = get_agent()
    
    # Get or create thread
    thread_id = request.thread_id
    if not thread_id:
        # Create new thread
        thread = ThreadModel(
            title=request.text[:50] + "..." if len(request.text) > 50 else request.text,
            user_id=request.user_id,
        )
        db.add(thread)
        await db.flush()
        thread_id = thread.id
    else:
        # Verify thread exists
        result = await db.execute(
            select(ThreadModel).where(ThreadModel.id == thread_id)
        )
        thread = result.scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get message history
    result = await db.execute(
        select(MessageModel)
        .where(MessageModel.thread_id == thread_id)
        .order_by(MessageModel.created_at)
    )
    db_messages = result.scalars().all()
    
    history = [
        ChatMessage(
            role=MessageRole(m.role),
            content=m.content,
            tool_calls=m.tool_calls or [],
            tool_call_id=m.tool_call_id,
            name=m.tool_name,
        )
        for m in db_messages
    ]
    
    # Save user message
    user_msg = MessageModel(
        thread_id=thread_id,
        role="user",
        content=request.text,
    )
    db.add(user_msg)
    
    # Get response from agent
    response = await agent.chat(
        user_input=request.text,
        history=history,
        user_id=request.user_id,
    )
    
    # Save assistant message
    assistant_msg = MessageModel(
        thread_id=thread_id,
        role="assistant",
        content=response.text,
        tool_calls=response.tool_calls if response.tool_calls else None,
    )
    db.add(assistant_msg)
    
    # Update response with correct IDs
    response.thread_id = thread_id
    response.message_id = assistant_msg.id
    
    await db.commit()
    
    return response


# =============================================================================
# Thread Endpoints
# =============================================================================

@app.get("/api/threads", response_model=ThreadList)
async def list_threads(
    user_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List conversation threads."""
    query = select(ThreadModel).order_by(ThreadModel.updated_at.desc())
    
    if user_id:
        query = query.where(ThreadModel.user_id == user_id)
    
    # Get total count
    count_query = select(func.count()).select_from(ThreadModel)
    if user_id:
        count_query = count_query.where(ThreadModel.user_id == user_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get threads
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    db_threads = result.scalars().all()
    
    threads = [
        Thread(
            id=t.id,
            title=t.title,
            created_at=t.created_at,
            updated_at=t.updated_at,
            message_count=len(t.messages) if t.messages else 0,
            user_id=t.user_id,
        )
        for t in db_threads
    ]
    
    return ThreadList(threads=threads, total=total)


@app.post("/api/threads", response_model=Thread)
async def create_thread(
    request: ThreadCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new thread."""
    thread = ThreadModel(
        title=request.title or "New Conversation",
        user_id=request.user_id,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    
    return Thread(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        user_id=thread.user_id,
    )


@app.get("/api/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a thread with its messages."""
    result = await db.execute(
        select(ThreadModel).where(ThreadModel.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get messages
    result = await db.execute(
        select(MessageModel)
        .where(MessageModel.thread_id == thread_id)
        .order_by(MessageModel.created_at)
    )
    messages = result.scalars().all()
    
    return {
        "thread": Thread(
            id=thread.id,
            title=thread.title,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            message_count=len(messages),
            user_id=thread.user_id,
        ),
        "messages": [m.to_dict() for m in messages],
    }


@app.delete("/api/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a thread."""
    result = await db.execute(
        select(ThreadModel).where(ThreadModel.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    await db.delete(thread)
    await db.commit()
    
    return {"status": "deleted", "thread_id": thread_id}


# =============================================================================
# Memory Endpoints
# =============================================================================

@app.get("/api/memories", response_model=MemoryList)
async def list_memories(
    user_id: str | None = None,
    limit: int = 20,
):
    """List all memories for a user."""
    agent = get_agent()
    memories = agent.get_all_memories(user_id=user_id, limit=limit)
    return MemoryList(memories=memories, total=len(memories))


@app.post("/api/memories/search", response_model=MemoryList)
async def search_memories(request: MemorySearchRequest):
    """Search memories by query."""
    agent = get_agent()
    memories = agent.search_memories(
        query=request.query,
        user_id=request.user_id,
        limit=request.limit,
    )
    return MemoryList(memories=memories, total=len(memories))


@app.post("/api/memories")
async def save_memory(request: MemoryRequest):
    """Save a new memory."""
    agent = get_agent()
    success = agent.save_memory(
        text=request.text,
        user_id=request.user_id,
        memory_type=request.memory_type,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save memory")
    
    return {"status": "saved"}


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory."""
    agent = get_agent()
    success = agent.delete_memory(memory_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memory")
    
    return {"status": "deleted", "memory_id": memory_id}


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for streaming conversations.
    
    Protocol:
    - Client sends: {"text": "message", "thread_id": "optional", "user_id": "optional"}
    - Server sends: StreamEvent objects as JSON
    """
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                request = json.loads(data)
                text = request.get("text", "")
                thread_id = request.get("thread_id")
                user_id = request.get("user_id")
                
                if not text:
                    await websocket.send_json({
                        "type": "error",
                        "content": "No text provided"
                    })
                    continue
                
                # Get agent
                agent = get_agent()
                
                # Stream response
                async for event in agent.chat_stream(
                    user_input=text,
                    history=None,  # TODO: Load from thread_id
                    user_id=user_id,
                ):
                    await websocket.send_json({
                        "type": event.type.value,
                        "content": event.content,
                        "tool_name": event.tool_name,
                        "tool_args": event.tool_args,
                        "timestamp": event.timestamp.isoformat(),
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON"
                })
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": str(e)
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"🚀 Starting Nova on {host}:{port}")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
