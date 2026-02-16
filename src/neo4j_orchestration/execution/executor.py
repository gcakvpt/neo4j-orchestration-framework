"""Query executor for Neo4j database operations."""

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from .config import Neo4jConfig
from .result import QueryResult, ExecutionMetadata


logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Base exception for execution errors."""
    pass


class ConnectionError(ExecutionError):
    """Exception for connection-related errors."""
    pass


class QueryError(ExecutionError):
    """Exception for query execution errors."""
    pass


class QueryExecutor:
    """Executes Cypher queries against Neo4j database."""
    
    def __init__(self, config: Neo4jConfig):
        """Initialize query executor."""
        self.config = config
        self._driver: Optional[Driver] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_timeout=self.config.connection_timeout,
            )
            
            self.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.config.uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise ConnectionError(f"Failed to connect to Neo4j: {e}") from e
    
    def verify_connectivity(self) -> bool:
        """Verify database connectivity."""
        if not self._driver:
            raise ConnectionError("Driver not initialized")
        
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Connectivity verification failed: {e}")
            raise ConnectionError(f"Connectivity verification failed: {e}") from e
    
    def execute(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> QueryResult:
        """Execute a Cypher query (read operation)."""
        if not self._driver:
            raise ConnectionError("Driver not initialized")
        
        parameters = parameters or {}
        database = database or self.config.database
        
        try:
            with self._driver.session(database=database) as session:
                result = session.run(query, parameters)
                
                records = []
                for record in result:
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        record_dict[key] = self._convert_value(value)
                    records.append(record_dict)
                
                summary = result.consume()
                metadata = ExecutionMetadata.from_summary(query, parameters, summary)
                summary_text = self._create_summary(records, metadata)
                
                logger.info(f"Query executed: {len(records)} records returned")
                
                return QueryResult(
                    records=records,
                    metadata=metadata,
                    summary=summary_text,
                )
                
        except (ServiceUnavailable, SessionExpired) as e:
            logger.error(f"Connection error during query execution: {e}")
            raise ConnectionError(f"Connection error: {e}") from e
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise QueryError(f"Query execution failed: {e}") from e
    
    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> QueryResult:
        """Execute a write query in a transaction."""
        if not self._driver:
            raise ConnectionError("Driver not initialized")
        
        parameters = parameters or {}
        database = database or self.config.database
        
        def _execute_tx(tx):
            result = tx.run(query, parameters)
            records = []
            for record in result:
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    record_dict[key] = self._convert_value(value)
                records.append(record_dict)
            summary = result.consume()
            return records, summary
        
        try:
            with self._driver.session(database=database) as session:
                records, summary = session.execute_write(_execute_tx)
                
                metadata = ExecutionMetadata.from_summary(query, parameters, summary)
                summary_text = self._create_summary(records, metadata)
                
                logger.info(f"Write query executed")
                
                return QueryResult(
                    records=records,
                    metadata=metadata,
                    summary=summary_text,
                )
                
        except Exception as e:
            logger.error(f"Write query execution failed: {e}")
            raise QueryError(f"Write query execution failed: {e}") from e
    
    def _convert_value(self, value: Any) -> Any:
        """Convert Neo4j value to Python native type."""
        if hasattr(value, 'labels') and hasattr(value, 'items'):
            return {
                'id': value.id,
                'labels': list(value.labels),
                'properties': dict(value.items()),
            }
        
        if hasattr(value, 'type') and hasattr(value, 'start_node'):
            return {
                'id': value.id,
                'type': value.type,
                'start_node': value.start_node.id,
                'end_node': value.end_node.id,
                'properties': dict(value.items()),
            }
        
        if isinstance(value, list):
            return [self._convert_value(v) for v in value]
        
        if isinstance(value, dict):
            return {k: self._convert_value(v) for k, v in value.items()}
        
        return value
    
    def _create_summary(
        self,
        records: List[Dict[str, Any]],
        metadata: ExecutionMetadata
    ) -> str:
        """Create human-readable summary."""
        count = len(records)
        
        if metadata.counters:
            mutations = []
            c = metadata.counters
            if c.get("nodes_created", 0) > 0:
                mutations.append(f"{c['nodes_created']} nodes created")
            if c.get("relationships_created", 0) > 0:
                mutations.append(f"{c['relationships_created']} relationships created")
            if c.get("properties_set", 0) > 0:
                mutations.append(f"{c['properties_set']} properties set")
            
            if mutations:
                return f"Query executed: {', '.join(mutations)}"
        
        if count == 0:
            return "No results found"
        elif count == 1:
            return "Found 1 result"
        else:
            return f"Found {count} results"
    
    def close(self) -> None:
        """Close database connection and cleanup resources."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
