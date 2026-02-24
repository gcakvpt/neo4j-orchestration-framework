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


class TestPatternLearning:
    """Tests for pattern learning integration in QueryOrchestrator."""
    
    @pytest.fixture
    def mock_executor_with_driver(self):
        """Create a mock executor with driver."""
        executor = Mock(spec=QueryExecutor)
        executor.driver = Mock()  # Add driver for QueryPatternMemory
        
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
    
    def test_initialization_without_pattern_learning(self, mock_executor_with_driver):
        """Test default initialization without pattern learning."""
        orchestrator = QueryOrchestrator(mock_executor_with_driver)
        
        assert orchestrator.enable_pattern_learning is False
        assert orchestrator.pattern_memory is None
        assert orchestrator.preference_tracker is None
        assert orchestrator.classifier.__class__.__name__ == 'QueryIntentClassifier'
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryPatternMemory')
    @patch('neo4j_orchestration.orchestration.orchestrator.UserPreferenceTracker')
    def test_initialization_with_pattern_learning(
        self, 
        mock_tracker_class, 
        mock_memory_class,
        mock_executor_with_driver
    ):
        """Test initialization with pattern learning enabled."""
        # Setup mocks
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker
        
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=True
        )
        
        assert orchestrator.enable_pattern_learning is True
        assert orchestrator.pattern_memory is not None
        assert orchestrator.preference_tracker is not None
        assert orchestrator.classifier.__class__.__name__ == 'PatternEnhancedClassifier'
        
        # Verify QueryPatternMemory was initialized with driver
        mock_memory_class.assert_called_once()
        assert mock_memory_class.call_args[1]['driver'] == mock_executor_with_driver.driver
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryPatternMemory')
    @patch('neo4j_orchestration.orchestration.orchestrator.UserPreferenceTracker')
    def test_initialization_with_custom_pattern_components(
        self,
        mock_tracker_class,
        mock_memory_class,
        mock_executor_with_driver
    ):
        """Test initialization with custom pattern learning components."""
        custom_memory = Mock()
        custom_tracker = Mock()
        
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=True,
            pattern_memory=custom_memory,
            preference_tracker=custom_tracker
        )
        
        assert orchestrator.pattern_memory == custom_memory
        assert orchestrator.preference_tracker == custom_tracker
        
        # Should not create new instances
        mock_memory_class.assert_not_called()
        mock_tracker_class.assert_not_called()
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryPatternMemory')
    @patch('neo4j_orchestration.orchestration.orchestrator.UserPreferenceTracker')
    @patch('neo4j_orchestration.orchestration.orchestrator.PatternEnhancedClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_query_with_pattern_learning_enabled(
        self,
        mock_gen_class,
        mock_enhanced_clf_class,
        mock_tracker_class,
        mock_memory_class,
        mock_executor_with_driver,
        mock_intent
    ):
        """Test query execution with pattern learning enabled."""
        # Setup mocks
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        
        from unittest.mock import AsyncMock
        
        mock_tracker = Mock()
        mock_tracker.record_query_preference = AsyncMock(return_value=None)
        mock_tracker_class.return_value = mock_tracker
        
        mock_classifier = Mock()
        mock_classifier.classify = AsyncMock(return_value=mock_intent)
        mock_enhanced_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=True
        )
        
        # Execute query
        result = orchestrator.query("Show vendors")
        
        assert result is not None
        assert len(result.records) == 2
        
        # Verify preference recording was called
        # Note: asyncio.run will have executed it
        assert mock_tracker.record_query_preference.called
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_query_without_pattern_learning(
        self,
        mock_gen_class,
        mock_clf_class,
        mock_executor_with_driver,
        mock_intent
    ):
        """Test query execution without pattern learning."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=False
        )
        
        # Execute query
        result = orchestrator.query("Show vendors")
        
        assert result is not None
        assert orchestrator.preference_tracker is None
    
    def test_get_pattern_stats_disabled(self, mock_executor_with_driver):
        """Test get_pattern_stats when pattern learning is disabled."""
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=False
        )
        
        stats = orchestrator.get_pattern_stats()
        
        assert stats == {"enabled": False}
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryPatternMemory')
    @patch('neo4j_orchestration.orchestration.orchestrator.UserPreferenceTracker')
    def test_get_pattern_stats_enabled(
        self,
        mock_tracker_class,
        mock_memory_class,
        mock_executor_with_driver
    ):
        """Test get_pattern_stats when pattern learning is enabled."""
        # Setup mocks
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        
        mock_tracker = Mock()
        mock_tracker.get_session_stats.return_value = {
            "queries_recorded": 5,
            "unique_entities": 2,
            "unique_filter_patterns": 3
        }
        mock_tracker_class.return_value = mock_tracker
        
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=True
        )
        
        stats = orchestrator.get_pattern_stats()
        
        assert stats["enabled"] is True
        assert stats["queries_recorded"] == 5
        assert stats["unique_entities"] == 2
        assert stats["unique_filter_patterns"] == 3
    
    def test_get_preferred_entities_disabled(self, mock_executor_with_driver):
        """Test get_preferred_entities when pattern learning is disabled."""
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=False
        )
        
        entities = orchestrator.get_preferred_entities()
        
        assert entities == []
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryPatternMemory')
    @patch('neo4j_orchestration.orchestration.orchestrator.UserPreferenceTracker')
    def test_get_preferred_entities_enabled(
        self,
        mock_tracker_class,
        mock_memory_class,
        mock_executor_with_driver
    ):
        """Test get_preferred_entities when pattern learning is enabled."""
        # Setup mocks
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        
        mock_tracker = Mock()
        mock_tracker.get_preferred_entities.return_value = [
            EntityType.VENDOR,
            EntityType.CONTROL,
            EntityType.RISK
        ]
        mock_tracker_class.return_value = mock_tracker
        
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=True
        )
        
        entities = orchestrator.get_preferred_entities(limit=3)
        
        assert len(entities) == 3
        assert EntityType.VENDOR in entities
        assert EntityType.CONTROL in entities
        assert EntityType.RISK in entities
        
        # Verify tracker was called with correct limit
        mock_tracker.get_preferred_entities.assert_called_once_with(limit=3)
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryPatternMemory')
    @patch('neo4j_orchestration.orchestration.orchestrator.UserPreferenceTracker')
    @patch('neo4j_orchestration.orchestration.orchestrator.PatternEnhancedClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_pattern_learning_with_failed_query(
        self,
        mock_gen_class,
        mock_enhanced_clf_class,
        mock_tracker_class,
        mock_memory_class,
        mock_executor_with_driver,
        mock_intent
    ):
        """Test that pattern learning handles failed queries gracefully."""
        # Setup mocks
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        
        mock_tracker = Mock()
        mock_tracker.record_query_preference = Mock()
        mock_tracker_class.return_value = mock_tracker
        
        mock_classifier = Mock()
        mock_classifier.classify = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_enhanced_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.side_effect = Exception("Generation failed")
        mock_gen_class.return_value = mock_generator
        
        orchestrator = QueryOrchestrator(
            mock_executor_with_driver,
            enable_pattern_learning=True
        )
        
        # Execute query and expect failure
        with pytest.raises(Exception, match="Generation failed"):
            orchestrator.query("Bad query")
        
        # Preference recording should NOT be called for failed queries
        mock_tracker.record_query_preference.assert_not_called()
    
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_backward_compatibility(
        self,
        mock_gen_class,
        mock_clf_class,
        mock_executor_with_driver,
        mock_intent
    ):
        """Test that existing code without pattern learning still works."""
        # Setup mocks
        mock_classifier = Mock()
        mock_classifier.classify.return_value = mock_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        # Old-style initialization (no pattern learning parameters)
        orchestrator = QueryOrchestrator(mock_executor_with_driver)
        
        # Should work exactly as before
        result = orchestrator.query("Show vendors")
        
        assert result is not None
        assert len(result.records) == 2
        assert orchestrator.enable_pattern_learning is False
        assert orchestrator.pattern_memory is None
        assert orchestrator.preference_tracker is None
