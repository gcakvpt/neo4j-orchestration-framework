"""
Unit tests for Semantic Memory.

Tests semantic memory operations using a mock Neo4j driver.
Integration tests with real Neo4j are in tests/integration/.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from neo4j_orchestration.memory import SemanticMemory
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
def semantic_memory(mock_driver):
    """Create a SemanticMemory instance with mock driver."""
    return SemanticMemory(driver=mock_driver)


@pytest.mark.asyncio
async def test_semantic_memory_initialization(semantic_memory):
    """Test semantic memory initializes correctly."""
    assert semantic_memory.memory_type == MemoryType.SEMANTIC
    assert semantic_memory.driver is not None


@pytest.mark.asyncio
async def test_store_rule(semantic_memory, mock_driver, mock_session):
    """Test storing a new rule."""
    # Setup mocks for version check
    version_result = AsyncMock()
    version_result.single = AsyncMock(return_value={"max_version": None})
    
    # Setup mocks for rule creation
    create_result = AsyncMock()
    create_result.single = AsyncMock(return_value={"version": 1})
    
    mock_session.run = AsyncMock(side_effect=[version_result, create_result])
    mock_driver.session = MagicMock(return_value=mock_session)
    
    # Store rule
    version = await semantic_memory.store_rule(
        rule_id="RULE_VR_001",
        category="vendor_risk",
        content={"condition": "risk_score >= 85"},
        tags=["vendor", "risk"],
        metadata={"created_by": "gokul"}
    )
    
    assert version == 1
    assert mock_session.run.call_count == 2  # Version check + create


@pytest.mark.asyncio
async def test_store_rule_validation(semantic_memory):
    """Test store_rule validates required fields."""
    # Empty rule_id
    with pytest.raises(ValidationError) as exc_info:
        await semantic_memory.store_rule(
            rule_id="",
            category="test",
            content={}
        )
    assert "Rule ID and category are required" in str(exc_info.value)
    
    # Empty category
    with pytest.raises(ValidationError) as exc_info:
        await semantic_memory.store_rule(
            rule_id="RULE_001",
            category="",
            content={}
        )
    assert "Rule ID and category are required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_store_rule_with_version(semantic_memory, mock_driver, mock_session):
    """Test storing a new version of existing rule."""
    # When previous_version is provided, only create query runs (no version check)
    create_result = AsyncMock()
    create_result.single = AsyncMock(return_value={"version": 2})
    
    mock_session.run = AsyncMock(return_value=create_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    version = await semantic_memory.store_rule(
        rule_id="RULE_VR_001",
        category="vendor_risk",
        content={"condition": "risk_score >= 90"},  # Updated
        previous_version=1
    )
    
    assert version == 2
    assert mock_session.run.call_count == 1  # Only create, no version check


@pytest.mark.asyncio
async def test_get_current_rule(semantic_memory, mock_driver, mock_session):
    """Test retrieving current version of a rule."""
    mock_result = AsyncMock()
    mock_record = {
        "id": "RULE_VR_001",
        "version": 2,
        "category": "vendor_risk",
        "content": {"condition": "risk_score >= 90"},
        "is_active": True,
        "created_at": datetime.utcnow(),
        "metadata": {"created_by": "gokul"},
        "tags": ["vendor", "risk"],
        "dependencies": []
    }
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    entry = await semantic_memory.get_current_rule("RULE_VR_001")
    
    assert entry is not None
    assert entry.value["id"] == "RULE_VR_001"
    assert entry.value["version"] == 2
    assert entry.value["is_active"] is True
    assert entry.memory_type == MemoryType.SEMANTIC


@pytest.mark.asyncio
async def test_get_nonexistent_rule(semantic_memory, mock_driver, mock_session):
    """Test getting a rule that doesn't exist returns None."""
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    entry = await semantic_memory.get_current_rule("NONEXISTENT")
    
    assert entry is None


@pytest.mark.asyncio
async def test_get_rule_version(semantic_memory, mock_driver, mock_session):
    """Test retrieving a specific rule version."""
    mock_result = AsyncMock()
    mock_record = {
        "id": "RULE_VR_001",
        "version": 1,
        "category": "vendor_risk",
        "content": {"condition": "risk_score >= 85"},
        "is_active": False,  # Old version
        "created_at": datetime.utcnow(),
        "metadata": {},
        "tags": ["vendor"],
        "dependencies": []
    }
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    entry = await semantic_memory.get_rule_version("RULE_VR_001", version=1)
    
    assert entry is not None
    assert entry.value["version"] == 1
    assert entry.value["is_active"] is False


