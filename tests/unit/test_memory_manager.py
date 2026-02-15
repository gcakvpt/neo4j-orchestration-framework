"""
Unit tests for Memory Manager.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from neo4j import AsyncDriver

from src.neo4j_orchestration.memory.manager import MemoryManager, MemoryType
from src.neo4j_orchestration.core.types import MemoryEntry
from src.neo4j_orchestration.core.exceptions import ValidationError, MemoryError


@pytest.fixture
def mock_driver():
    """Create mock Neo4j driver."""
    driver = MagicMock(spec=AsyncDriver)
    return driver


@pytest.fixture
def memory_manager(mock_driver):
    """Create MemoryManager instance with mocked driver."""
    manager = MemoryManager(
        working_config={"max_size": 100, "default_ttl": 3600},
        neo4j_driver=mock_driver,
        auto_initialize=True
    )
    return manager


@pytest.fixture
def manager_without_driver():
    """Create MemoryManager without Neo4j driver."""
    return MemoryManager(
        working_config={"max_size": 50},
        neo4j_driver=None,
        auto_initialize=True
    )


class TestMemoryManagerInitialization:
    """Test MemoryManager initialization."""
    
    def test_initialization_with_all_backends(self, mock_driver):
        """Test initialization with all memory backends."""
        manager = MemoryManager(
            working_config={"max_size": 100},
            neo4j_driver=mock_driver,
            auto_initialize=True
        )
        
        assert manager._working is not None
        assert manager._episodic is not None
        assert manager._semantic is not None
    
    def test_initialization_without_neo4j(self):
        """Test initialization without Neo4j driver."""
        manager = MemoryManager(
            working_config={"max_size": 100},
            neo4j_driver=None,
            auto_initialize=True
        )
        
        assert manager._working is not None
        assert manager._episodic is None
        assert manager._semantic is None
    
    def test_initialization_no_auto_init(self, mock_driver):
        """Test initialization without auto-initialize."""
        manager = MemoryManager(
            working_config={"max_size": 100},
            neo4j_driver=mock_driver,
            auto_initialize=False
        )
        
        assert manager._working is None
        assert manager._episodic is None
        assert manager._semantic is None


class TestMemoryManagerProperties:
    """Test MemoryManager property accessors."""
    
    def test_working_property(self, memory_manager):
        """Test working memory property."""
        working = memory_manager.working
        assert working is not None
        assert working == memory_manager._working
    
    def test_episodic_property(self, memory_manager):
        """Test episodic memory property."""
        episodic = memory_manager.episodic
        assert episodic is not None
        assert episodic == memory_manager._episodic
    
    def test_semantic_property(self, memory_manager):
        """Test semantic memory property."""
        semantic = memory_manager.semantic
        assert semantic is not None
        assert semantic == memory_manager._semantic
    
    def test_episodic_property_without_driver(self, manager_without_driver):
        """Test episodic property raises error without driver."""
        with pytest.raises(MemoryError) as exc_info:
            _ = manager_without_driver.episodic
        
        assert "requires Neo4j driver" in str(exc_info.value)
    
    def test_semantic_property_without_driver(self, manager_without_driver):
        """Test semantic property raises error without driver."""
        with pytest.raises(MemoryError) as exc_info:
            _ = manager_without_driver.semantic
        
        assert "requires Neo4j driver" in str(exc_info.value)
    
    def test_lazy_initialization(self, mock_driver):
        """Test lazy initialization of memory backends."""
        manager = MemoryManager(
            working_config={"max_size": 100},
            neo4j_driver=mock_driver,
            auto_initialize=False
        )
        
        # Initially None
        assert manager._working is None
        
        # Access triggers initialization
        working = manager.working
        assert working is not None
        assert manager._working is not None


class TestGetMemory:
    """Test get_memory method."""
    
    def test_get_working_memory(self, memory_manager):
        """Test getting working memory backend."""
        memory = memory_manager.get_memory(MemoryType.WORKING)
        assert memory == memory_manager.working
    
    def test_get_episodic_memory(self, memory_manager):
        """Test getting episodic memory backend."""
        memory = memory_manager.get_memory(MemoryType.EPISODIC)
        assert memory == memory_manager.episodic
    
    def test_get_semantic_memory(self, memory_manager):
        """Test getting semantic memory backend."""
        memory = memory_manager.get_memory(MemoryType.SEMANTIC)
        assert memory == memory_manager.semantic
    
    def test_get_memory_with_string(self, memory_manager):
        """Test getting memory with string type."""
        memory = memory_manager.get_memory("working")
        assert memory == memory_manager.working
        
        memory = memory_manager.get_memory("EPISODIC")
        assert memory == memory_manager.episodic
    
    def test_get_memory_invalid_type(self, memory_manager):
        """Test getting memory with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            memory_manager.get_memory("invalid")
        
        assert "Invalid memory type" in str(exc_info.value)


