"""
Abstract base class for all memory implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List
from datetime import datetime

from neo4j_orchestration.core.types import MemoryEntry, MemoryType
from neo4j_orchestration.core.exceptions import MemoryError


class BaseMemory(ABC):
    """Abstract base class for memory implementations
    
    All memory types (Working, Episodic, Semantic) inherit from this
    and implement the core interface methods.
    """
    
    def __init__(self, memory_type: MemoryType):
        """Initialize base memory
        
        Args:
            memory_type: Type of memory (WORKING, EPISODIC, SEMANTIC)
        """
        self.memory_type = memory_type
    
    @abstractmethod
    async def get(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve entry from memory
        
        Args:
            key: Unique key for the entry
            
        Returns:
            MemoryEntry if found, None otherwise
            
        Raises:
            MemoryError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        **kwargs
    ) -> MemoryEntry:
        """Store entry in memory
        
        Args:
            key: Unique key for the entry
            value: Data to store
            **kwargs: Additional metadata (ttl, tags, etc.)
            
        Returns:
            Created MemoryEntry
            
        Raises:
            MemoryError: If storage fails
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove entry from memory
        
        Args:
            key: Unique key for the entry
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            MemoryError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory
        
        Args:
            key: Key to check
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """Clear all entries from memory
        
        Returns:
            Number of entries cleared
        """
        pass
    
    @abstractmethod
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all keys in memory
        
        Args:
            pattern: Optional pattern to filter keys (e.g., "vendor:*")
            
        Returns:
            List of matching keys
        """
        pass


__all__ = ["BaseMemory"]
