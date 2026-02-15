"""
Unit tests for Episodic Memory.

Tests episodic memory operations using a mock Neo4j driver.
Integration tests with real Neo4j are in tests/integration/.
"""

import pytest
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, call

from neo4j_orchestration.memory import EpisodicMemory
from neo4j_orchestration.core.types import MemoryType, MemoryEntry
from neo4j_orchestration.core.exceptions import (
    MemoryError,
    ValidationError,
)


@pytest.fixture
def mock_driver():
    """Create a mock Neo4j async driver."""
    driver = MagicMock()
    return driver


@pytest.fixture
def mock_session():
    """Create a mock Neo4j session."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    return session


@pytest.fixture
def episodic_memory(mock_driver):
    """Create an EpisodicMemory instance with mock driver."""
    return EpisodicMemory(driver=mock_driver)


@pytest.mark.asyncio
async def test_episodic_memory_initialization(episodic_memory):
    """Test episodic memory initializes correctly."""
    assert episodic_memory.memory_type == MemoryType.EPISODIC
    assert episodic_memory.driver is not None


@pytest.mark.asyncio
async def test_save_session(episodic_memory, mock_driver, mock_session):
    """Test saving a session."""
    # Setup mock
    mock_result = AsyncMock()
    mock_record = {"session_id": "sess_001"}
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    # Save session
    session_id = await episodic_memory.save_session(
        session_id="sess_001",
        workflow="vendor_risk_analysis",
        entities=["VEN001", "VEN002"],
        results={"risk_score": 85},
        metadata={"analyst": "gokul"}
    )
    
    assert session_id == "sess_001"
    mock_session.run.assert_called_once()


@pytest.mark.asyncio
async def test_save_session_validation(episodic_memory):
    """Test save_session validates required fields."""
    # Empty session_id
    with pytest.raises(ValidationError) as exc_info:
        await episodic_memory.save_session(
            session_id="",
            workflow="test",
            entities=[],
            results={}
        )
    assert "Session ID and workflow are required" in str(exc_info.value)
    
    # Empty workflow
    with pytest.raises(ValidationError) as exc_info:
        await episodic_memory.save_session(
            session_id="sess_001",
            workflow="",
            entities=[],
            results={}
        )
    assert "Session ID and workflow are required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_save_session_with_previous(episodic_memory, mock_driver, mock_session):
    """Test saving a session linked to previous session."""
    mock_result = AsyncMock()
    mock_record = {"session_id": "sess_002"}
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    session_id = await episodic_memory.save_session(
        session_id="sess_002",
        workflow="vendor_risk_analysis",
        entities=["VEN001"],
        results={"risk_score": 90},
        previous_session_id="sess_001"
    )
    
    assert session_id == "sess_002"
    # Verify previous_session_id was passed to query
    call_args = mock_session.run.call_args
    assert call_args.kwargs["previous_session_id"] == "sess_001"


@pytest.mark.asyncio
async def test_get_session(episodic_memory, mock_driver, mock_session):
    """Test retrieving a session by ID."""
    mock_result = AsyncMock()
    mock_record = {
        "id": "sess_001",
        "workflow": "vendor_risk_analysis",
        "timestamp": datetime.utcnow(),
        "results": {"risk_score": 85},
        "metadata": {"analyst": "gokul"},
        "entities": ["VEN001", "VEN002"]
    }
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    entry = await episodic_memory.get("sess_001")
    
    assert entry is not None
    assert entry.key == "sess_001"
    assert entry.value["workflow"] == "vendor_risk_analysis"
    assert entry.value["entities"] == ["VEN001", "VEN002"]
    assert entry.memory_type == MemoryType.EPISODIC


@pytest.mark.asyncio
async def test_get_nonexistent_session(episodic_memory, mock_driver, mock_session):
    """Test getting a session that doesn't exist returns None."""
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    entry = await episodic_memory.get("nonexistent")
    
    assert entry is None


@pytest.mark.asyncio
async def test_exists(episodic_memory, mock_driver, mock_session):
    """Test checking if a session exists."""
    mock_result = AsyncMock()
    mock_record = {"exists": True}
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    exists = await episodic_memory.exists("sess_001")
    
    assert exists is True


@pytest.mark.asyncio
async def test_set_not_supported(episodic_memory):
    """Test that direct set() is not supported."""
    with pytest.raises(MemoryError) as exc_info:
        await episodic_memory.set("key", "value")
    assert "not supported for episodic memory" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_not_supported(episodic_memory):
    """Test that delete() is not supported (immutable)."""
    with pytest.raises(MemoryError) as exc_info:
        await episodic_memory.delete("sess_001")
    assert "immutable history" in str(exc_info.value)


