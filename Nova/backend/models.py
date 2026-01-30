"""
Nova - Pydantic Models for API
Request/Response schemas for the REST API.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class MessageRole(str, Enum):
    """Message role in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MemoryType(str, Enum):
    """Type of memory stored."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class StreamEventType(str, Enum):
    """Types of streaming events."""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    DONE = "done"
    ERROR = "error"


# =============================================================================
# Chat Models
# =============================================================================

class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    text: str
    thread_id: str | None = None
    user_id: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from a chat request."""
    text: str
    thread_id: str
    message_id: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamEvent(BaseModel):
    """Real-time streaming event."""
    type: StreamEventType
    content: str = ""
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Thread Models
# =============================================================================

class Thread(BaseModel):
    """A conversation thread."""
    id: str
    title: str = "New Conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    memory_count: int = 0
    user_id: str | None = None


class ThreadCreate(BaseModel):
    """Request to create a new thread."""
    title: str | None = None
    user_id: str | None = None


class ThreadList(BaseModel):
    """List of threads."""
    threads: list[Thread]
    total: int


# =============================================================================
# Memory Models
# =============================================================================

class Memory(BaseModel):
    """A stored memory."""
    id: str
    content: str
    memory_type: MemoryType = MemoryType.EPISODIC
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRequest(BaseModel):
    """Request to save a memory."""
    text: str
    user_id: str | None = None
    memory_type: MemoryType = MemoryType.SEMANTIC


class MemorySearchRequest(BaseModel):
    """Request to search memories."""
    query: str
    user_id: str | None = None
    limit: int = 10


class MemoryList(BaseModel):
    """List of memories."""
    memories: list[Memory]
    total: int


# =============================================================================
# Status Models
# =============================================================================

class ServiceStatus(BaseModel):
    """Status of a service."""
    name: str
    enabled: bool
    details: str = ""


class StatusResponse(BaseModel):
    """System status response."""
    status: str = "ok"
    version: str = "0.1.0"
    model: str = ""
    provider: str = ""
    services: list[ServiceStatus] = Field(default_factory=list)
    uptime_seconds: float = 0


# =============================================================================
# Error Models
# =============================================================================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: str | None = None
    code: str | None = None
