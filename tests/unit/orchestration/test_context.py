"""
Unit tests for ConversationContext
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from neo4j_orchestration.orchestration.context import ConversationContext
from neo4j_orchestration.planning.intent import QueryIntent, QueryType, EntityType
from neo4j_orchestration.execution.result import QueryResult, ExecutionMetadata
from neo4j_orchestration.core.types import MemoryEntry, MemoryType


@pytest.fixture
def mock_working_memory():
    """Create mock WorkingMemory."""
    memory = Mock()
    memory.get = AsyncMock(return_value=None)
    memory.set = AsyncMock()
    memory.delete = AsyncMock()
    return memory


@pytest.fixture
def sample_intent():
    """Create sample QueryIntent."""
    return QueryIntent(
        query_type=QueryType.VENDOR_LIST,
        entities=[EntityType.VENDOR],
        filters=[],
        aggregations=[],
        sort_by=None,
        sort_order="ASC",  # Changed to uppercase
        limit=None,
        include_relationships=False,
        confidence=0.9
    )


@pytest.fixture
def sample_result():
    """Create sample QueryResult."""
    return QueryResult(
        records=[{"name": "Vendor A"}, {"name": "Vendor B"}],
        summary="Query completed successfully",
        metadata=ExecutionMetadata(
            query="MATCH (v:Vendor) RETURN v",
            parameters={},
            result_available_after=10,
            result_consumed_after=20
        )
    )


class TestConversationContext:
    """Test ConversationContext class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_working_memory):
        """Test context initialization."""
        context = ConversationContext(
            working_memory=mock_working_memory,
            session_id="test_session",
            max_history=5
        )
        
        assert context.session_id == "test_session"
        assert context.max_history == 5
        assert context._history_key == "conversation:test_session:history"
    
    @pytest.mark.asyncio
    async def test_add_query_creates_new_history(
        self,
        mock_working_memory,
        sample_intent,
        sample_result
    ):
        """Test adding first query creates new history."""
        context = ConversationContext(mock_working_memory, "session1")
        
        await context.add_query(
            query="Show all vendors",
            intent=sample_intent,
            result=sample_result
        )
        
        # Should check for existing history
        mock_working_memory.get.assert_called_once()
        
        # Should store new history
        mock_working_memory.set.assert_called_once()
        call_args = mock_working_memory.set.call_args
        assert call_args[1]["key"] == "conversation:session1:history"
        
        history = call_args[1]["value"]
        assert len(history) == 1
        assert history[0]["query"] == "Show all vendors"
        assert history[0]["intent"]["query_type"] == "VENDOR_LIST"
    
    @pytest.mark.asyncio
    async def test_add_query_appends_to_existing_history(
        self,
        mock_working_memory,
        sample_intent
    ):
        """Test adding query appends to existing history."""
        # Mock existing history
        existing_history = [{
            "query": "First query",
            "intent": {"query_type": "VENDOR_LIST"},
            "timestamp": datetime.now().isoformat()
        }]
        
        mock_working_memory.get.return_value = MemoryEntry(
            key="conversation:session1:history",
            value=existing_history,
            memory_type=MemoryType.WORKING
        )
        
        context = ConversationContext(mock_working_memory, "session1")
        
        await context.add_query(
            query="Second query",
            intent=sample_intent,
            result=None
        )
        
        # Should store updated history
        call_args = mock_working_memory.set.call_args
        history = call_args[1]["value"]
        assert len(history) == 2
        assert history[0]["query"] == "First query"
        assert history[1]["query"] == "Second query"
    
    @pytest.mark.asyncio
    async def test_max_history_limit(self, mock_working_memory, sample_intent):
        """Test that history is limited to max_history entries."""
        # Create history with max_history items
        existing_history = [
            {
                "query": f"Query {i}",
                "intent": {"query_type": "VENDOR_LIST"},
                "timestamp": datetime.now().isoformat()
            }
            for i in range(5)
        ]
        
        mock_working_memory.get.return_value = MemoryEntry(
            key="conversation:session1:history",
            value=existing_history,
            memory_type=MemoryType.WORKING
        )
        
        context = ConversationContext(mock_working_memory, "session1", max_history=5)
        
        # Add one more query
        await context.add_query(
            query="Query 5",
            intent=sample_intent
        )
        
        # Should keep only last 5
        call_args = mock_working_memory.set.call_args
        history = call_args[1]["value"]
        assert len(history) == 5
        assert history[0]["query"] == "Query 1"  # First is removed
        assert history[-1]["query"] == "Query 5"  # Last is new
    
    @pytest.mark.asyncio
    async def test_get_last_entities_empty_history(self, mock_working_memory):
        """Test getting entities from empty history."""
        context = ConversationContext(mock_working_memory, "session1")
        
        entities = await context.get_last_entities()
        
        assert entities == []
    
    @pytest.mark.asyncio
    async def test_get_last_entities_single_query(self, mock_working_memory):
        """Test getting entities from single query."""
        history = [{
            "query": "Show vendors",
            "intent": {
                "query_type": "VENDOR_LIST",
                "entities": ["VENDOR", "CONTROL"]
            },
            "timestamp": datetime.now().isoformat()
        }]
        
        mock_working_memory.get.return_value = MemoryEntry(
            key="test",
            value=history,
            memory_type=MemoryType.WORKING
        )
        
        context = ConversationContext(mock_working_memory, "session1")
        entities = await context.get_last_entities()
        
        assert entities == [EntityType.VENDOR, EntityType.CONTROL]
    
    @pytest.mark.asyncio
    async def test_get_last_entities_multiple_queries(self, mock_working_memory):
        """Test getting entities from multiple queries."""
        history = [
            {
                "query": "Show vendors",
                "intent": {"entities": ["VENDOR"]},
                "timestamp": datetime.now().isoformat()
            },
            {
                "query": "Show controls",
                "intent": {"entities": ["CONTROL"]},
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        mock_working_memory.get.return_value = MemoryEntry(
            key="test",
            value=history,
            memory_type=MemoryType.WORKING
        )
        
        context = ConversationContext(mock_working_memory, "session1")
        entities = await context.get_last_entities(n=2)
        
        # Should return most recent first
        assert EntityType.CONTROL in entities
        assert EntityType.VENDOR in entities
    
    @pytest.mark.asyncio
    async def test_get_last_query_type(self, mock_working_memory):
        """Test getting last query type."""
        history = [{
            "query": "Show vendors",
            "intent": {"query_type": "VENDOR_RISK"},
            "timestamp": datetime.now().isoformat()
        }]
        
        mock_working_memory.get.return_value = MemoryEntry(
            key="test",
            value=history,
            memory_type=MemoryType.WORKING
        )
        
        context = ConversationContext(mock_working_memory, "session1")
        query_type = await context.get_last_query_type()
        
        assert query_type == QueryType.VENDOR_RISK
    
    @pytest.mark.asyncio
    async def test_get_last_query_type_empty(self, mock_working_memory):
        """Test getting query type from empty history."""
        context = ConversationContext(mock_working_memory, "session1")
        
        query_type = await context.get_last_query_type()
        
        assert query_type is None
    
    @pytest.mark.asyncio
    async def test_get_last_query(self, mock_working_memory):
        """Test getting last query string."""
        history = [{
            "query": "Show all vendors with critical risks",
            "intent": {"query_type": "VENDOR_RISK"},
            "timestamp": datetime.now().isoformat()
        }]
        
        mock_working_memory.get.return_value = MemoryEntry(
            key="test",
            value=history,
            memory_type=MemoryType.WORKING
        )
        
        context = ConversationContext(mock_working_memory, "session1")
        query = await context.get_last_query()
        
        assert query == "Show all vendors with critical risks"
    
    @pytest.mark.asyncio
    async def test_clear(self, mock_working_memory):
        """Test clearing conversation history."""
        context = ConversationContext(mock_working_memory, "session1")
        
        await context.clear()
        
        mock_working_memory.delete.assert_called_once_with(
            "conversation:session1:history"
        )
    
    @pytest.mark.asyncio
    async def test_serialize_intent(self, mock_working_memory, sample_intent):
        """Test intent serialization."""
        context = ConversationContext(mock_working_memory, "session1")
        
        serialized = context._serialize_intent(sample_intent)
        
        assert serialized["query_type"] == "VENDOR_LIST"
        assert serialized["entities"] == ["VENDOR"]
        assert serialized["confidence"] == 0.9
        assert serialized["has_filters"] is False
        assert serialized["has_aggregations"] is False
    
    def test_summarize_result(self, mock_working_memory, sample_result):
        """Test result summarization."""
        context = ConversationContext(mock_working_memory, "session1")
        
        summary = context._summarize_result(sample_result)
        
        assert summary["record_count"] == 2
        assert summary["has_data"] is True