class TestRoutedOperations:
    """Test routed memory operations."""
    
    @pytest.mark.asyncio
    async def test_set_to_working_memory(self, memory_manager):
        """Test set operation routed to working memory."""
        await memory_manager.set("test_key", {"value": 123}, memory_type=MemoryType.WORKING)
        
        entry = await memory_manager.working.get("test_key")
        assert entry is not None
        assert entry.value == {"value": 123}
    
    @pytest.mark.asyncio
    async def test_get_from_working_memory(self, memory_manager):
        """Test get operation routed to working memory."""
        await memory_manager.working.set("test_key", {"value": 456})
        
        entry = await memory_manager.get("test_key", memory_type=MemoryType.WORKING)
        assert entry is not None
        assert entry.value == {"value": 456}
    
    @pytest.mark.asyncio
    async def test_exists_in_working_memory(self, memory_manager):
        """Test exists operation routed to working memory."""
        await memory_manager.working.set("test_key", {"value": 789})
        
        exists = await memory_manager.exists("test_key", memory_type=MemoryType.WORKING)
        assert exists is True
        
        exists = await memory_manager.exists("nonexistent", memory_type=MemoryType.WORKING)
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_delete_from_working_memory(self, memory_manager):
        """Test delete operation routed to working memory."""
        await memory_manager.working.set("test_key", {"value": 999})
        
        deleted = await memory_manager.delete("test_key", memory_type=MemoryType.WORKING)
        assert deleted is True
        
        exists = await memory_manager.working.exists("test_key")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_clear_working_memory(self, memory_manager):
        """Test clear operation routed to working memory."""
        await memory_manager.working.set("key1", {"value": 1})
        await memory_manager.working.set("key2", {"value": 2})
        
        count = await memory_manager.clear(memory_type=MemoryType.WORKING)
        assert count == 2
        
        keys = await memory_manager.working.list_keys()
        assert len(keys) == 0
    
    @pytest.mark.asyncio
    async def test_list_keys_from_working_memory(self, memory_manager):
        """Test list_keys operation routed to working memory."""
        await memory_manager.working.set("test:key1", {"value": 1})
        await memory_manager.working.set("test:key2", {"value": 2})
        await memory_manager.working.set("other:key", {"value": 3})
        
        all_keys = await memory_manager.list_keys(memory_type=MemoryType.WORKING)
        assert len(all_keys) == 3
        assert "test:key1" in all_keys
        assert "test:key2" in all_keys
        assert "other:key" in all_keys


class TestGetStats:
    """Test get_stats method."""
    
    @pytest.mark.asyncio
    async def test_get_stats_all_initialized(self, memory_manager):
        """Test get_stats with all backends initialized."""
        # Add some data
        await memory_manager.working.set("key1", {"value": 1})
        await memory_manager.working.set("key2", {"value": 2})
        
        stats = await memory_manager.get_stats()
        
        assert "working" in stats
        assert stats["working"]["initialized"] is True
        assert stats["working"]["key_count"] == 2
        assert stats["working"]["max_size"] == 100
        assert stats["working"]["default_ttl"] == 3600
        
        assert "episodic" in stats
        assert stats["episodic"]["initialized"] is True
        
        assert "semantic" in stats
        assert stats["semantic"]["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_get_stats_working_only(self, manager_without_driver):
        """Test get_stats with only working memory."""
        await manager_without_driver.working.set("key1", {"value": 1})
        
        stats = await manager_without_driver.get_stats()
        
        assert stats["working"]["initialized"] is True
        assert stats["working"]["key_count"] == 1
        assert stats["episodic"]["initialized"] is False
        assert stats["semantic"]["initialized"] is False
    
    @pytest.mark.asyncio
    async def test_get_stats_no_data(self, memory_manager):
        """Test get_stats with no data."""
        stats = await memory_manager.get_stats()
        
        assert stats["working"]["key_count"] == 0
        assert stats["episodic"]["session_count"] == 0
        assert stats["semantic"]["rule_count"] == 0


class TestClose:
    """Test close method."""
    
    @pytest.mark.asyncio
    async def test_close_clears_working_memory(self, memory_manager):
        """Test close clears working memory."""
        await memory_manager.working.set("key1", {"value": 1})
        await memory_manager.working.set("key2", {"value": 2})
        
        await memory_manager.close()
        
        keys = await memory_manager.working.list_keys()
        assert len(keys) == 0


class TestMemoryType:
    """Test MemoryType enum."""
    
    def test_memory_type_values(self):
        """Test MemoryType enum values."""
        assert MemoryType.WORKING.value == "working"
        assert MemoryType.EPISODIC.value == "episodic"
        assert MemoryType.SEMANTIC.value == "semantic"
    
    def test_memory_type_string_conversion(self):
        """Test MemoryType string conversion."""
        assert MemoryType.WORKING.value == "working"
        assert MemoryType.EPISODIC.value == "episodic"
        assert MemoryType.SEMANTIC.value == "semantic"
