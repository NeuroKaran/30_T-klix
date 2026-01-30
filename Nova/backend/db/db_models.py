"""
Nova - SQLAlchemy Database Models
Thread and Message storage for conversation persistence.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Handle imports for both module and direct execution
try:
    from .database import Base
except ImportError:
    from database import Base


# =============================================================================
# Helper Functions
# =============================================================================

def generate_uuid() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


# =============================================================================
# Thread Model
# =============================================================================

class ThreadModel(Base):
    """
    Conversation thread.
    
    A thread contains multiple messages and tracks metadata
    like title, timestamps, and memory associations.
    """
    
    __tablename__ = "threads"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    title: Mapped[str] = mapped_column(
        String(255), 
        default="New Conversation"
    )
    user_id: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(), 
        onupdate=func.now()
    )
    
    # Relationships
    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at"
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": len(self.messages) if self.messages else 0,
        }


# =============================================================================
# Message Model
# =============================================================================

class MessageModel(Base):
    """
    Individual message in a thread.
    
    Stores the role (user/assistant/system/tool), content,
    and any tool call information.
    """
    
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    thread_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("threads.id", ondelete="CASCADE"),
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(20),  # user, assistant, system, tool
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    tool_calls: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    tool_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now()
    )
    
    # Relationships
    thread: Mapped["ThreadModel"] = relationship(
        "ThreadModel",
        back_populates="messages"
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