@pytest.mark.asyncio
async def test_clear(episodic_memory, mock_driver, mock_session):
    """Test clearing all sessions."""
    mock_session.run = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    await episodic_memory.clear()
    
    mock_session.run.assert_called_once()
    # Verify DETACH DELETE was called
    call_args = mock_session.run.call_args
    assert "DETACH DELETE" in call_args.args[0]


@pytest.mark.asyncio
async def test_list_keys(episodic_memory, mock_driver, mock_session):
    """Test listing session IDs."""
    mock_result = AsyncMock()
    mock_result.values = AsyncMock(return_value=[
        ["sess_003"],
        ["sess_002"],
        ["sess_001"]
    ])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    keys = await episodic_memory.list_keys()
    
    assert keys == ["sess_003", "sess_002", "sess_001"]


@pytest.mark.asyncio
async def test_list_keys_with_pattern(episodic_memory, mock_driver, mock_session):
    """Test listing session IDs with workflow filter."""
    mock_result = AsyncMock()
    mock_result.values = AsyncMock(return_value=[["sess_001"]])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    keys = await episodic_memory.list_keys(pattern="vendor_risk")
    
    assert keys == ["sess_001"]
    # Verify pattern was passed
    call_args = mock_session.run.call_args
    assert call_args.kwargs["pattern"] == "vendor_risk"


@pytest.mark.asyncio
async def test_get_sessions_by_entity(episodic_memory, mock_driver, mock_session):
    """Test getting sessions for a specific entity."""
    # Create async iterator for records
    async def async_iter():
        yield {
            "id": "sess_001",
            "workflow": "vendor_risk_analysis",
            "timestamp": datetime.utcnow(),
            "results": {"risk_score": 85},
            "metadata": {"analyst": "gokul"},
            "entities": ["VEN001", "VEN002"]
        }
        yield {
            "id": "sess_002",
            "workflow": "vendor_assessment",
            "timestamp": datetime.utcnow(),
            "results": {"status": "approved"},
            "metadata": {},
            "entities": ["VEN001"]
        }
    
    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    sessions = await episodic_memory.get_sessions_by_entity("VEN001", limit=10)
    
    assert len(sessions) == 2
    assert all(isinstance(s, MemoryEntry) for s in sessions)
    assert sessions[0].key == "sess_001"
    assert sessions[1].key == "sess_002"


@pytest.mark.asyncio
async def test_get_recent_sessions(episodic_memory, mock_driver, mock_session):
    """Test getting recent sessions."""
    async def async_iter():
        yield {
            "id": "sess_003",
            "workflow": "vendor_risk_analysis",
            "timestamp": datetime.utcnow(),
            "results": {},
            "metadata": {},
            "entities": ["VEN003"]
        }
    
    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    sessions = await episodic_memory.get_recent_sessions(days=7, limit=50)
    
    assert len(sessions) == 1
    assert sessions[0].key == "sess_003"


@pytest.mark.asyncio
async def test_get_recent_sessions_with_workflow(episodic_memory, mock_driver, mock_session):
    """Test getting recent sessions filtered by workflow."""
    async def async_iter():
        yield {
            "id": "sess_001",
            "workflow": "vendor_risk_analysis",
            "timestamp": datetime.utcnow(),
            "results": {},
            "metadata": {},
            "entities": []
        }
    
    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    sessions = await episodic_memory.get_recent_sessions(
        days=7,
        workflow="vendor_risk_analysis",
        limit=50
    )
    
    assert len(sessions) == 1
    # Verify workflow filter was passed
    call_args = mock_session.run.call_args
    assert call_args.kwargs["workflow"] == "vendor_risk_analysis"


@pytest.mark.asyncio
async def test_get_session_chain(episodic_memory, mock_driver, mock_session):
    """Test getting a session chain (conversation thread)."""
    async def async_iter():
        # Return in chronological order
        yield {
            "id": "sess_001",
            "workflow": "vendor_risk_analysis",
            "timestamp": datetime.utcnow() - timedelta(hours=2),
            "results": {"step": 1},
            "metadata": {},
            "entities": ["VEN001"]
        }
        yield {
            "id": "sess_002",
            "workflow": "vendor_risk_analysis",
            "timestamp": datetime.utcnow() - timedelta(hours=1),
            "results": {"step": 2},
            "metadata": {},
            "entities": ["VEN001"]
        }
        yield {
            "id": "sess_003",
            "workflow": "vendor_risk_analysis",
            "timestamp": datetime.utcnow(),
            "results": {"step": 3},
            "metadata": {},
            "entities": ["VEN001"]
        }
    
    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    chain = await episodic_memory.get_session_chain("sess_003", max_depth=10)
    
    assert len(chain) == 3
    # Verify chronological order
    assert chain[0].key == "sess_001"
    assert chain[1].key == "sess_002"
    assert chain[2].key == "sess_003"
