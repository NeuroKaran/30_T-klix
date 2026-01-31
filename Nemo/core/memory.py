"""
Nemo - Memory Service using Mem0
Provides persistent, personalized memory layer for Nemo with its own Qdrant database.
This is separate from Klix's memory to avoid conflicts.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Union
from pathlib import Path

from mem0 import Memory as Mem0Local
from mem0 import MemoryClient as Mem0Cloud
from dotenv import load_dotenv

import logging

logger = logging.getLogger(__name__)

# Load Nemo's .env
nemo_env = Path(__file__).parent.parent / ".env"
load_dotenv(nemo_env)


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


@dataclass
class NemoConfig:
    """Nemo-specific configuration for memory."""
    
    # Nemo's own Qdrant path
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.resolve())
    
    # Memory settings
    memory_enabled: bool = field(default_factory=lambda: os.getenv("MEMORY_ENABLED", "true").lower() == "true")
    mem0_local: bool = field(default_factory=lambda: os.getenv("MEM0_LOCAL", "true").lower() == "true")
    mem0_api_key: str = field(default_factory=lambda: os.getenv("MEM0_API_KEY", ""))
    memory_user_id: str = field(default_factory=lambda: os.getenv("NEMO_USER_ID", "Friend"))
    
    # Nemo-specific Qdrant path (separate from Klix)
    qdrant_path: str = field(default_factory=lambda: os.getenv("NEMO_QDRANT_PATH", "./.qdrant_nemo"))
    collection_name: str = field(default_factory=lambda: os.getenv("NEMO_COLLECTION_NAME", "nemo_memories"))
    
    # Ollama settings
    ollama_host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    embedder_model: str = field(default_factory=lambda: os.getenv("MEM0_EMBEDDER_MODEL", "nomic-embed-text-v2-moe:latest"))
    llm_model: str = field(default_factory=lambda: os.getenv("MEM0_LLM_MODEL", "qwen2.5-coder:3b"))
    
    def __post_init__(self) -> None:
        """Ensure qdrant path is absolute."""
        if not os.path.isabs(self.qdrant_path):
            self.qdrant_path = str(self.project_root / self.qdrant_path)


def _build_nemo_config(config: NemoConfig, client: Any):
    """Build configuration for Nemo's local mem0 setup."""
    from mem0.configs.base import MemoryConfig
    from mem0.vector_stores.configs import VectorStoreConfig
    from mem0.embeddings.configs import EmbedderConfig
    from mem0.llms.configs import LlmConfig
    
    return MemoryConfig(
        vector_store=VectorStoreConfig(
            provider="qdrant",
            config={
                "collection_name": config.collection_name,
                "client": client,
                "embedding_model_dims": 768,  # nomic-embed-text-v2-moe dimensions
            }
        ),
        embedder=EmbedderConfig(
            provider="ollama",
            config={
                "model": config.embedder_model,
                "ollama_base_url": config.ollama_host,
            }
        ),
        llm=LlmConfig(
            provider="ollama",
            config={
                "model": config.llm_model,
                "ollama_base_url": config.ollama_host,
                "temperature": 0.1,
                "max_tokens": 2000,
            }
        ),
        version="v1.1",
    )


