"""
Unit tests for PatternEnhancedClassifier.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from neo4j_orchestration.orchestration.pattern_classifier import PatternEnhancedClassifier
from neo4j_orchestration.planning.classifier import QueryIntentClassifier
from neo4j_orchestration.orchestration.preferences import UserPreferenceTracker
from neo4j_orchestration.planning.intent import (
    QueryIntent, QueryType, EntityType, FilterCondition, FilterOperator
)


@pytest.fixture
def mock_base_classifier():
    """Create a mock QueryIntentClassifier."""
    classifier = MagicMock(spec=QueryIntentClassifier)
    # Default return value
    classifier.classify.return_value = QueryIntent(
        query_type=QueryType.VENDOR_LIST,
        entities=[EntityType.VENDOR],
        filters=[],
        confidence=0.9
    )
    return classifier


@pytest.fixture
def mock_preference_tracker():
    """Create a mock UserPreferenceTracker."""
    tracker = AsyncMock(spec=UserPreferenceTracker)
    # Default: no suggestions
    tracker.suggest_enhancements = AsyncMock(return_value=[])
    tracker.get_session_stats.return_value = {
        "session_id": "test-session",
        "total_entities_used": 5,
        "unique_entities": 2
    }
    return tracker


@pytest.fixture
def pattern_classifier(mock_base_classifier, mock_preference_tracker):
    """Create PatternEnhancedClassifier with mocks."""
    return PatternEnhancedClassifier(
        base_classifier=mock_base_classifier,
        preference_tracker=mock_preference_tracker
    )


@pytest.fixture
def pattern_classifier_no_tracker(mock_base_classifier):
    """Create PatternEnhancedClassifier without tracker."""
    return PatternEnhancedClassifier(
        base_classifier=mock_base_classifier,
        preference_tracker=None
    )


def test_initialization(pattern_classifier, mock_base_classifier, mock_preference_tracker):
    """Test PatternEnhancedClassifier initialization."""
    assert pattern_classifier.base_classifier is mock_base_classifier
    assert pattern_classifier.preference_tracker is mock_preference_tracker


def test_initialization_without_tracker(mock_base_classifier):
    """Test initialization without preference tracker."""
    classifier = PatternEnhancedClassifier(
        base_classifier=mock_base_classifier,
        preference_tracker=None
    )
    assert classifier.base_classifier is mock_base_classifier
    assert classifier.preference_tracker is None


@pytest.mark.asyncio
async def test_classify_without_tracker(
    pattern_classifier_no_tracker,
    mock_base_classifier
):
    """Test classification without preference tracker."""
    # Classify
    result = await pattern_classifier_no_tracker.classify("list vendors")
    
    # Verify base classifier was called
    mock_base_classifier.classify.assert_called_once_with("list vendors")
    
    # Verify result is from base classifier
    assert result.query_type == QueryType.VENDOR_LIST
    assert len(result.filters) == 0


@pytest.mark.asyncio
async def test_classify_without_enhancements(
    pattern_classifier,
    mock_base_classifier,
    mock_preference_tracker
):
    """Test classification with tracker but enhancements disabled."""
    # Classify with enhancements disabled
    result = await pattern_classifier.classify(
        "list vendors",
        apply_enhancements=False
    )
    
    # Verify base classifier was called
    mock_base_classifier.classify.assert_called_once_with("list vendors")
    
    # Verify preference tracker was NOT called
    mock_preference_tracker.suggest_enhancements.assert_not_called()
    
    # Verify result is from base classifier
    assert result.query_type == QueryType.VENDOR_LIST
    assert len(result.filters) == 0


@pytest.mark.asyncio
async def test_classify_with_enhancements(
    pattern_classifier,
    mock_base_classifier,
    mock_preference_tracker
):
    """Test classification with enhancements applied."""
    # Setup suggestion
    mock_preference_tracker.suggest_enhancements = AsyncMock(return_value=[
        {
            "type": "add_filter",
            "key": "status",
            "value": "Active",
            "reason": "You often use this filter"
        }
    ])
    
    # Classify
    result = await pattern_classifier.classify("list vendors")
    
    # Verify both classifiers were called
    mock_base_classifier.classify.assert_called_once_with("list vendors")
    mock_preference_tracker.suggest_enhancements.assert_called_once()
    
    # Verify enhancement was applied
    assert len(result.filters) == 1
    assert result.filters[0].field == "status"
    assert result.filters[0].value == "Active"
    assert result.filters[0].operator == FilterOperator.EQUALS


@pytest.mark.asyncio
async def test_enhancement_adds_filters(
    pattern_classifier,
    mock_preference_tracker
):
    """Test that enhancements correctly add filters."""
    # Setup multiple suggestions
    mock_preference_tracker.suggest_enhancements = AsyncMock(return_value=[
        {
            "type": "add_filter",
            "key": "status",
            "value": "Active",
            "reason": "Common filter"
        },
        {
            "type": "add_filter",
            "key": "tier",
            "value": "Critical",
            "reason": "Frequently used"
        }
    ])
    
    # Classify
    result = await pattern_classifier.classify("list vendors")
    
    # Verify both filters were added
    assert len(result.filters) == 2
    
    # Check first filter
    assert result.filters[0].field == "status"
    assert result.filters[0].value == "Active"
    
    # Check second filter
    assert result.filters[1].field == "tier"
    assert result.filters[1].value == "Critical"


@pytest.mark.asyncio
async def test_enhancement_metadata(
    pattern_classifier,
    mock_preference_tracker
):
    """Test that enhancement metadata is recorded."""
    # Setup suggestion
    mock_preference_tracker.suggest_enhancements = AsyncMock(return_value=[
        {
            "type": "add_filter",
            "key": "status",
            "value": "Active",
            "reason": "You often use this filter for vendor queries"
        }
    ])
    
    # Classify
    result = await pattern_classifier.classify("list vendors")
    
    # Verify metadata was added
    assert "pattern_enhancements" in result.metadata
    assert len(result.metadata["pattern_enhancements"]) == 1
    assert "You often use this filter" in result.metadata["pattern_enhancements"][0]


@pytest.mark.asyncio
async def test_no_enhancements_needed(
    pattern_classifier,
    mock_preference_tracker
):
    """Test when no enhancements are suggested."""
    # Setup: no suggestions
    mock_preference_tracker.suggest_enhancements = AsyncMock(return_value=[])
    
    # Classify
    result = await pattern_classifier.classify("list vendors")
    
    # Verify no filters were added
    assert len(result.filters) == 0
    
    # Verify no metadata was added
    assert "pattern_enhancements" not in result.metadata


def test_get_stats_without_tracker(pattern_classifier_no_tracker):
    """Test get_enhancement_stats without tracker."""
    stats = pattern_classifier_no_tracker.get_enhancement_stats()
    
    assert stats["tracker_enabled"] is False
    assert stats["session_stats"] == {}


def test_get_stats_with_tracker(pattern_classifier, mock_preference_tracker):
    """Test get_enhancement_stats with tracker."""
    stats = pattern_classifier.get_enhancement_stats()
    
    assert stats["tracker_enabled"] is True
    assert "session_stats" in stats
    assert stats["session_stats"]["session_id"] == "test-session"
    assert stats["session_stats"]["total_entities_used"] == 5
    
    # Verify tracker was called
    mock_preference_tracker.get_session_stats.assert_called_once()
