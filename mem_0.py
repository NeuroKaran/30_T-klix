"""
Klix - Memory Service using Mem0
Provides persistent, personalized memory layer for the AI agent.
Supports both Cloud API and Local (Qdrant + Ollama) modes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Union

# Import both Memory (local) and MemoryClient (cloud) from mem0
from mem0 import Memory as Mem0Local
from mem0 import MemoryClient as Mem0Cloud

from config import Config, get_config
from logging_config import get_logger

logger = get_logger(__name__)


class MemoryType(Enum):
    """Types of memories stored."""
    EPISODIC = "episodic"      # Specific past events/conversations
    SEMANTIC = "semantic"       # User preferences & facts
    PROCEDURAL = "procedural"   # How-to knowledge & patterns


@dataclass
class MemoryItem:
    """Represents a single memory item."""
    id: str
    content: str
    memory_type: MemoryType = MemoryType.EPISODIC
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_mem0(cls, data: dict[str, Any]) -> MemoryItem:
        """Create MemoryItem from mem0 API response."""
        memory_type = MemoryType.EPISODIC
        metadata = data.get("metadata") or {}
        if metadata:
            if type_str := metadata.get("type"):
                try:
                    memory_type = MemoryType(type_str)
                except ValueError:
                    pass
        
        return cls(
            id=data.get("id", ""),
            content=data.get("memory", ""),
            memory_type=memory_type,
            metadata=data.get("metadata") or {},
        )


def _build_local_config(config: Config, client: Any):
    """Build configuration for local mem0 setup using MemoryConfig objects."""
    from mem0.configs.base import MemoryConfig
    from mem0.vector_stores.configs import VectorStoreConfig
    from mem0.embeddings.configs import EmbedderConfig
    from mem0.llms.configs import LlmConfig
    
    # Client is now passed in
    # client = QdrantClient(path=os.path.abspath(config.mem0_qdrant_path))
    
    return MemoryConfig(
        vector_store=VectorStoreConfig(
            provider="qdrant",
            config={
                "collection_name": "klix_memories",
                "client": client,
                "embedding_model_dims": 768,  # nomic-embed-text-v2-moe dimensions
            }
        ),
        embedder=EmbedderConfig(
            provider="ollama",
            config={
                "model": config.mem0_embedder_model,
                "ollama_base_url": config.ollama_host,
            }
        ),
        llm=LlmConfig(
            provider="ollama",
            config={
                "model": config.mem0_llm_model,
                "ollama_base_url": config.ollama_host,
                "temperature": 0.1,
                "max_tokens": 2000,
            }
        ),
        version="v1.1",
    )


@dataclass
class MemoryService:
    """
    Persistent memory layer using Mem0.
    
    Supports both Cloud API (MemoryClient) and Local (Memory with Qdrant + Ollama).
    Provides semantic search and storage of memories across sessions.
    Memories are stored per-user and can be scoped to projects.
    """
    
    config: Config = field(default_factory=get_config)
    _client: Union[Mem0Local, Mem0Cloud, None] = field(default=None, repr=False)
    _qdrant_client: Any = field(default=None, repr=False)
    _is_local: bool = field(default=False, repr=False)
    
    def __post_init__(self) -> None:
        """Initialize the mem0 client (local or cloud)."""
        if not self.config.memory_enabled:
            logger.info("Memory service is disabled.")
            return
        
        if self.config.mem0_local:
            # Local mode: Use Qdrant + Ollama
            logger.info("Initializing local mem0 with Qdrant and Ollama...")
            try:
                # Store client reference to close it properly later
                from qdrant_client import QdrantClient
                self._qdrant_client = QdrantClient(path=os.path.abspath(self.config.mem0_qdrant_path))
                
                # Build config with this client
                local_config = _build_local_config(self.config, self._qdrant_client)
                
                self._client = Mem0Local(config=local_config)
                self._is_local = True
                logger.info(f"Local mem0 initialized. Qdrant path: {self.config.mem0_qdrant_path}")
            except Exception as e:
                logger.error(f"Failed to initialize local mem0: {e}")
                self._client = None
        else:
            # Cloud mode: Use API key
            api_key = self.config.mem0_api_key
            if api_key:
                logger.info("Initializing cloud mem0 with API key...")
                self._client = Mem0Cloud(api_key=api_key)
                self._is_local = False
            else:
                logger.warning("MEM0_API_KEY not set and MEM0_LOCAL is false. Memory disabled.")
    
    @property
    def is_enabled(self) -> bool:
        """Check if memory service is enabled and configured."""
        return self._client is not None and self.config.memory_enabled
    
    def _get_filters(self, user_id: str) -> dict[str, str]:
        """Build filters dict for mem0 API calls."""
        return {"user_id": user_id}
    
    async def close(self) -> None:
        """Close the memory service."""
        logger.debug("Closing memory service")
        if self._qdrant_client:
            try:
                self._qdrant_client.close()
                logger.debug("Qdrant client closed.")
            except Exception as e:
                logger.warning(f"Error closing Qdrant client: {e}")
    
    # =========================================================================
    # Core Memory Operations
    # =========================================================================
    
    def search(
        self,
        query: str,
        user_id: str | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        """
        Search for relevant memories using semantic similarity.
        
        Args:
            query: The search query
            user_id: User identifier (defaults to config)
            limit: Maximum number of results
            
        Returns:
            List of relevant memories
        """
        if not self.is_enabled:
            return []
        
        user_id = user_id or self.config.memory_user_id
        
        try:
            result = self._client.search(
                query=query,
                user_id=user_id,
                limit=limit,
            )
            
            memories = []
            # Handle both local and cloud response formats
            items = result.get("results", []) if isinstance(result, dict) else result
            for item in items:
                memories.append(MemoryItem.from_mem0(item))
            return memories
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []
    
    def get_all(
        self,
        user_id: str | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        """
        Get all memories for a user.
        
        Args:
            user_id: User identifier (defaults to config)
            limit: Maximum number of results
            
        Returns:
            List of all memories
        """
        if not self.is_enabled:
            return []
        
        user_id = user_id or self.config.memory_user_id
        
        try:
            result = self._client.get_all(user_id=user_id)
            
            memories = []
            # Handle both local and cloud response formats
            items = result.get("results", []) if isinstance(result, dict) else result
            for item in items[:limit]:
                memories.append(MemoryItem.from_mem0(item))
            return memories
            
        except Exception as e:
            logger.error(f"Memory get_all failed: {e}")
            return []
    
    def add(
        self,
        messages: list[dict[str, str]],
        user_id: str | None = None,
        memory_type: MemoryType = MemoryType.EPISODIC,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Add a conversation exchange to memory.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier (defaults to config)
            memory_type: Type of memory to store
            metadata: Additional metadata to store
            
        Returns:
            True if successful
        """
        if not self.is_enabled:
            return False
        
        user_id = user_id or self.config.memory_user_id
        
        # Build metadata
        mem_metadata = metadata or {}
        mem_metadata["type"] = memory_type.value
        mem_metadata["user_id"] = user_id
        mem_metadata["timestamp"] = datetime.now().isoformat()
        
        try:
            self._client.add(
                messages=messages,
                user_id=user_id,
                metadata=mem_metadata,
            )
            return True
            
        except Exception as e:
            logger.error(f"Memory add failed: {e}")
            return False
    
    def add_text(
        self,
        text: str,
        user_id: str | None = None,
        memory_type: MemoryType = MemoryType.SEMANTIC,
    ) -> bool:
        """
        Add a simple text memory (for /remember command).
        
        Args:
            text: The memory text to store
            user_id: User identifier
            memory_type: Type of memory
            
        Returns:
            True if successful
        """
        if not self.is_enabled:
            return False
        
        user_id = user_id or self.config.memory_user_id
        
        try:
            self._client.add(
                messages=[{"role": "user", "content": text}],
                user_id=user_id,
                metadata={
                    "type": memory_type.value,
                    "user_id": user_id,
                    "source": "manual",
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return True
            
        except Exception as e:
            logger.error(f"Memory add_text failed: {e}")
            return False
    
    def delete(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: The memory ID to delete
            
        Returns:
            True if successful
        """
        if not self.is_enabled:
            return False
        
        try:
            self._client.delete(memory_id=memory_id)
            return True
        except Exception as e:
            logger.error(f"Memory delete failed: {e}")
            return False
    
    def delete_all(self, user_id: str | None = None) -> bool:
        """
        Delete all memories for a user.
        
        Args:
            user_id: User identifier (defaults to config)
            
        Returns:
            True if successful
        """
        if not self.is_enabled:
            return False
        
        user_id = user_id or self.config.memory_user_id
        
        try:
            self._client.delete_all(user_id=user_id)
            return True
        except Exception as e:
            logger.error(f"Memory delete_all failed: {e}")
            return False
    
    # =========================================================================
    # Context Building
    # =========================================================================
    
    def get_memory_context(
        self,
        query: str,
        user_id: str | None = None,
        max_memories: int = 5,
    ) -> str:
        """
        Build a context string from relevant memories for LLM injection.
        
        This is the main method used by the agent to retrieve memories
        before sending a prompt to the LLM.
        
        Args:
            query: The user's current query
            user_id: User identifier
            max_memories: Maximum memories to include
            
        Returns:
            Formatted string of relevant memories, or empty string
        """
        if not self.is_enabled:
            return ""
        
        user_id = user_id or self.config.memory_user_id
        
        # First try semantic search
        memories = self.search(query, user_id=user_id, limit=max_memories)
        
        # Fallback to recent memories if search returns nothing
        if not memories:
            memories = self.get_all(user_id=user_id, limit=max_memories)
        
        if not memories:
            return ""
        
        # Format memories for context
        lines = []
        for mem in memories:
            type_icon = {
                MemoryType.EPISODIC: "📅",
                MemoryType.SEMANTIC: "💡", 
                MemoryType.PROCEDURAL: "⚙️",
            }.get(mem.memory_type, "•")
            lines.append(f"{type_icon} {mem.content}")
        
        return "\n".join(lines)
    
    def extract_and_store(
        self,
        user_input: str,
        assistant_response: str,
        user_id: str | None = None,
    ) -> bool:
        """
        Extract and store memories from a conversation exchange.
        
        Called automatically after each exchange if auto_extract is enabled.
        Mem0 handles the extraction - we just need to pass the messages.
        
        Args:
            user_input: The user's message
            assistant_response: The assistant's response
            user_id: User identifier
            
        Returns:
            True if successful
        """
        if not self.is_enabled:
            return False
        
        messages = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": assistant_response},
        ]
        
        return self.add(
            messages=messages,
            user_id=user_id,
            memory_type=MemoryType.EPISODIC,
        )
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Get memory statistics for a user."""
        if not self.is_enabled:
            return {"enabled": False}
        
        user_id = user_id or self.config.memory_user_id
        memories = self.get_all(user_id=user_id, limit=100)
        
        # Count by type
        type_counts = {t: 0 for t in MemoryType}
        for mem in memories:
            type_counts[mem.memory_type] += 1
        
        return {
            "enabled": True,
            "local_mode": self._is_local,
            "user_id": user_id,
            "total_memories": len(memories),
            "by_type": {t.value: count for t, count in type_counts.items()},
        }


# =============================================================================
# Module-level convenience functions
# =============================================================================

_memory_service: MemoryService | None = None


def get_memory_service(config: Config | None = None) -> MemoryService:
    """Get or create the global MemoryService instance."""
    global _memory_service
    
    if _memory_service is None:
        _memory_service = MemoryService(config=config or get_config())
    
    return _memory_service


def reset_memory_service() -> None:
    """Reset the global MemoryService (for testing)."""
    global _memory_service
    _memory_service = None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "MemoryItem",
    "MemoryType",
    "MemoryService",
    "get_memory_service",
    "reset_memory_service",
]