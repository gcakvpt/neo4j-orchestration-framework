"""Integration tests for pattern learning system.

Tests the complete pattern learning workflow including:
- QueryPatternMemory (Neo4j storage)
- UserPreferenceTracker (session tracking)
- PatternEnhancedClassifier (query enhancement)
- QueryOrchestrator (end-to-end integration)

⚠️ ARCHITECTURAL LIMITATION - SCHEDULED FOR WEEK 5 REFACTORING ⚠️
=================================================================
ISSUE: QueryType is currently domain-specific (VENDOR_RISK, CONTROL_EFFECTIVENESS, etc.)
       This limits pattern learning to predefined use cases only.

IMPACT: Pattern learning cannot work with arbitrary entities in the knowledge graph.
        New entities require code changes in multiple places.

SOLUTION: Refactor QueryType to generic operations (LIST, FILTER, DETAILS, etc.)
          See: QUERYTYPE_REFACTOR_ANALYSIS.md for full plan

TEMPORARY WORKAROUND: Tests use QueryType.VENDOR_LIST as placeholder.
                     This validates pattern learning mechanics but not scalability.

REFACTORING SCHEDULED: Week 5, Session 1 (~4 hours)
=================================================================
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from neo4j import GraphDatabase

from neo4j_orchestration.orchestration import QueryOrchestrator, OrchestratorConfig
from neo4j_orchestration.orchestration.preferences import UserPreferenceTracker
from neo4j_orchestration.memory.query_patterns import QueryPatternMemory
from neo4j_orchestration.execution import QueryExecutor, QueryResult, ExecutionMetadata
from neo4j_orchestration.planning.intent import (
    QueryIntent, QueryType, EntityType, FilterCondition, FilterOperator
)


class TestPatternLearningIntegration:
    """Integration tests for pattern learning system."""
    
    @pytest.fixture
    def neo4j_driver(self):
        """Create Neo4j driver for testing.
        
        Note: This requires a running Neo4j instance.
        Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD environment variables.
        """
        import os
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        yield driver
        
        # Cleanup: Delete test pattern data
        with driver.session() as session:
            session.run("MATCH (p:QueryPattern) DELETE p")
        
        driver.close()
    
    @pytest.fixture
    def pattern_memory(self, neo4j_driver):
        """Create QueryPatternMemory instance."""
        return QueryPatternMemory(driver=neo4j_driver)
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor with realistic responses."""
        executor = Mock(spec=QueryExecutor)
        
        # Mock the driver attribute for pattern memory
        executor.driver = Mock()
        
        # Create realistic query results
        result = QueryResult(
            records=[
                {"name": "Critical Vendor A", "criticality": "Critical"},
                {"name": "Critical Vendor B", "criticality": "Critical"},
            ],
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) WHERE v.criticality = 'Critical' RETURN v",
                parameters={},
                result_available_after=15,
                result_consumed_after=25,
            ),
            summary="Query completed successfully",
        )
        executor.execute.return_value = result
        
        return executor
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pattern_learning_convergence(self, pattern_memory):
        """Test that patterns converge after multiple similar queries."""
        # Create preference tracker
        tracker = UserPreferenceTracker(
            pattern_memory=pattern_memory,
            session_id="test-session-1"
        )
        
        # Create intent with critical filter
        critical_intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition(
                    field="criticality",
                    operator=FilterOperator.EQUALS,
                    value="Critical"
                )
            ],
        )
        
        # Simulate successful query result
        result = QueryResult(
            records=[{"name": "Vendor A"}],
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) WHERE v.criticality = 'Critical' RETURN v",
                parameters={},
                result_available_after=10,
                result_consumed_after=20,
            ),
            summary="Success",
        )
        
        # Record the preference 3 times (establish pattern)
        for _ in range(3):
            await tracker.record_query_preference(critical_intent, result, True)
        
        # Verify pattern was learned
        filters = await tracker.get_preferred_filters(QueryType.VENDOR_LIST, min_frequency=2)
        assert "criticality" in filters
        assert filters["criticality"] == "Critical"
        
        # Verify entity preference
        entities = tracker.get_preferred_entities(limit=5)
        assert EntityType.VENDOR in entities
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_entity_pattern_isolation(self, pattern_memory):
        """Test that patterns for different entities don't interfere."""
        tracker = UserPreferenceTracker(
            pattern_memory=pattern_memory,
            session_id="test-session-2"
        )
        
        # Record vendor patterns
        vendor_intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition(
                    field="criticality",
                    operator=FilterOperator.EQUALS,
                    value="Critical"
                )
            ],
        )
        
        vendor_result = QueryResult(
            records=[{"name": "Vendor A"}],
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) RETURN v",
                parameters={},
                result_available_after=10,
                result_consumed_after=20,
            ),
            summary="Success",
        )
        
        for _ in range(3):
            await tracker.record_query_preference(vendor_intent, vendor_result, True)
        
        # Record control patterns with different filter
        control_intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.CONTROL],
            filters=[
                FilterCondition(
                    field="status",
                    operator=FilterOperator.EQUALS,
                    value="Active"
                )
            ],
        )
        
        control_result = QueryResult(
            records=[{"name": "Control A"}],
            metadata=ExecutionMetadata(
                query="MATCH (c:Control) RETURN c",
                parameters={},
                result_available_after=10,
                result_consumed_after=20,
            ),
            summary="Success",
        )
        
        for _ in range(3):
            await tracker.record_query_preference(control_intent, control_result, True)
        
        # Create new intent for vendor (without filters)
        new_vendor_intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[],
        )
        
        # Get suggestions - should only suggest vendor-specific filters
        suggestions = await tracker.suggest_enhancements(new_vendor_intent)
        
        # Should suggest criticality for vendors, not status
        suggested_fields = {f.field for f in suggestions}
        assert "criticality" in suggested_fields
        assert "status" not in suggested_fields  # Control filter shouldn't leak
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cross_session_pattern_persistence(self, neo4j_driver):
        """Test that patterns persist across different sessions."""
        # Session 1: Record patterns
        memory1 = QueryPatternMemory(driver=neo4j_driver)
        tracker1 = UserPreferenceTracker(
            pattern_memory=memory1,
            session_id="session-1"
        )
        
        # Record a pattern
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition(
                    field="criticality",
                    operator=FilterOperator.EQUALS,
                    value="Critical"
                )
            ],
        )
        
        result = QueryResult(
            records=[{"name": "Vendor A"}],
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) RETURN v",
                parameters={},
                result_available_after=10,
                result_consumed_after=20,
            ),
            summary="Success",
        )
        
        # Record pattern multiple times to exceed min_occurrences
        for _ in range(3):
            await tracker1.record_query_preference(intent, result, True)
        
        # Wait a bit for Neo4j to process
        await asyncio.sleep(0.1)
        
        # Session 2: Create new tracker and verify pattern is retrieved
        memory2 = QueryPatternMemory(driver=neo4j_driver)
        tracker2 = UserPreferenceTracker(
            pattern_memory=memory2,
            session_id="session-2"  # Different session
        )
        
        # Get patterns from Neo4j (not from in-memory cache)
        filters = await memory2.get_common_filters(
            query_type=QueryType.VENDOR_LIST,
            entity_type=EntityType.VENDOR,
            min_occurrences=2
        )
        
        # Should retrieve the pattern from Neo4j
        assert "criticality" in filters
        assert filters["criticality"] == "Critical"
    
    @pytest.mark.integration
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_orchestrator_pattern_learning_enabled(
        self, mock_gen_class, mock_clf_class, mock_executor, neo4j_driver
    ):
        """Test QueryOrchestrator with pattern learning enabled."""
        # Setup mocks
        mock_classifier = Mock()
        critical_intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition(
                    field="criticality",
                    operator=FilterOperator.EQUALS,
                    value="Critical"
                )
            ],
        )
        mock_classifier.classify.return_value = critical_intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = (
            "MATCH (v:Vendor) WHERE v.criticality = 'Critical' RETURN v",
            {}
        )
        mock_gen_class.return_value = mock_generator
        
        # Update mock executor to use real driver
        mock_executor.driver = neo4j_driver
        
        # Create orchestrator with pattern learning
        orchestrator = QueryOrchestrator(
            mock_executor,
            enable_pattern_learning=True
        )
        
        # Execute query
        result = orchestrator.query("Show critical vendors")
        
        # Verify result
        assert result is not None
        assert len(result.records) == 2
        
        # Verify pattern learning components were initialized
        assert orchestrator.enable_pattern_learning is True
        assert orchestrator.pattern_memory is not None
        assert orchestrator.preference_tracker is not None
        
        # Verify pattern stats
        stats = orchestrator.get_pattern_stats()
        assert stats["enabled"] is True
        assert stats["queries_recorded"] >= 1
    
    @pytest.mark.integration
    def test_orchestrator_backward_compatibility(self, mock_executor):
        """Test that orchestrator works without pattern learning (default)."""
        # Create orchestrator without pattern learning (default)
        orchestrator = QueryOrchestrator(mock_executor)
        
        # Verify pattern learning is disabled
        assert orchestrator.enable_pattern_learning is False
        assert orchestrator.pattern_memory is None
        assert orchestrator.preference_tracker is None
        
        # Verify stats show disabled
        stats = orchestrator.get_pattern_stats()
        assert stats == {"enabled": False}
        
        # Verify preferred entities is empty
        entities = orchestrator.get_preferred_entities()
        assert entities == []
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pattern_enhancement_suggestion_quality(self, pattern_memory):
        """Test that suggestions are high-quality and relevant."""
        tracker = UserPreferenceTracker(
            pattern_memory=pattern_memory,
            session_id="test-session-quality"
        )
        
        # Record diverse patterns
        patterns = [
            ("criticality", "Critical", 5),  # Strong pattern
            ("status", "Active", 3),         # Medium pattern
            ("region", "US", 2),             # Weak pattern
        ]
        
        for field, value, count in patterns:
            intent = QueryIntent(
                query_type=QueryType.VENDOR_LIST,
                entities=[EntityType.VENDOR],
                filters=[
                    FilterCondition(
                        field=field,
                        operator=FilterOperator.EQUALS,
                        value=value
                    )
                ],
            )
            
            result = QueryResult(
                records=[{"name": "Vendor A"}],
                metadata=ExecutionMetadata(
                    query="MATCH (v:Vendor) RETURN v",
                    parameters={},
                    result_available_after=10,
                    result_consumed_after=20,
                ),
                summary="Success",
            )
            
            for _ in range(count):
                await tracker.record_query_preference(intent, result, True)
        
        # Get suggestions for a new query
        new_intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[],
        )
        
        suggestions = await tracker.suggest_enhancements(new_intent)
        
        # Should get suggestions in order of frequency
        suggested_fields = [f.field for f in suggestions]
        
        # Criticality should be first (most frequent)
        assert suggested_fields[0] == "criticality"
        
        # Should not suggest weak patterns (below min_frequency=2)
        # Note: region has count=2, exactly at threshold, so it should appear
        assert "region" in suggested_fields or len(suggested_fields) <= 2
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_result_handling(self, pattern_memory):
        """Test that empty results are handled gracefully."""
        tracker = UserPreferenceTracker(
            pattern_memory=pattern_memory,
            session_id="test-session-empty"
        )
        
        # Create intent
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition(
                    field="criticality",
                    operator=FilterOperator.EQUALS,
                    value="Critical"
                )
            ],
        )
        
        # Create empty result
        empty_result = QueryResult(
            records=[],  # Empty!
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) WHERE v.criticality = 'Critical' RETURN v",
                parameters={},
                result_available_after=5,
                result_consumed_after=10,
            ),
            summary="No results found",
        )
        
        # Record preference (should handle empty result)
        await tracker.record_query_preference(intent, empty_result, True)
        
        # Verify it was recorded (even with 0 results)
        stats = tracker.get_stats()
        assert stats["queries_recorded"] == 1
        
        # Pattern should still be tracked
        filters = await tracker.get_preferred_filters(QueryType.VENDOR_LIST, min_frequency=1)
        assert "criticality" in filters


