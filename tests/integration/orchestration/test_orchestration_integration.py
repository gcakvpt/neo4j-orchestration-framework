"""Integration tests for query orchestration."""

import pytest
from unittest.mock import Mock, patch
from neo4j_orchestration.orchestration import QueryOrchestrator, OrchestratorConfig
from neo4j_orchestration.execution import QueryExecutor, QueryResult, ExecutionMetadata
from neo4j_orchestration.planning.intent import QueryIntent, QueryType, EntityType
from neo4j_orchestration.memory.episodic import SimpleEpisodicMemory


class TestOrchestratorIntegration:
    """Integration tests for full orchestration pipeline."""
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor with realistic responses."""
        executor = Mock(spec=QueryExecutor)
        
        result = QueryResult(
            records=[
                {"name": "Vendor A", "risk_level": "high"},
                {"name": "Vendor B", "risk_level": "medium"},
            ],
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) RETURN v",
                parameters={},
                result_available_after=15,
                result_consumed_after=25,
            ),
            summary="Query completed successfully",
        )
        executor.execute.return_value = result
        
        return executor
    
    @pytest.fixture
    def mock_intent(self):
        """Create a realistic query intent."""
        return QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            filters=[],
        )
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_end_to_end_query_flow(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test complete query flow from NL to results."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        # Create orchestrator
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Execute query
        result = orchestrator.query("Show high-risk vendors")
        
        # Verify results
        assert result is not None
        assert len(result.records) == 2
        assert result.records[0]["risk_level"] == "high"
        
        # Verify history
        history = orchestrator.get_history()
        assert len(history) == 1
        assert history[0].natural_language == "Show high-risk vendors"
        assert history[0].success is True
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_query_history_persistence(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that query history is maintained across multiple queries."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Execute multiple queries
        orchestrator.query("Query 1")
        orchestrator.query("Query 2")
        orchestrator.query("Query 3")
        
        # Verify all are in history
        history = orchestrator.get_history(limit=10)
        assert len(history) == 3
        
        # Verify order (most recent first)
        assert history[0].natural_language == "Query 3"
        assert history[1].natural_language == "Query 2"
        assert history[2].natural_language == "Query 1"
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_query_metadata_completeness(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that query metadata is properly captured."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = (
            "MATCH (v:Vendor {risk_level: $risk}) RETURN v",
            {"risk": "high"}
        )
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        orchestrator.query("Show critical vendors")
        
        last = orchestrator.get_last_query()
        
        # Verify metadata
        assert last.query_id is not None
        assert last.cypher_query == "MATCH (v:Vendor {risk_level: $risk}) RETURN v"
        assert last.parameters == {"risk": "high"}
        assert last.result_count == 2
        assert last.execution_time_ms > 0
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_failed_query_handling(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that failed queries are properly recorded."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.side_effect = Exception("Cypher generation failed")
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Execute and catch error
        with pytest.raises(Exception, match="Cypher generation failed"):
            orchestrator.query("Invalid query")
        
        # Verify failure is recorded
        last = orchestrator.get_last_query()
        assert last is not None
        assert last.success is False
        assert "Cypher generation failed" in last.error_message
        assert last.result_count == 0
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_episodic_memory_integration(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test integration with episodic memory."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        # Use explicit episodic memory
        memory = SimpleEpisodicMemory()
        orchestrator = QueryOrchestrator(mock_executor, episodic_memory=memory)
        
        # Execute query
        orchestrator.query("Test query")
        
        # Verify memory contains query event
        events = memory.retrieve_recent(event_type="query_executed", limit=10)
        assert len(events) == 1
        assert events[0].content["natural_language"] == "Test query"
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_multiple_queries_different_entities(self, mock_gen_class, mock_clf_class, mock_executor):
        """Test handling different entity types in history."""
        # Setup mocks
        mock_classifier = Mock()
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (n) RETURN n", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Query different entities
        vendor_intent = QueryIntent(query_type=QueryType.VENDOR_LIST, entities=[EntityType.VENDOR])
        control_intent = QueryIntent(query_type=QueryType.CONTROL_EFFECTIVENESS, entities=[EntityType.CONTROL])
        
        mock_classifier.classify.return_value = vendor_intent
        orchestrator.query("Show vendors")
        
        mock_classifier.classify.return_value = control_intent
        orchestrator.query("Show controls")
        
        # Verify both in history
        history = orchestrator.get_history(limit=10)
        assert len(history) == 2
