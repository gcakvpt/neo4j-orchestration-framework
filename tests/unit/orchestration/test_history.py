"""Unit tests for query history tracking."""

import pytest
from datetime import datetime, timedelta
from neo4j_orchestration.orchestration.history import QueryHistory, QueryRecord
from neo4j_orchestration.memory.episodic import SimpleEpisodicMemory, Event


class TestQueryRecord:
    """Tests for QueryRecord."""
    
    def test_create_query_record(self):
        """Test creating a query record."""
        record = QueryRecord(
            query_id="test-123",
            natural_language="Show critical vendors",
            intent={"entity_type": "Vendor", "filters": {"risk_level": "critical"}},
            cypher_query="MATCH (v:Vendor) WHERE v.risk_level = $risk_level RETURN v",
            parameters={"risk_level": "critical"},
            result_count=5,
            execution_time_ms=123.45,
        )
        
        assert record.query_id == "test-123"
        assert record.natural_language == "Show critical vendors"
        assert record.success is True
        assert record.error_message is None
    
    def test_failed_query_record(self):
        """Test creating a failed query record."""
        record = QueryRecord(
            query_id="test-456",
            natural_language="Invalid query",
            intent={},
            cypher_query="",
            success=False,
            error_message="Invalid syntax",
        )
        
        assert record.success is False
        assert record.error_message == "Invalid syntax"
        assert record.result_count == 0
    
    def test_record_to_event_conversion(self):
        """Test converting QueryRecord to Event."""
        record = QueryRecord(
            query_id="test-789",
            natural_language="Find vendors",
            intent={"entity_type": "Vendor"},
            cypher_query="MATCH (v:Vendor) RETURN v",
            result_count=10,
        )
        
        event = record.to_event()
        
        assert event.event_id == "test-789"
        assert event.event_type == "query_executed"
        assert event.content["natural_language"] == "Find vendors"
        assert event.content["result_count"] == 10
    
    def test_record_from_event_conversion(self):
        """Test converting Event to QueryRecord."""
        event = Event(
            event_id="test-abc",
            event_type="query_executed",
            content={
                "natural_language": "Show vendors",
                "intent": {"entity_type": "Vendor"},
                "cypher_query": "MATCH (v:Vendor) RETURN v",
                "parameters": {},
                "result_count": 8,
                "execution_time_ms": 100.0,
                "success": True,
                "error_message": None,
            },
        )
        
        record = QueryRecord.from_event(event)
        
        assert record.query_id == "test-abc"
        assert record.natural_language == "Show vendors"
        assert record.result_count == 8
        assert record.success is True


class TestQueryHistory:
    """Tests for QueryHistory."""
    
    @pytest.fixture
    def history(self):
        """Create a QueryHistory instance."""
        memory = SimpleEpisodicMemory()
        return QueryHistory(memory, max_size=10)
    
    def test_add_and_retrieve_query(self, history):
        """Test adding and retrieving a query."""
        record = QueryRecord(
            query_id="q1",
            natural_language="Show vendors",
            intent={"entity_type": "Vendor"},
            cypher_query="MATCH (v:Vendor) RETURN v",
            result_count=5,
        )
        
        history.add_query(record)
        
        last = history.get_last_query()
        assert last is not None
        assert last.query_id == "q1"
        assert last.natural_language == "Show vendors"
    
    def test_get_history_multiple_queries(self, history):
        """Test retrieving multiple queries."""
        # Add three queries
        for i in range(3):
            record = QueryRecord(
                query_id=f"q{i}",
                natural_language=f"Query {i}",
                intent={},
                cypher_query="MATCH (n) RETURN n",
            )
            history.add_query(record)
        
        # Get history
        records = history.get_history(limit=5)
        
        assert len(records) == 3
        # Should be in reverse chronological order
        assert records[0].query_id == "q2"
        assert records[1].query_id == "q1"
        assert records[2].query_id == "q0"
    
    def test_get_successful_queries(self, history):
        """Test filtering successful queries."""
        # Add successful query
        history.add_query(QueryRecord(
            query_id="success1",
            natural_language="Good query",
            intent={},
            cypher_query="MATCH (n) RETURN n",
            success=True,
        ))
        
        # Add failed query
        history.add_query(QueryRecord(
            query_id="fail1",
            natural_language="Bad query",
            intent={},
            cypher_query="",
            success=False,
            error_message="Error",
        ))
        
        # Add another successful query
        history.add_query(QueryRecord(
            query_id="success2",
            natural_language="Another good query",
            intent={},
            cypher_query="MATCH (n) RETURN n",
            success=True,
        ))
        
        successful = history.get_successful_queries(limit=5)
        
        assert len(successful) == 2
        assert all(r.success for r in successful)
        assert successful[0].query_id == "success2"
        assert successful[1].query_id == "success1"
    
    def test_search_by_entity_type(self, history):
        """Test searching by entity type."""
        # Add Vendor queries
        history.add_query(QueryRecord(
            query_id="v1",
            natural_language="Find vendors",
            intent={"entity_type": "Vendor"},
            cypher_query="MATCH (v:Vendor) RETURN v",
        ))
        
        # Add Control query
        history.add_query(QueryRecord(
            query_id="c1",
            natural_language="Find controls",
            intent={"entity_type": "Control"},
            cypher_query="MATCH (c:Control) RETURN c",
        ))
        
        # Add another Vendor query
        history.add_query(QueryRecord(
            query_id="v2",
            natural_language="Show critical vendors",
            intent={"entity_type": "Vendor"},
            cypher_query="MATCH (v:Vendor) RETURN v",
        ))
        
        vendor_queries = history.search_by_entity_type("Vendor", limit=5)
        
        assert len(vendor_queries) == 2
        assert all(r.intent.get("entity_type") == "Vendor" for r in vendor_queries)
    
    def test_empty_history(self, history):
        """Test behavior with empty history."""
        assert history.get_last_query() is None
        assert len(history.get_history()) == 0
        assert len(history.get_successful_queries()) == 0
    
    def test_history_pruning(self):
        """Test that history is pruned at max_size."""
        memory = SimpleEpisodicMemory()
        history = QueryHistory(memory, max_size=3)
        
        # Add 5 queries
        for i in range(5):
            record = QueryRecord(
                query_id=f"q{i}",
                natural_language=f"Query {i}",
                intent={},
                cypher_query="MATCH (n) RETURN n",
            )
            history.add_query(record)
        
        # Should only keep last 3
        all_history = history.get_history(limit=10)
        assert len(all_history) == 3
        
        # Should have most recent queries (q4, q3, q2)
        query_ids = [r.query_id for r in all_history]
        assert "q4" in query_ids
        assert "q3" in query_ids
        assert "q2" in query_ids
        assert "q0" not in query_ids
        assert "q1" not in query_ids
