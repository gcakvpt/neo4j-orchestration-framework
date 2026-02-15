"""
Memory Manager - Unified interface for all memory types.

Provides a single entry point for working with different memory backends:
- Working Memory (cache)
- Episodic Memory (session history)
- Semantic Memory (business rules)
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from neo4j import AsyncDriver

from ..core.types import MemoryEntry
from ..core.exceptions import ValidationError, MemoryError
from .base import BaseMemory
from .working import WorkingMemory
from .episodic import EpisodicMemory
from .semantic import SemanticMemory


class MemoryType(str, Enum):
    """Memory backend types."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryManager:
    """
    Unified interface for all memory types.
    
    Provides factory methods, automatic routing, and cross-memory operations.
    
    Example:
        >>> manager = MemoryManager(
        ...     working_config={"max_size": 1000, "default_ttl": 3600},
        ...     neo4j_driver=driver
        ... )
        >>> 
        >>> # Use specific memory types
        >>> await manager.working.set("temp", {"value": 123})
        >>> await manager.episodic.save_session(session_data)
        >>> await manager.semantic.store_rule("RULE_001", "risk", {...})
        >>> 
        >>> # Or use routing
        >>> await manager.set("key", value, memory_type=MemoryType.WORKING)
    """
    
    def __init__(
        self,
        working_config: Optional[Dict[str, Any]] = None,
        neo4j_driver: Optional[AsyncDriver] = None,
        auto_initialize: bool = True
    ):
        """
        Initialize memory manager.
        
        Args:
            working_config: Configuration for WorkingMemory
            neo4j_driver: Neo4j driver for graph-backed memory
            auto_initialize: Whether to initialize all memory types
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self._working_config = working_config or {}
        self._neo4j_driver = neo4j_driver
        
        # Memory backends
        self._working: Optional[WorkingMemory] = None
        self._episodic: Optional[EpisodicMemory] = None
        self._semantic: Optional[SemanticMemory] = None
        
        if auto_initialize:
            self._initialize_all()
    
    def _initialize_all(self) -> None:
        """Initialize all memory backends."""
        # Working memory always available
        self._working = WorkingMemory(**self._working_config)
        
        # Graph-backed memory requires driver
        if self._neo4j_driver:
            self._episodic = EpisodicMemory(self._neo4j_driver)
            self._semantic = SemanticMemory(self._neo4j_driver)
    
    @property
    def working(self) -> WorkingMemory:
        """Get working memory instance."""
        if self._working is None:
            self._working = WorkingMemory(**self._working_config)
        return self._working
    
    @property
    def episodic(self) -> EpisodicMemory:
        """Get episodic memory instance."""
        if self._episodic is None:
            if self._neo4j_driver is None:
                raise MemoryError("Episodic memory requires Neo4j driver")
            self._episodic = EpisodicMemory(self._neo4j_driver)
        return self._episodic
    
    @property
    def semantic(self) -> SemanticMemory:
        """Get semantic memory instance."""
        if self._semantic is None:
            if self._neo4j_driver is None:
                raise MemoryError("Semantic memory requires Neo4j driver")
            self._semantic = SemanticMemory(self._neo4j_driver)
        return self._semantic
    
    def get_memory(self, memory_type: Union[MemoryType, str]) -> BaseMemory:
        """
        Get specific memory backend.
        
        Args:
            memory_type: Type of memory to retrieve
            
        Returns:
            Memory backend instance
            
        Raises:
            ValidationError: If memory type is invalid
        """
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType(memory_type.lower())
            except ValueError:
                raise ValidationError(
                    f"Invalid memory type: {memory_type}",
                    field="memory_type",
                    value=memory_type
                )
        
        if memory_type == MemoryType.WORKING:
            return self.working
        elif memory_type == MemoryType.EPISODIC:
            return self.episodic
        elif memory_type == MemoryType.SEMANTIC:
            return self.semantic
        else:
            raise ValidationError(
                f"Unknown memory type: {memory_type}",
                field="memory_type",
                value=memory_type
            )
    
    async def set(
        self,
        key: str,
        value: Any,
        memory_type: Union[MemoryType, str] = MemoryType.WORKING,
        **kwargs
    ) -> None:
        """
        Store value in specified memory type.
        
        Args:
            key: Storage key
            value: Value to store
            memory_type: Which memory backend to use
            **kwargs: Additional arguments for specific memory type
            
        Raises:
            ValidationError: If memory type is invalid
            MemoryError: If operation not supported
        """
        memory = self.get_memory(memory_type)
        await memory.set(key, value, **kwargs)
    
    async def get(
        self,
        key: str,
        memory_type: Union[MemoryType, str] = MemoryType.WORKING
    ) -> Optional[MemoryEntry]:
        """
        Retrieve value from specified memory type.
        
        Args:
            key: Storage key
            memory_type: Which memory backend to use
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            ValidationError: If memory type is invalid
        """
        memory = self.get_memory(memory_type)
        return await memory.get(key)
    
    async def exists(
        self,
        key: str,
        memory_type: Union[MemoryType, str] = MemoryType.WORKING
    ) -> bool:
        """
        Check if key exists in specified memory type.
        
        Args:
            key: Storage key
            memory_type: Which memory backend to use
            
        Returns:
            True if key exists, False otherwise
        """
        memory = self.get_memory(memory_type)
        return await memory.exists(key)
    
    async def delete(
        self,
        key: str,
        memory_type: Union[MemoryType, str] = MemoryType.WORKING
    ) -> bool:
        """
        Delete key from specified memory type.
        
        Args:
            key: Storage key
            memory_type: Which memory backend to use
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            MemoryError: If operation not supported
        """
        memory = self.get_memory(memory_type)
        return await memory.delete(key)
    
    async def clear(
        self,
        memory_type: Union[MemoryType, str] = MemoryType.WORKING
    ) -> int:
        """
        Clear all entries from specified memory type.
        
        Args:
            memory_type: Which memory backend to clear
            
        Returns:
            Number of entries cleared
        """
        memory = self.get_memory(memory_type)
        return await memory.clear()
    
    async def list_keys(
        self,
        pattern: Optional[str] = None,
        memory_type: Union[MemoryType, str] = MemoryType.WORKING
    ) -> List[str]:
        """
        List keys in specified memory type.
        
        Args:
            pattern: Optional pattern to filter keys
            memory_type: Which memory backend to query
            
        Returns:
            List of matching keys
        """
        memory = self.get_memory(memory_type)
        return await memory.list_keys(pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all memory backends.
        
        Returns:
            Dictionary with stats for each memory type
        """
        stats = {}
        
        # Working memory stats
        if self._working:
            working_keys = await self._working.list_keys()
            stats["working"] = {
                "initialized": True,
                "key_count": len(working_keys),
                "max_size": self._working_config.get("max_size"),
                "default_ttl": self._working_config.get("default_ttl")
            }
        else:
            stats["working"] = {"initialized": False}
        
        # Episodic memory stats
        if self._episodic:
            episodic_keys = await self._episodic.list_keys()
            stats["episodic"] = {
                "initialized": True,
                "session_count": len(episodic_keys)
            }
        else:
            stats["episodic"] = {"initialized": False}
        
        # Semantic memory stats
        if self._semantic:
            semantic_keys = await self._semantic.list_keys()
            stats["semantic"] = {
                "initialized": True,
                "rule_count": len(semantic_keys)
            }
        else:
            stats["semantic"] = {"initialized": False}
        
        return stats
    
    async def close(self) -> None:
        """Close all memory backends and release resources."""
        # Working memory cleanup
        if self._working:
            await self._working.clear()
        
        # Neo4j driver should be closed by caller
        # (since it may be shared across components)
        pass