class TestPatternLearningPerformance:
    """Performance tests for pattern learning system."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    @patch('neo4j_orchestration.orchestration.orchestrator.QueryIntentClassifier')
    @patch('neo4j_orchestration.orchestration.orchestrator.CypherQueryGenerator')
    def test_pattern_learning_overhead(
        self, mock_gen_class, mock_clf_class
    ):
        """Measure overhead of pattern learning on query execution."""
        import time
        
        # Create mock executor
        executor = Mock(spec=QueryExecutor)
        executor.driver = Mock()  # Mock driver for pattern learning
        
        result = QueryResult(
            records=[{"name": "Vendor A"}],
            metadata=ExecutionMetadata(
                query="MATCH (v:Vendor) RETURN v",
                parameters={},
                result_available_after=10,
                result_consumed_after=20,
            ),
            summary="Success",
        )
        executor.execute.return_value = result
        
        # Setup mocks
        mock_classifier = Mock()
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[],
        )
        mock_classifier.classify.return_value = intent
        mock_clf_class.return_value = mock_classifier
        
        mock_generator = Mock()
        mock_generator.generate.return_value = ("MATCH (v:Vendor) RETURN v", {})
        mock_gen_class.return_value = mock_generator
        
        # Test WITHOUT pattern learning
        orchestrator_no_pl = QueryOrchestrator(executor, enable_pattern_learning=False)
        
        start = time.time()
        for _ in range(10):
            orchestrator_no_pl.query("Show vendors")
        baseline_time = time.time() - start
        
        # Test WITH pattern learning
        orchestrator_with_pl = QueryOrchestrator(executor, enable_pattern_learning=True)
        
        start = time.time()
        for _ in range(10):
            orchestrator_with_pl.query("Show vendors")
        pl_time = time.time() - start
        
        # Calculate overhead
        overhead = pl_time - baseline_time
        overhead_per_query = (overhead / 10) * 1000  # Convert to ms
        
        print(f"\nPerformance Results:")
        print(f"Baseline (no PL): {baseline_time:.4f}s for 10 queries")
        print(f"With PL: {pl_time:.4f}s for 10 queries")
        print(f"Overhead: {overhead:.4f}s total ({overhead_per_query:.2f}ms per query)")
        
        # Verify overhead is acceptable (< 50ms per query)
        # Note: This is lenient for CI/CD environments
        assert overhead_per_query < 50, f"Pattern learning overhead too high: {overhead_per_query:.2f}ms"


# Pytest configuration
def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Neo4j)"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
