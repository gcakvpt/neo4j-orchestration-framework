"""
Unit tests for QueryPatternMemory.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from neo4j import AsyncDriver

from neo4j_orchestration.memory.query_patterns import QueryPatternMemory
from neo4j_orchestration.core.types import MemoryType
from neo4j_orchestration.planning.intent import QueryType, EntityType


@pytest.fixture
def mock_driver():
    """Create a mock Neo4j driver."""
    driver = AsyncMock(spec=AsyncDriver)
    return driver


@pytest.fixture
def pattern_memory(mock_driver):
    """Create QueryPatternMemory instance with mock driver."""
    return QueryPatternMemory(mock_driver)


@pytest.mark.asyncio
async def test_initialization(pattern_memory):
    """Test QueryPatternMemory initialization."""
    assert pattern_memory.memory_type == MemoryType.SEMANTIC
    assert pattern_memory.driver is not None


@pytest.mark.asyncio
async def test_record_pattern_new(mock_driver, pattern_memory):
    """Test recording a new pattern."""
    # Setup mock session and result
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_record = {"pattern_id": "test-pattern-id"}
    
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    
    # Mock the context manager
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = None
    
    # Record pattern
    pattern_id = await pattern_memory.record_pattern(
        query_type=QueryType.VENDOR_LIST,
        entities=[EntityType.VENDOR],
        filters={"tier": "Critical"},
        success=True
    )
    
    # Verify
    assert pattern_id == "test-pattern-id"
    assert mock_session.run.called


@pytest.mark.asyncio  
async def test_get_pattern(mock_driver, pattern_memory):
    """Test retrieving a pattern by ID."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    
    mock_node = {
        "query_type": "vendor_list",
        "entities": ["VENDOR"],
        "common_filters": {"tier": "Critical"},
        "frequency": 5,
        "success_rate": 0.8,
        "last_used": datetime.now(),
        "created_at": datetime.now()
    }
    mock_record = {"p": mock_node}
    
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    
    # Mock the context manager
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = None
    
    # Get pattern
    entry = await pattern_memory.get_pattern("test-id")
    
    # Verify
    assert entry is not None
    assert entry.key == "test-id"
    assert entry.value["query_type"] == "vendor_list"
    assert entry.value["frequency"] == 5


@pytest.mark.asyncio
async def test_get_pattern_not_found(mock_driver, pattern_memory):
    """Test getting non-existent pattern."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    mock_session.run = AsyncMock(return_value=mock_result)
    
    # Mock the context manager
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = None
    
    entry = await pattern_memory.get_pattern("nonexistent")
    assert entry is None


@pytest.mark.asyncio
async def test_delete_pattern(mock_driver, pattern_memory):
    """Test deleting a pattern."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_record = {"deleted": 1}
    
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    
    # Mock the context manager
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = None
    
    deleted = await pattern_memory.delete("test-pattern")
    assert deleted is True


@pytest.mark.asyncio
async def test_exists(mock_driver, pattern_memory):
    """Test checking if pattern exists."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_node = {
        "query_type": "vendor_list",
        "entities": ["VENDOR"],
        "common_filters": {},
        "frequency": 1,
        "success_rate": 1.0,
        "last_used": datetime.now(),
        "created_at": datetime.now()
    }
    
    mock_result.single = AsyncMock(return_value={"p": mock_node})
    mock_session.run = AsyncMock(return_value=mock_result)
    
    # Mock the context manager
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = None
    
    exists = await pattern_memory.exists("test-pattern")
    assert exists is True


@pytest.mark.asyncio
async def test_set_not_supported(pattern_memory):
    """Test that set() is not supported."""
    with pytest.raises(NotImplementedError):
        await pattern_memory.set("key", "value")