@dataclass
class NemoMemoryService:
    """
    Nemo's persistent memory layer using Mem0.
    
    Uses a separate Qdrant database from Klix to avoid conflicts.
    """
    
    config: NemoConfig = field(default_factory=NemoConfig)
    _client: Union[Mem0Local, Mem0Cloud, None] = field(default=None, repr=False)
    _qdrant_client: Any = field(default=None, repr=False)
    _is_local: bool = field(default=False, repr=False)
    
    def __post_init__(self) -> None:
        """Initialize the mem0 client (local or cloud)."""
        if not self.config.memory_enabled:
            logger.info("Nemo Memory service is disabled.")
            return
        
        if self.config.mem0_local:
            # Local mode: Use Nemo's own Qdrant
            logger.info(f"Initializing Nemo mem0 with Qdrant at {self.config.qdrant_path}...")
            try:
                from qdrant_client import QdrantClient
                self._qdrant_client = QdrantClient(path=os.path.abspath(self.config.qdrant_path))
                
                # Build config with this client
                local_config = _build_nemo_config(self.config, self._qdrant_client)
                
                self._client = Mem0Local(config=local_config)
                self._is_local = True
                logger.info(f"Nemo mem0 initialized. Collection: {self.config.collection_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Nemo mem0: {e}")
                self._client = None
        else:
            # Cloud mode: Use API key
            api_key = self.config.mem0_api_key
            if api_key:
                logger.info("Initializing cloud mem0 for Nemo...")
                self._client = Mem0Cloud(api_key=api_key)
                self._is_local = False
            else:
                logger.warning("MEM0_API_KEY not set and MEM0_LOCAL is false. Memory disabled.")
    
    @property
    def is_enabled(self) -> bool:
        """Check if memory service is enabled and configured."""
        return self._client is not None and self.config.memory_enabled
    
    async def close(self) -> None:
        """Close the memory service."""
        logger.debug("Closing Nemo memory service")
        if self._qdrant_client:
            try:
                self._qdrant_client.close()
                logger.debug("Nemo Qdrant client closed.")
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
        """Search for relevant memories using semantic similarity."""
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
            items = result.get("results", []) if isinstance(result, dict) else result
            for item in items:
                memories.append(MemoryItem.from_mem0(item))
            return memories
            
        except Exception as e:
            logger.error(f"Nemo memory search failed: {e}")
            return []
    
    def get_all(
        self,
        user_id: str | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        """Get all memories for a user."""
        if not self.is_enabled:
            return []
        
        user_id = user_id or self.config.memory_user_id
        
        try:
            result = self._client.get_all(user_id=user_id)
            
            memories = []
            items = result.get("results", []) if isinstance(result, dict) else result
            for item in items[:limit]:
                memories.append(MemoryItem.from_mem0(item))
            return memories
            
        except Exception as e:
            logger.error(f"Nemo memory get_all failed: {e}")
            return []
    
    def add(
        self,
        messages: list[dict[str, str]],
        user_id: str | None = None,
        memory_type: MemoryType = MemoryType.EPISODIC,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Add a conversation exchange to memory."""
        if not self.is_enabled:
            return False
        
        user_id = user_id or self.config.memory_user_id
        
        # Build metadata
        mem_metadata = metadata or {}
        mem_metadata["type"] = memory_type.value
        mem_metadata["user_id"] = user_id
        mem_metadata["timestamp"] = datetime.now().isoformat()
        mem_metadata["source"] = "nemo"
        
        try:
            self._client.add(
                messages=messages,
                user_id=user_id,
                metadata=mem_metadata,
            )
            return True
            
        except Exception as e:
            logger.error(f"Nemo memory add failed: {e}")
            return False
    
    def add_text(
        self,
        text: str,
        user_id: str | None = None,
        memory_type: MemoryType = MemoryType.SEMANTIC,
    ) -> bool:
        """Add a simple text memory."""
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
                    "source": "nemo_manual",
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return True
            
        except Exception as e:
            logger.error(f"Nemo memory add_text failed: {e}")
            return False
    
    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        if not self.is_enabled:
            return False
        
        try:
            self._client.delete(memory_id=memory_id)
            return True
        except Exception as e:
            logger.error(f"Nemo memory delete failed: {e}")
            return False
    
    def delete_all(self, user_id: str | None = None) -> bool:
        """Delete all memories for a user."""
        if not self.is_enabled:
            return False
        
        user_id = user_id or self.config.memory_user_id
        
        try:
            self._client.delete_all(user_id=user_id)
            return True
        except Exception as e:
            logger.error(f"Nemo memory delete_all failed: {e}")
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
        """Build a context string from relevant memories for LLM injection."""
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
        """Extract and store memories from a conversation exchange."""
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
            "qdrant_path": self.config.qdrant_path,
            "collection_name": self.config.collection_name,
            "user_id": user_id,
            "total_memories": len(memories),
            "by_type": {t.value: count for t, count in type_counts.items()},
        }


# =============================================================================
# Module-level convenience functions
# =============================================================================

_nemo_memory_service: NemoMemoryService | None = None


def get_nemo_memory_service(config: NemoConfig | None = None) -> NemoMemoryService:
    """Get or create Nemo's global MemoryService instance."""
    global _nemo_memory_service
    
    if _nemo_memory_service is None:
        _nemo_memory_service = NemoMemoryService(config=config or NemoConfig())
    
    return _nemo_memory_service


def reset_nemo_memory_service() -> None:
    """Reset Nemo's global MemoryService (for testing)."""
    global _nemo_memory_service
    _nemo_memory_service = None


__all__ = [
    "MemoryItem",
    "MemoryType",
    "NemoConfig",
    "NemoMemoryService",
    "get_nemo_memory_service",
    "reset_nemo_memory_service",
]