@pytest.mark.asyncio
async def test_get_rule_history(semantic_memory, mock_driver, mock_session):
    """Test getting all versions of a rule."""
    async def async_iter():
        yield {
            "id": "RULE_VR_001",
            "version": 1,
            "category": "vendor_risk",
            "content": {"condition": "risk_score >= 85"},
            "is_active": False,
            "created_at": datetime.utcnow(),
            "metadata": {},
            "tags": ["vendor"]
        }
        yield {
            "id": "RULE_VR_001",
            "version": 2,
            "category": "vendor_risk",
            "content": {"condition": "risk_score >= 90"},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "metadata": {},
            "tags": ["vendor", "risk"]
        }
    
    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    history = await semantic_memory.get_rule_history("RULE_VR_001")
    
    assert len(history) == 2
    assert history[0].value["version"] == 1
    assert history[1].value["version"] == 2


@pytest.mark.asyncio
async def test_get_rules_by_category(semantic_memory, mock_driver, mock_session):
    """Test getting rules by category."""
    async def async_iter():
        yield {
            "id": "RULE_VR_001",
            "version": 1,
            "category": "vendor_risk",
            "content": {},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "metadata": {},
            "tags": ["vendor"]
        }
        yield {
            "id": "RULE_VR_002",
            "version": 1,
            "category": "vendor_risk",
            "content": {},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "metadata": {},
            "tags": ["vendor"]
        }
    
    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    rules = await semantic_memory.get_rules_by_category("vendor_risk")
    
    assert len(rules) == 2
    assert all(r.value["category"] == "vendor_risk" for r in rules)


@pytest.mark.asyncio
async def test_get_rules_by_tag(semantic_memory, mock_driver, mock_session):
    """Test getting rules by tag."""
    async def async_iter():
        yield {
            "id": "RULE_VR_001",
            "version": 1,
            "category": "vendor_risk",
            "content": {},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "metadata": {},
            "tags": ["vendor", "approval"]
        }
    
    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    rules = await semantic_memory.get_rules_by_tag("approval")
    
    assert len(rules) == 1
    assert "approval" in rules[0].value["tags"]


@pytest.mark.asyncio
async def test_deactivate_rule(semantic_memory, mock_driver, mock_session):
    """Test deactivating a rule."""
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"deactivated": True})
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    result = await semantic_memory.deactivate_rule("RULE_VR_001")
    
    assert result is True


@pytest.mark.asyncio
async def test_exists(semantic_memory, mock_driver, mock_session):
    """Test checking if an active rule exists."""
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"exists": True})
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    exists = await semantic_memory.exists("RULE_VR_001")
    
    assert exists is True


@pytest.mark.asyncio
async def test_set_not_supported(semantic_memory):
    """Test that direct set() is not supported."""
    with pytest.raises(MemoryError) as exc_info:
        await semantic_memory.set("key", "value")
    assert "not supported for semantic memory" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_not_supported(semantic_memory):
    """Test that delete() is not supported."""
    with pytest.raises(MemoryError) as exc_info:
        await semantic_memory.delete("RULE_001")
    assert "Use deactivate_rule()" in str(exc_info.value)


@pytest.mark.asyncio
async def test_clear(semantic_memory, mock_driver, mock_session):
    """Test clearing all rules."""
    mock_session.run = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    await semantic_memory.clear()
    
    mock_session.run.assert_called_once()


@pytest.mark.asyncio
async def test_list_keys(semantic_memory, mock_driver, mock_session):
    """Test listing active rule IDs."""
    mock_result = AsyncMock()
    mock_result.values = AsyncMock(return_value=[
        ["RULE_VR_001"],
        ["RULE_VR_002"],
        ["RULE_CM_001"]
    ])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    keys = await semantic_memory.list_keys()
    
    assert keys == ["RULE_VR_001", "RULE_VR_002", "RULE_CM_001"]


@pytest.mark.asyncio
async def test_list_keys_with_pattern(semantic_memory, mock_driver, mock_session):
    """Test listing rule IDs with category filter."""
    mock_result = AsyncMock()
    mock_result.values = AsyncMock(return_value=[
        ["RULE_VR_001"],
        ["RULE_VR_002"]
    ])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    keys = await semantic_memory.list_keys(pattern="vendor")
    
    assert keys == ["RULE_VR_001", "RULE_VR_002"]


@pytest.mark.asyncio
async def test_get_delegates_to_get_current_rule(semantic_memory, mock_driver, mock_session):
    """Test that get() delegates to get_current_rule()."""
    mock_result = AsyncMock()
    mock_record = {
        "id": "RULE_001",
        "version": 1,
        "category": "test",
        "content": {},
        "is_active": True,
        "created_at": datetime.utcnow(),
        "metadata": {},
        "tags": [],
        "dependencies": []
    }
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_driver.session = MagicMock(return_value=mock_session)
    
    entry = await semantic_memory.get("RULE_001")
    
    assert entry is not None
    assert entry.value["id"] == "RULE_001"
