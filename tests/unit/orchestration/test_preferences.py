"""
Unit tests for UserPreferenceTracker.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from collections import Counter

from neo4j_orchestration.orchestration.preferences import UserPreferenceTracker
from neo4j_orchestration.memory.query_patterns import QueryPatternMemory
from neo4j_orchestration.planning.intent import QueryIntent, QueryType, EntityType, FilterCondition, FilterOperator
from neo4j_orchestration.execution.result import QueryResult, ExecutionMetadata


@pytest.fixture
def mock_pattern_memory():
    """Create a mock QueryPatternMemory."""
    memory = AsyncMock(spec=QueryPatternMemory)
    # Configure get_common_filters to return empty dict by default
    memory.get_common_filters = AsyncMock(return_value={})
    return memory


@pytest.fixture
def preference_tracker(mock_pattern_memory):
    """Create UserPreferenceTracker instance."""
    return UserPreferenceTracker(
        pattern_memory=mock_pattern_memory,
        session_id="test-session-123"
    )


@pytest.fixture
def sample_intent():
    """Create a sample QueryIntent."""
    return QueryIntent(
        query_type=QueryType.VENDOR_LIST,
        entities=[EntityType.VENDOR],
        filters=[
            FilterCondition(
                field="tier",
                operator=FilterOperator.EQUALS,
                value="Critical"
            )
        ],
        confidence=0.9
    )


@pytest.fixture
def sample_result():
    """Create a sample QueryResult."""
    return QueryResult(
        records=[{"name": "Vendor A"}, {"name": "Vendor B"}],
        metadata=ExecutionMetadata(
            query="MATCH (v:Vendor) RETURN v",
            parameters={},
            result_available_after=50,
            result_consumed_after=55
        ),
        summary="Found 2 vendors"
    )


def test_initialization(preference_tracker):
    """Test UserPreferenceTracker initialization."""
    assert preference_tracker.session_id == "test-session-123"
    assert preference_tracker.pattern_memory is not None
    assert isinstance(preference_tracker._entity_usage, Counter)
    assert isinstance(preference_tracker._filter_usage, dict)


@pytest.mark.asyncio
async def test_record_query_preference(
    preference_tracker,
    mock_pattern_memory,
    sample_intent,
    sample_result
):
    """Test recording query preferences."""
    # Record preference
    await preference_tracker.record_query_preference(
        intent=sample_intent,
        result=sample_result,
        user_satisfied=True
    )
    
    # Verify entity tracking
    assert preference_tracker._entity_usage[EntityType.VENDOR] == 1
    
    # Verify pattern memory was called
    assert mock_pattern_memory.record_pattern.called
    call_args = mock_pattern_memory.record_pattern.call_args
    assert call_args.kwargs["query_type"] == QueryType.VENDOR_LIST
    assert EntityType.VENDOR in call_args.kwargs["entities"]
    assert call_args.kwargs["success"] is True


@pytest.mark.asyncio
async def test_record_multiple_preferences(
    preference_tracker,
    sample_intent,
    sample_result
):
    """Test recording multiple preferences tracks entity usage."""
    # Record same preference multiple times
    for _ in range(3):
        await preference_tracker.record_query_preference(
            intent=sample_intent,
            result=sample_result
        )
    
    # Verify entity count
    assert preference_tracker._entity_usage[EntityType.VENDOR] == 3


@pytest.mark.asyncio
async def test_get_preferred_filters(
    preference_tracker,
    mock_pattern_memory
):
    """Test getting preferred filters."""
    # Setup mock - configure the async method
    mock_pattern_memory.get_common_filters = AsyncMock(return_value={
        "tier": "Critical",
        "status": "Active"
    })
    
    # Get preferred filters
    filters = await preference_tracker.get_preferred_filters(
        query_type=QueryType.VENDOR_RISK,
        min_frequency=2
    )
    
    # Verify
    assert filters["tier"] == "Critical"
    assert filters["status"] == "Active"
    assert mock_pattern_memory.get_common_filters.called


def test_get_preferred_entities_empty(preference_tracker):
    """Test getting preferred entities when none recorded."""
    entities = preference_tracker.get_preferred_entities()
    assert entities == []


def test_get_preferred_entities(preference_tracker):
    """Test getting preferred entities."""
    # Manually add entity usage
    preference_tracker._entity_usage[EntityType.VENDOR] = 5
    preference_tracker._entity_usage[EntityType.RISK] = 3
    preference_tracker._entity_usage[EntityType.CONTROL] = 1
    
    # Get top 2
    entities = preference_tracker.get_preferred_entities(limit=2)
    
    # Verify order (most common first)
    assert len(entities) == 2
    assert entities[0] == EntityType.VENDOR
    assert entities[1] == EntityType.RISK


@pytest.mark.asyncio
async def test_suggest_enhancements(
    preference_tracker,
    mock_pattern_memory,
    sample_intent
):
    """Test suggesting query enhancements."""
    # Setup mock - return filters not in current query
    mock_pattern_memory.get_common_filters = AsyncMock(return_value={
        "tier": "Critical",  # Already in query
        "status": "Active"   # Not in query - should be suggested
    })
    
    # Get suggestions
    suggestions = await preference_tracker.suggest_enhancements(sample_intent)
    
    # Verify - should only suggest "status" (tier already present)
    assert len(suggestions) == 1
    assert suggestions[0]["key"] == "status"
    assert suggestions[0]["value"] == "Active"
    assert suggestions[0]["type"] == "add_filter"
    assert "often use" in suggestions[0]["reason"]


@pytest.mark.asyncio
async def test_suggest_enhancements_no_new_filters(
    preference_tracker,
    mock_pattern_memory,
    sample_intent
):
    """Test suggestions when all common filters already applied."""
    # Setup mock - return filter already in query
    mock_pattern_memory.get_common_filters = AsyncMock(return_value={
        "tier": "Critical"  # Already in query
    })
    
    # Get suggestions
    suggestions = await preference_tracker.suggest_enhancements(sample_intent)
    
    # Verify - no suggestions
    assert len(suggestions) == 0


def test_get_session_stats_empty(preference_tracker):
    """Test session stats with no recorded queries."""
    stats = preference_tracker.get_session_stats()
    
    assert stats["session_id"] == "test-session-123"
    assert stats["total_entities_used"] == 0
    assert stats["unique_entities"] == 0
    assert stats["most_used_entity"] is None
    assert stats["query_types_tracked"] == []


def test_get_session_stats_with_data(preference_tracker):
    """Test session stats with recorded data."""
    # Add some usage data
    preference_tracker._entity_usage[EntityType.VENDOR] = 5
    preference_tracker._entity_usage[EntityType.RISK] = 2
    preference_tracker._filter_usage[QueryType.VENDOR_LIST] = [{"tier": "Critical"}]
    
    stats = preference_tracker.get_session_stats()
    
    assert stats["session_id"] == "test-session-123"
    assert stats["total_entities_used"] == 7  # 5 + 2
    assert stats["unique_entities"] == 2
    assert stats["most_used_entity"] == "Vendor"  # EntityType.VENDOR.value is "Vendor"
    assert QueryType.VENDOR_LIST in stats["query_types_tracked"]
