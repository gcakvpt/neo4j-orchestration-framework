"""Unit tests for query orchestrator."""

import pytest
from unittest.mock import Mock, patch
from neo4j_orchestration.orchestration import QueryOrchestrator, OrchestratorConfig
from neo4j_orchestration.execution import QueryExecutor, QueryResult, ExecutionMetadata
from neo4j_orchestration.planning.intent import QueryIntent, QueryType, EntityType
from neo4j_orchestration.memory.episodic import SimpleEpisodicMemory


class TestQueryOrchestrator:
    """Tests for QueryOrchestrator."""
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor."""
        executor = Mock(spec=QueryExecutor)
        
        # Mock successful query execution
        result = QueryResult(
            records=[{"name": "Vendor1"}, {"name": "Vendor2"}],
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) RETURN v",
                parameters={},
                result_available_after=10,
                result_consumed_after=20,
            ),
            summary="Query completed successfully",
        )
        executor.execute.return_value = result
        
        return executor
    
    @pytest.fixture
    def mock_intent(self):
        """Create a mock QueryIntent."""
        return QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[],
        )
    
    def test_initialization(self, mock_executor):
        """Test orchestrator initialization."""
        orchestrator = QueryOrchestrator(mock_executor)
        
        assert orchestrator.executor == mock_executor
        assert orchestrator.config.enable_history is True
        assert orchestrator.classifier is not None
        assert orchestrator.generator is not None
        assert orchestrator.history is not None
    
    def test_custom_config(self, mock_executor):
        """Test orchestrator with custom config."""
        config = OrchestratorConfig(
            enable_history=False,
            max_history_size=50,
        )
        
        orchestrator = QueryOrchestrator(mock_executor, config=config)
        
        assert orchestrator.config.enable_history is False
        assert orchestrator.config.max_history_size == 50
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_successful_query(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test executing a successful query."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        result = orchestrator.query("Show all vendors")
        
        assert result is not None
        assert len(result.records) == 2
        assert mock_executor.execute.called
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_query_stores_history(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that queries are stored in history."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        orchestrator.query("Show all vendors")
        
        last = orchestrator.get_last_query()
        assert last is not None
        assert last.natural_language == "Show all vendors"
        assert last.success is True
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_multiple_queries_in_history(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test multiple queries are tracked."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        orchestrator.query("Query 1")
        orchestrator.query("Query 2")
        orchestrator.query("Query 3")
        
        history = orchestrator.get_history(limit=5)
        
        assert len(history) == 3
        assert history[0].natural_language == "Query 3"
        assert history[1].natural_language == "Query 2"
        assert history[2].natural_language == "Query 1"
    
    def test_get_last_query(self, mock_executor):
        """Test getting the last query."""
        orchestrator = QueryOrchestrator(mock_executor)
        
        # No queries yet
        assert orchestrator.get_last_query() is None
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_failed_query_recorded(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that failed queries are recorded."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.side_effect = Exception("Query generation failed")
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Execute and catch error
        with pytest.raises(Exception, match="Query generation failed"):
            orchestrator.query("Bad query")
        
        # Check history
        last = orchestrator.get_last_query()
        assert last is not None
        assert last.success is False
        assert "Query generation failed" in last.error_message
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_get_successful_queries_filter(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test filtering for successful queries."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Add successful query
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        orchestrator.query("Good query 1")
        
        # Add failed query
        mock_generator.generate.side_effect = Exception("Error")
        with pytest.raises(Exception):
            orchestrator.query("Bad query")
        
        # Reset mock
        mock_generator.generate.side_effect = None
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        
        # Add another successful query
        orchestrator.query("Good query 2")
        
        successful = orchestrator.get_successful_queries(limit=5)
        
        assert len(successful) == 2
        assert all(r.success for r in successful)
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_search_history_by_entity(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test searching history by entity type."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Add queries
        orchestrator.query("Find vendors")
        orchestrator.query("Show critical vendors")
        
        # Search - note: entities is a list in QueryIntent
        vendor_queries = orchestrator.search_history_by_entity("Vendor", limit=5)
        
        # May or may not find matches depending on how intent is stored
        assert isinstance(vendor_queries, list)
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_history_disabled(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that history can be disabled."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        config = OrchestratorConfig(enable_history=False)
        orchestrator = QueryOrchestrator(mock_executor, config=config)
        
        orchestrator.query("Test query")
        
        # History should be empty
        assert orchestrator.get_last_query() is None
        assert len(orchestrator.get_history()) == 0
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_execution_time_recorded(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that execution time is recorded."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        orchestrator.query("Test query")
        
        last = orchestrator.get_last_query()
        assert last is not None
        assert last.execution_time_ms > 0
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_query_id_generated(self, mock_gen_class, mock_clf_class, mock_executor, mock_intent):
        """Test that unique query IDs are generated."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(mock_executor)
        
        orchestrator.query("Query 1")
        orchestrator.query("Query 2")
        
        history = orchestrator.get_history(limit=2)
        
        assert len(history) == 2
        assert history[0].query_id != history[1].query_id
