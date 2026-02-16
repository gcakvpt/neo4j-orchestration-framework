"""Unit tests for result types."""

import pytest
from unittest.mock import MagicMock
from neo4j_orchestration.execution import QueryResult, ExecutionMetadata


class TestExecutionMetadata:
    """Test ExecutionMetadata class."""
    
    def test_basic_metadata(self):
        """Test creating basic metadata."""
        metadata = ExecutionMetadata(
            query="MATCH (n) RETURN n",
            parameters={"param": "value"},
        )
        
        assert metadata.query == "MATCH (n) RETURN n"
        assert metadata.parameters == {"param": "value"}
    
    def test_from_summary(self):
        """Test creating metadata from Neo4j summary."""
        mock_summary = MagicMock()
        mock_summary.result_available_after = 15
        mock_summary.result_consumed_after = 30
        
        mock_counters = MagicMock()
        mock_counters.nodes_created = 5
        mock_counters.relationships_created = 3
        mock_counters.properties_set = 10
        mock_counters.nodes_deleted = 0
        mock_counters.relationships_deleted = 0
        mock_counters.labels_added = 2
        mock_counters.labels_removed = 0
        mock_summary.counters = mock_counters
        
        metadata = ExecutionMetadata.from_summary(
            "CREATE (n:Test)",
            {"name": "test"},
            mock_summary
        )
        
        assert metadata.query == "CREATE (n:Test)"
        assert metadata.counters is not None
        assert metadata.counters["nodes_created"] == 5


class TestQueryResult:
    """Test QueryResult class."""
    
    def test_basic_result(self):
        """Test creating basic query result."""
        metadata = ExecutionMetadata(query="MATCH (n) RETURN n", parameters={})
        records = [{"name": "Vendor1"}, {"name": "Vendor2"}]
        
        result = QueryResult(
            records=records,
            metadata=metadata,
            summary="Found 2 results",
        )
        
        assert len(result) == 2
        assert result.summary == "Found 2 results"
    
    def test_iteration(self):
        """Test iterating over results."""
        metadata = ExecutionMetadata(query="", parameters={})
        records = [{"id": 1}, {"id": 2}]
        
        result = QueryResult(records=records, metadata=metadata, summary="")
        
        ids = [r["id"] for r in result]
        assert ids == [1, 2]
