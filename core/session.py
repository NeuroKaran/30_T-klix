"""
Klix Core - Session Management
Manages the active runtime state, conversation history, and ephemeral context.
Now includes persistence for save/resume functionality.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from llm_client import Message

# Default sessions directory (relative to project root)
DEFAULT_SESSIONS_DIR = ".klix_sessions"


@dataclass
class Session:
    """
    Represents an active agent session.
    Manages the sliding window of conversation history in memory.
    Supports persistence for save/resume functionality.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""  # Optional human-readable name
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Configuration for sliding window
    max_messages: int = 50
    sliding_window_size: int = 20
    total_tokens_used: int = 0
    
    # Class-level sessions directory
    sessions_dir: ClassVar[Path] = Path(DEFAULT_SESSIONS_DIR)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the session history."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    async def compact_history(self, client: Any) -> None:
        """
        Compact the session history by summarizing older messages.
        Triggered when message count exceeds max_messages.
        """
        if len(self.messages) <= self.max_messages:
            return
            
        # Strategy: Keep system prompt + last N messages. Summarize the middle.
        system_msgs = [m for m in self.messages if m.role == "system"]
        recent_msgs = self.messages[-self.sliding_window_size:]
        
        # Messages to summarize (everything in between)
        # Filter out system messages from the middle chunk to avoid duplicating them
        middle_msgs = [
            m for m in self.messages 
            if m not in system_msgs and m not in recent_msgs
        ]
        
        if not middle_msgs:
            self.messages = system_msgs + recent_msgs
            return
            
        # Generate summary
        try:
            conversation_text = "\n".join([f"{m.role}: {m.content}" for m in middle_msgs])
            summary_prompt = (
                f"Summarize the following conversation events concisely to preserve context:\n\n{conversation_text}"
            )
            
            summary = await client.generate(summary_prompt)
            
            summary_msg = Message(
                role="system",
                content=f"[Previous Context Summary]: {summary}"
            )
            
            # Reconstruct: System + Summary + Recent
            self.messages = system_msgs + [summary_msg] + recent_msgs
            
        except Exception as e:
            # Fallback to simple sliding window on failure
            print(f"Compaction failed: {e}")
            self.messages = system_msgs + recent_msgs
    
    def get_messages(self) -> list[Message]:
        """Get the current list of messages."""
        return self.messages.copy()
    
    def clear(self) -> None:
        """Clear the session history, preserving system prompts."""
        system_messages = [m for m in self.messages if m.role == "system"]
        self.messages = system_messages
        self.total_tokens_used = 0
    
    def update_token_usage(self, usage: dict[str, int]) -> None:
        """Update total token usage statistics."""
        self.total_tokens_used += usage.get("total_tokens", 0)
    
    def get_context_summary(self) -> str:
        """Get a text summary of the current session state."""
        name_str = f" ({self.name})" if self.name else ""
        return (
            f"Session ID: {self.id[:8]}{name_str}\n"
            f"Messages: {len(self.messages)}\n"
            f"Tokens used: {self.total_tokens_used:,}"
        )
    
    # =========================================================================
    # Persistence Methods
    # =========================================================================
    
    def to_dict(self) -> dict[str, Any]:
        """Convert session to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "tool_calls": m.tool_calls,
                    "tool_call_id": m.tool_call_id,
                    "name": m.name,
                }
                for m in self.messages
            ],
            "metadata": self.metadata,
            "max_messages": self.max_messages,
            "sliding_window_size": self.sliding_window_size,
            "total_tokens_used": self.total_tokens_used,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Create a Session from a dictionary."""
        messages = [
            Message(
                role=m["role"],
                content=m["content"],
                tool_calls=m.get("tool_calls", []),
                tool_call_id=m.get("tool_call_id"),
                name=m.get("name"),
            )
            for m in data.get("messages", [])
        ]
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            messages=messages,
            metadata=data.get("metadata", {}),
            max_messages=data.get("max_messages", 50),
            sliding_window_size=data.get("sliding_window_size", 20),
            total_tokens_used=data.get("total_tokens_used", 0),
        )
    
    def save(self, name: str | None = None, sessions_dir: Path | None = None) -> Path:
        """
        Save the session to a JSON file.
        
        Args:
            name: Optional name for the session (defaults to session ID)
            sessions_dir: Directory to save sessions (defaults to .klix_sessions)
            
        Returns:
            Path to the saved session file
        """
        if name:
            self.name = name
        
        save_dir = sessions_dir or self.sessions_dir
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Use name if provided, otherwise use ID
        filename = f"{self.name or self.id}.json"
        filepath = save_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        
        return filepath
    
    @classmethod
    def load(cls, name_or_id: str, sessions_dir: Path | None = None) -> Session:
        """
        Load a session from a JSON file.
        
        Args:
            name_or_id: Session name or ID to load
            sessions_dir: Directory to load sessions from
            
        Returns:
            Loaded Session instance
            
        Raises:
            FileNotFoundError: If session file doesn't exist
        """
        load_dir = sessions_dir or cls.sessions_dir
        load_dir = Path(load_dir)
        
        # Try exact filename first
        filepath = load_dir / f"{name_or_id}.json"
        if not filepath.exists():
            # Try with .json extension if not provided
            filepath = load_dir / name_or_id
            if not filepath.exists():
                raise FileNotFoundError(f"Session not found: {name_or_id}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def list_sessions(cls, sessions_dir: Path | None = None) -> list[dict[str, Any]]:
        """
        List all saved sessions.
        
        Args:
            sessions_dir: Directory to list sessions from
            
        Returns:
            List of session metadata dictionaries
        """
        list_dir = sessions_dir or cls.sessions_dir
        list_dir = Path(list_dir)
        
        if not list_dir.exists():
            return []
        
        sessions = []
        for filepath in list_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append({
                    "name": data.get("name") or data.get("id", "")[:8],
                    "id": data.get("id", ""),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                    "filepath": str(filepath),
                })
            except Exception:
                continue
        
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions
    
    def export_transcript(self, include_system: bool = False) -> str:
        """
        Export the session as a readable transcript.
        
        Args:
            include_system: Whether to include system messages
            
        Returns:
            Formatted transcript string
        """
        lines = [
            f"# Session Transcript",
            f"**ID:** {self.id}",
            f"**Name:** {self.name or 'Unnamed'}",
            f"**Created:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Messages:** {len(self.messages)}",
            "",
            "---",
            "",
        ]
        
        for msg in self.messages:
            if msg.role == "system" and not include_system:
                continue
            
            role_label = {
                "user": "👤 User",
                "assistant": "🤖 Assistant",
                "system": "⚙️ System",
                "tool": f"🔧 Tool ({msg.name})",
            }.get(msg.role, msg.role)
            
            lines.append(f"### {role_label}")
            lines.append("")
            lines.append(msg.content or "(empty)")
            lines.append("")
        
        return "\n".join(lines)
