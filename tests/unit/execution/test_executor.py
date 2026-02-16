"""
Unit tests for QueryExecutor.

Tests executor functionality with mocked Neo4j driver.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from neo4j_orchestration.execution import QueryExecutor, Neo4jConfig, QueryResult
from neo4j_orchestration.execution.executor import (
    ConnectionError,
    QueryError,
)


@pytest.fixture
def config():
    """Create test configuration."""
    return Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test_password",
        database="neo4j",
    )


@pytest.fixture
def mock_driver():
    """Create mock Neo4j driver."""
    driver = MagicMock()
    driver.verify_connectivity.return_value = None
    return driver


@pytest.fixture
def mock_session():
    """Create mock Neo4j session."""
    session = MagicMock()
    return session


class TestQueryExecutorInit:
    """Test QueryExecutor initialization."""
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_successful_initialization(self, mock_graph_db, config, mock_driver):
        """Test successful executor initialization."""
        mock_graph_db.driver.return_value = mock_driver
        
        executor = QueryExecutor(config)
        
        assert executor.config == config
        assert executor._driver is not None
        mock_graph_db.driver.assert_called_once()
        mock_driver.verify_connectivity.assert_called_once()
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_initialization_connection_failure(self, mock_graph_db, config):
        """Test initialization fails when connection fails."""
        mock_graph_db.driver.side_effect = ServiceUnavailable("Connection failed")
        
        with pytest.raises(ConnectionError, match="Failed to connect"):
            QueryExecutor(config)


class TestQueryExecution:
    """Test query execution."""
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_execute_simple_query(self, mock_graph_db, config, mock_driver, mock_session):
        """Test executing a simple query."""
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock result
        mock_record = MagicMock()
        mock_record.keys.return_value = ['name', 'count']
        mock_record.__getitem__.side_effect = lambda k: 'TestVendor' if k == 'name' else 5
        
        mock_result = MagicMock()
        mock_result.__iter__.return_value = [mock_record]
        mock_session.run.return_value = mock_result
        
        # Mock summary
        mock_summary = MagicMock()
        mock_summary.result_available_after = 10
        mock_summary.result_consumed_after = 15
        mock_summary.counters = None
        mock_result.consume.return_value = mock_summary
        
        executor = QueryExecutor(config)
        result = executor.execute("MATCH (v:Vendor) RETURN v.name AS name, count(v) AS count")
        
        assert isinstance(result, QueryResult)
        assert len(result.records) == 1
        assert result.records[0]['name'] == 'TestVendor'
        assert result.records[0]['count'] == 5
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_execute_with_parameters(self, mock_graph_db, config, mock_driver, mock_session):
        """Test executing query with parameters."""
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []
        mock_summary = MagicMock()
        mock_summary.counters = None
        mock_result.consume.return_value = mock_summary
        mock_session.run.return_value = mock_result
        
        executor = QueryExecutor(config)
        query = "MATCH (v:Vendor) WHERE v.riskLevel = $riskLevel RETURN v"
        params = {"riskLevel": "Critical"}
        
        result = executor.execute(query, params)
        
        mock_session.run.assert_called_once_with(query, params)
        assert result.metadata.parameters == params
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_execute_no_results(self, mock_graph_db, config, mock_driver, mock_session):
        """Test executing query with no results."""
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []
        mock_summary = MagicMock()
        mock_summary.counters = None
        mock_result.consume.return_value = mock_summary
        mock_session.run.return_value = mock_result
        
        executor = QueryExecutor(config)
        result = executor.execute("MATCH (v:Vendor) WHERE v.name = 'NonExistent' RETURN v")
        
        assert len(result.records) == 0
        assert result.summary == "No results found"


class TestErrorHandling:
    """Test error handling."""
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_connection_error_during_execution(self, mock_graph_db, config, mock_driver, mock_session):
        """Test connection error during query execution."""
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.side_effect = ServiceUnavailable("Connection lost")
        
        executor = QueryExecutor(config)
        
        with pytest.raises(ConnectionError, match="Connection error"):
            executor.execute("MATCH (n) RETURN n")
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_query_error(self, mock_graph_db, config, mock_driver, mock_session):
        """Test query execution error."""
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.side_effect = Exception("Invalid query syntax")
        
        executor = QueryExecutor(config)
        
        with pytest.raises(QueryError, match="Query execution failed"):
            executor.execute("INVALID QUERY")


class TestContextManager:
    """Test context manager functionality."""
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_context_manager(self, mock_graph_db, config, mock_driver):
        """Test using executor as context manager."""
        mock_graph_db.driver.return_value = mock_driver
        
        with QueryExecutor(config) as executor:
            assert executor._driver is not None
        
        mock_driver.close.assert_called_once()
    
    @patch('neo4j_orchestration.execution.executor.GraphDatabase')
    def test_close_method(self, mock_graph_db, config, mock_driver):
        """Test close method."""
        mock_graph_db.driver.return_value = mock_driver
        
        executor = QueryExecutor(config)
        executor.close()
        
        mock_driver.close.assert_called_once()
        assert executor._driver is None
