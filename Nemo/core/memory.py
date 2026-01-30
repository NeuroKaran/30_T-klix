"""
Nemo - Memory Service using Mem0
Provides persistent, personalized memory layer for the AI companion.
Borrowed and adapted from the Klix project architecture.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mem0 import MemoryClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """Represents a single memory entry."""
    id: str
    content: str
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)



@dataclass
class MemoryService:
    """
    Persistent memory layer using Mem0 for Nemo.
    
    Provides semantic search and storage of memories across sessions.
    Memories are stored per-user and can be personalized for conversations.
    
    Key Features:
    - Semantic search for relevant past conversations
    - Non-blocking memory saves for low latency
    - User-scoped memory isolation
    """
    
    # Configuration
    user_id: str = field(default_factory=lambda: os.getenv("NEMO_USER_ID", "user_default"))
    api_key: str = field(default_factory=lambda: os.getenv("MEM0_API_KEY", ""))
    enabled: bool = field(default_factory=lambda: os.getenv("MEMORY_ENABLED", "true").lower() == "true")
    search_limit: int = 5
    
    # Internal state
    _client: MemoryClient | None = field(default=None, init=False)
    
    def __post_init__(self) -> None:
        """Initialize the Mem0 client."""
        if self.enabled and self.api_key:
            try:
                self._client = MemoryClient(api_key=self.api_key)
                logger.info("🧠 Memory service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize memory service: {e}")
                self._client = None
                self.enabled = False
        else:
            logger.warning("⚠️ Memory service disabled - no API key provided")
            self._client = None
            self.enabled = False
    
    @property
    def is_enabled(self) -> bool:
        """Check if memory service is enabled and configured."""
        return self.enabled and self._client is not None
    
    def get_context(self, text: str, user_id: str | None = None) -> str:
        """
        Searches past conversations for relevant info.
        
        This is the main method for context injection before sending
        a prompt to the LLM. Returns relevant memories as a formatted string.
        
        Example: If user says "I'm sad", it might recall 
                 "User mentioned breaking up last week".
        
        Args:
            text: The current user input to search against
            user_id: Optional user identifier (defaults to configured user)
            
        Returns:
            Formatted string of relevant memories, or empty string if none found
        """
        if not self.is_enabled:
            return ""
        
        target_user = user_id or self.user_id
        
        try:
            # 1. Try semantic search first
            memories = self._client.search(
                text, 
                user_id=target_user,
                filters={"user_id": target_user},
                limit=self.search_limit
            )
            
            # 2. If no semantic matches, or if query is broad ("what do you know"),
            # fallback to recent memories to provide some context.
            if not memories:
                logger.info("⚠️ No semantic matches found. Falling back to recent memories.")
                all_memories = self._client.get_all(user_id=target_user, limit=10)
                # Helper to normalize mem0 format differences if any
                memories = all_memories
            
            # Handle dictionary response format (mem0 v2)
            if isinstance(memories, dict) and 'results' in memories:
                memories = memories['results']
            
            if not memories:
                logger.debug("No relevant memories found (search & fallback)")
                return ""
            
            # Format memories for context injection
            context_parts = []
            for i, mem in enumerate(memories, 1):
                memory_text = mem.get('memory', '')
                # Handle simplified format from get_all if different
                if not memory_text and 'text' in mem:
                    memory_text = mem['text']
                    
                if memory_text:
                    context_parts.append(f"• {memory_text}")
            
            context_str = "\n".join(context_parts)
            logger.info(f"🧠 Recalled {len(context_parts)} memories")
            return context_str
            
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return ""
    
    def save_interaction(
        self, 
        user_text: str, 
        agent_text: str, 
        user_id: str | None = None
    ) -> bool:
        """
        Saves the conversation turn to long-term memory.
        
        This method stores the combined interaction for future retrieval.
        Should be called asynchronously to not block the response.
        
        Args:
            user_text: What the user said
            agent_text: What Nemo responded
            user_id: Optional user identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled:
            return False
        
        target_user = user_id or self.user_id
        
        try:
            # Store as a combined interaction for better recall
            memory_content = f"User: {user_text} | Nemo: {agent_text}"
            
            self._client.add(
                memory_content, 
                user_id=target_user
            )
            
            logger.info("💾 Memory saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False
    
    def save_text(self, text: str, user_id: str | None = None) -> bool:
        """
        Save a simple text memory (for explicit /remember commands).
        
        Args:
            text: The memory text to store
            user_id: Optional user identifier
            
        Returns:
            True if successful
        """
        if not self.is_enabled:
            return False
        
        target_user = user_id or self.user_id
        
        try:
            self._client.add(text, user_id=target_user)
            logger.info(f"💾 Text memory saved: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error saving text memory: {e}")
            return False
    
    def get_all_memories(
        self, 
        user_id: str | None = None, 
        limit: int = 20
    ) -> list[Memory]:
        """
        Get all memories for a user.
        
        Args:
            user_id: Optional user identifier
            limit: Maximum number of memories to return
            
        Returns:
            List of Memory objects
        """
        if not self.is_enabled:
            return []
        
        target_user = user_id or self.user_id
        
        try:
            memories = self._client.get_all(user_id=target_user, limit=limit)
            
            result = []
            for mem in memories:
                result.append(Memory(
                    id=mem.get('id', ''),
                    content=mem.get('memory', ''),
                    created_at=None,  # Parse if available
                    metadata=mem.get('metadata', {})
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching all memories: {e}")
            return []
    
    def delete_all(self, user_id: str | None = None) -> bool:
        """
        Delete all memories for a user.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            True if successful
        """
        if not self.is_enabled:
            return False
        
        target_user = user_id or self.user_id
        
        try:
            self._client.delete_all(user_id=target_user)
            logger.info(f"🗑️ All memories deleted for user: {target_user}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            return False
    
    def close(self) -> None:
        """Close the memory service."""
        self._client = None
        logger.info("Memory service closed")


# =============================================================================
# Module-level singleton
# =============================================================================

_memory_service: MemoryService | None = None


def get_memory_service() -> MemoryService:
    """Get or create the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def init_memory_service(
    user_id: str | None = None,
    api_key: str | None = None
) -> MemoryService:
    """
    Initialize memory service with custom configuration.
    
    Args:
        user_id: Custom user identifier
        api_key: Custom Mem0 API key
        
    Returns:
        Configured MemoryService instance
    """
    global _memory_service
    
    kwargs = {}
    if user_id:
        kwargs['user_id'] = user_id
    if api_key:
        kwargs['api_key'] = api_key
    
    _memory_service = MemoryService(**kwargs)
    return _memory_service
