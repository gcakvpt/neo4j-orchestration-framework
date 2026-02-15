"""
Unit tests for Working Memory implementation.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from neo4j_orchestration.memory.working import WorkingMemory
from neo4j_orchestration.core.types import MemoryType
from neo4j_orchestration.core.exceptions import MemoryExpiredError


@pytest.fixture
def working_memory():
    """Create working memory instance for testing"""
    return WorkingMemory(max_size=10, default_ttl=60)


@pytest.mark.asyncio
async def test_working_memory_initialization(working_memory):
    """Test working memory initializes correctly"""
    assert working_memory.memory_type == MemoryType.WORKING
    assert working_memory.max_size == 10
    assert working_memory.default_ttl == 60
    assert working_memory.redis_client is None


@pytest.mark.asyncio
async def test_set_and_get(working_memory):
    """Test basic set and get operations"""
    # Set a value
    entry = await working_memory.set("test_key", {"data": "test_value"})
    
    assert entry.key == "test_key"
    assert entry.value == {"data": "test_value"}
    assert entry.memory_type == MemoryType.WORKING
    assert entry.expires_at is not None
    
    # Get the value
    retrieved = await working_memory.get("test_key")
    
    assert retrieved is not None
    assert retrieved.key == "test_key"
    assert retrieved.value == {"data": "test_value"}


@pytest.mark.asyncio
async def test_get_nonexistent_key(working_memory):
    """Test getting non-existent key returns None"""
    result = await working_memory.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_exists(working_memory):
    """Test exists check"""
    await working_memory.set("exists_key", "value")
    
    assert await working_memory.exists("exists_key") is True
    assert await working_memory.exists("nonexistent") is False


@pytest.mark.asyncio
async def test_delete(working_memory):
    """Test delete operation"""
    await working_memory.set("delete_key", "value")
    
    # Verify it exists
    assert await working_memory.exists("delete_key") is True
    
    # Delete it
    deleted = await working_memory.delete("delete_key")
    assert deleted is True
    
    # Verify it's gone
    assert await working_memory.exists("delete_key") is False
    
    # Delete non-existent returns False
    deleted_again = await working_memory.delete("delete_key")
    assert deleted_again is False


@pytest.mark.asyncio
async def test_custom_ttl(working_memory):
    """Test custom TTL parameter"""
    # Set with 2 second TTL
    entry = await working_memory.set("ttl_key", "value", ttl=2)
    
    # Should exist immediately
    assert await working_memory.exists("ttl_key") is True
    
    # Wait for expiration
    await asyncio.sleep(2.5)
    
    # Should raise MemoryExpiredError when accessed
    with pytest.raises(MemoryExpiredError):
        await working_memory.get("ttl_key")


@pytest.mark.asyncio
async def test_lru_eviction(working_memory):
    """Test LRU eviction when max_size exceeded"""
    # Fill to capacity (max_size=10)
    for i in range(10):
        await working_memory.set(f"key_{i}", f"value_{i}")
    
    # Add one more - should evict oldest (key_0)
    await working_memory.set("key_10", "value_10")
    
    # key_0 should be gone
    assert await working_memory.exists("key_0") is False
    
    # key_10 should exist
    assert await working_memory.exists("key_10") is True
    
    # Others should still exist
    assert await working_memory.exists("key_9") is True


@pytest.mark.asyncio
async def test_lru_ordering(working_memory):
    """Test LRU moves accessed items to end"""
    # Add 3 items
    await working_memory.set("key_1", "value_1")
    await working_memory.set("key_2", "value_2")
    await working_memory.set("key_3", "value_3")
    
    # Access key_1 (moves to end)
    await working_memory.get("key_1")
    
    # Fill to capacity
    for i in range(4, 11):
        await working_memory.set(f"key_{i}", f"value_{i}")
    
    # Add one more - should evict key_2 (not key_1, which was accessed)
    await working_memory.set("key_11", "value_11")
    
    assert await working_memory.exists("key_1") is True
    assert await working_memory.exists("key_2") is False


@pytest.mark.asyncio
async def test_clear(working_memory):
    """Test clearing all entries"""
    # Add several entries
    for i in range(5):
        await working_memory.set(f"key_{i}", f"value_{i}")
    
    # Clear all
    count = await working_memory.clear()
    
    assert count == 5
    
    # Verify all gone
    for i in range(5):
        assert await working_memory.exists(f"key_{i}") is False


@pytest.mark.asyncio
async def test_list_keys(working_memory):
    """Test listing all keys"""
    # Add entries
    await working_memory.set("vendor:VEN001", "data1")
    await working_memory.set("vendor:VEN002", "data2")
    await working_memory.set("control:CTL001", "data3")
    
    # List all
    all_keys = await working_memory.list_keys()
    assert len(all_keys) == 3
    assert "vendor:VEN001" in all_keys
    
    # List with pattern
    vendor_keys = await working_memory.list_keys("vendor:*")
    assert len(vendor_keys) == 2
    assert "vendor:VEN001" in vendor_keys
    assert "vendor:VEN002" in vendor_keys
    assert "control:CTL001" not in vendor_keys


@pytest.mark.asyncio
async def test_metadata(working_memory):
    """Test storing metadata with entries"""
    metadata = {
        "source": "test",
        "created_by": "pytest",
        "tags": ["vendor", "critical"]
    }
    
    entry = await working_memory.set(
        "meta_key",
        "value",
        metadata=metadata
    )
    
    assert entry.metadata == metadata
    
    # Retrieve and verify metadata preserved
    retrieved = await working_memory.get("meta_key")
    assert retrieved.metadata == metadata
