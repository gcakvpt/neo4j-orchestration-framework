"""
Integration tests for execution with planning pipeline.

Tests the complete flow: Natural Language → Cypher → Execution
"""

import pytest
from unittest.mock import MagicMock, patch

from neo4j_orchestration.planning import QueryIntentClassifier, CypherQueryGenerator
from neo4j_orchestration.execution import QueryExecutor, Neo4jConfig


@pytest.fixture
def config():
    """Create test configuration."""
    return Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
    )


@pytest.fixture
def mock_driver():
    """Create mock Neo4j driver."""
    driver = MagicMock()
    driver.verify_connectivity.return_value = None
    return driver


@pytest.fixture
def mock_session():
    """Create mock session."""
    session = MagicMock()
    return session


class TestEndToEndPipeline:
    """Test complete pipeline from NL to execution."""
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_count_vendors_pipeline(self, mock_graph_db, config, mock_driver, mock_session):
        """Test: Natural Language → Intent → Cypher → Execute."""
        # Setup mocks
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock count result
        mock_record = MagicMock()
        mock_record.keys.return_value = ['count_result']
        mock_record.__getitem__.return_value = 42
        
        mock_result = MagicMock()
        mock_result.__iter__.return_value = [mock_record]
        mock_summary = MagicMock()
        mock_summary.counters = None
        mock_result.consume.return_value = mock_summary
        mock_session.run.return_value = mock_result
        
        # Execute pipeline
        classifier = QueryIntentClassifier()
        generator = CypherQueryGenerator()
        executor = QueryExecutor(config)
        
        # Step 1: Classify
        intent = classifier.classify("Count all vendors")
        assert intent.query_type.value == "vendor_list"
        
        # Step 2: Generate Cypher
        query, params = generator.generate(intent)
        assert "MATCH" in query
        assert "count" in query.lower()
        
        # Step 3: Execute
        result = executor.execute(query, params)
        assert len(result.records) == 1
        assert result.records[0]['count_result'] == 42
        
        executor.close()
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_filtered_query_pipeline(self, mock_graph_db, config, mock_driver, mock_session):
        """Test: Natural Language with filters → Execute."""
        # Setup mocks
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock vendor results
        mock_records = []
        for i in range(3):
            mock_record = MagicMock()
            mock_record.keys.return_value = ['v']
            mock_node = MagicMock()
            mock_node.id = i
            mock_node.labels = ['Vendor']
            mock_node.items.return_value = [
                ('name', f'Vendor{i}'),
                ('riskLevel', 'Critical'),
            ]
            mock_record.__getitem__.return_value = mock_node
            mock_records.append(mock_record)
        
        mock_result = MagicMock()
        mock_result.__iter__.return_value = mock_records
        mock_summary = MagicMock()
        mock_summary.counters = None
        mock_result.consume.return_value = mock_summary
        mock_session.run.return_value = mock_result
        
        # Execute pipeline
        classifier = QueryIntentClassifier()
        generator = CypherQueryGenerator()
        executor = QueryExecutor(config)
        
        # Full pipeline
        intent = classifier.classify("Show vendors with critical risk")
        query, params = generator.generate(intent)
        result = executor.execute(query, params)
        
        # Verify
        assert len(result.records) == 3
        assert result.records[0]['v']['properties']['riskLevel'] == 'Critical'
        assert params.get('riskLevel') == 'Critical'
        
        executor.close()


class TestExecutorWithGenerator:
    """Test executor with generated queries."""
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_execute_generated_simple_query(self, mock_graph_db, config, mock_driver, mock_session):
        """Test executing a generator-produced simple query."""
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []
        mock_summary = MagicMock()
        mock_summary.counters = None
        mock_result.consume.return_value = mock_summary
        mock_session.run.return_value = mock_result
        
        generator = CypherQueryGenerator()
        executor = QueryExecutor(config)
        
        from neo4j_orchestration.planning import QueryIntent, QueryType, EntityType
        
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        query, params = generator.generate(intent)
        result = executor.execute(query, params)
        
        assert result.summary == "No results found"
        mock_session.run.assert_called_once_with(query, params)
        
        executor.close()
