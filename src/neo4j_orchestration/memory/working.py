"""
Working Memory implementation with in-memory and Redis backends.

Working memory is a fast, temporary cache with TTL expiration and LRU eviction.
Used for active analysis sessions to avoid redundant Neo4j queries.
"""

import time
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta
from collections import OrderedDict

from neo4j_orchestration.core.types import MemoryEntry, MemoryType
from neo4j_orchestration.core.exceptions import MemoryError, MemoryExpiredError
from neo4j_orchestration.memory.base import BaseMemory
from neo4j_orchestration.utils.logging import get_logger

logger = get_logger(__name__)


class WorkingMemory(BaseMemory):
    """In-memory cache with TTL and LRU eviction
    
    Supports both local dict storage and Redis backend for distributed systems.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        redis_client=None
    ):
        """Initialize working memory
        
        Args:
            max_size: Maximum number of entries (LRU eviction when exceeded)
            default_ttl: Default TTL in seconds (1 hour default)
            redis_client: Optional Redis client for distributed cache
        """
        super().__init__(MemoryType.WORKING)
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.redis_client = redis_client
        
        # Local storage (OrderedDict for LRU)
        self._store: OrderedDict[str, MemoryEntry] = OrderedDict()
        
        logger.info(
            f"WorkingMemory initialized: max_size={max_size}, "
            f"default_ttl={default_ttl}s, "
            f"backend={'redis' if redis_client else 'local'}"
        )
    
    async def get(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve from cache
        
        Args:
            key: Cache key
            
        Returns:
            MemoryEntry if found and not expired, None otherwise
        """
        if self.redis_client:
            return await self._get_redis(key)
        else:
            return await self._get_local(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Store in cache
        
        Args:
            key: Cache key
            value: Data to cache
            ttl: Time-to-live in seconds (uses default_ttl if not specified)
            metadata: Optional metadata
            
        Returns:
            Created MemoryEntry
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=MemoryType.WORKING,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        if self.redis_client:
            await self._set_redis(entry, ttl)
        else:
            await self._set_local(entry)
        
        logger.debug(f"Stored in working memory: {key} (ttl={ttl}s)")
        return entry
    
    async def delete(self, key: str) -> bool:
        """Remove from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        if self.redis_client:
            return await self._delete_redis(key)
        else:
            return await self._delete_local(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists (and not expired)"""
        entry = await self.get(key)
        return entry is not None
    
    async def clear(self) -> int:
        """Clear all entries"""
        if self.redis_client:
            return await self._clear_redis()
        else:
            count = len(self._store)
            self._store.clear()
            logger.info(f"Cleared {count} entries from working memory")
            return count
    
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all keys (optionally filtered by pattern)"""
        if self.redis_client:
            return await self._list_keys_redis(pattern)
        else:
            await self._cleanup_expired()
            keys = list(self._store.keys())
            
            if pattern:
                # Simple wildcard matching
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
            
            return keys
    
    # Local storage methods
    
    async def _get_local(self, key: str) -> Optional[MemoryEntry]:
        """Get from local dict storage"""
        # Check if key exists
        if key not in self._store:
            return None
        
        entry = self._store[key]
        
        # Check expiration BEFORE cleanup
        if entry.expires_at and datetime.now() > entry.expires_at:
            del self._store[key]
            logger.debug(f"Entry expired: {key}")
            raise MemoryExpiredError(f"Memory entry expired: {key}", details={"key": key, "memory_type": self.memory_type.value})
        
        # Cleanup other expired entries (not the one we're accessing)
        await self._cleanup_expired()
        
        # Move to end (LRU)
        self._store.move_to_end(key)
        
        return entry
    
    async def _set_local(self, entry: MemoryEntry) -> None:
        """Set in local dict storage"""
        # LRU eviction if at capacity
        if len(self._store) >= self.max_size and entry.key not in self._store:
            # Remove oldest (first item in OrderedDict)
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
            logger.debug(f"LRU eviction: removed {oldest_key}")
        
        self._store[entry.key] = entry
        self._store.move_to_end(entry.key)
    
    async def _delete_local(self, key: str) -> bool:
        """Delete from local dict storage"""
        if key in self._store:
            del self._store[key]
            logger.debug(f"Deleted from working memory: {key}")
            return True
        return False
    
    async def _cleanup_expired(self) -> int:
        """Remove expired entries from local storage"""
        now = datetime.now()
        expired = [
            k for k, v in self._store.items()
            if v.expires_at and now > v.expires_at
        ]
        
        for key in expired:
            del self._store[key]
        
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired entries")
        
        return len(expired)
    
    # Redis storage methods
    
    async def _get_redis(self, key: str) -> Optional[MemoryEntry]:
        """Get from Redis"""
        import json
        
        value = self.redis_client.get(key)
        if not value:
            return None
        
        data = json.loads(value)
        return MemoryEntry(**data)
    
    async def _set_redis(self, entry: MemoryEntry, ttl: int) -> None:
        """Set in Redis with TTL"""
        import json
        
        # Serialize entry (Pydantic model_dump)
        data = entry.model_dump(mode='json')
        value = json.dumps(data)
        
        self.redis_client.setex(entry.key, ttl, value)
    
    async def _delete_redis(self, key: str) -> bool:
        """Delete from Redis"""
        result = self.redis_client.delete(key)
        return result > 0
    
    async def _clear_redis(self) -> int:
        """Clear all keys from Redis (use with caution!)"""
        keys = self.redis_client.keys("*")
        if keys:
            return self.redis_client.delete(*keys)
        return 0
    
    async def _list_keys_redis(self, pattern: Optional[str] = None) -> List[str]:
        """List keys from Redis"""
        pattern = pattern or "*"
        keys = self.redis_client.keys(pattern)
        return [k.decode() if isinstance(k, bytes) else k for k in keys]


__all__ = ["WorkingMemory"]
