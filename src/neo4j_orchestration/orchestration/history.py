"""Query history tracking using episodic memory."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from neo4j_orchestration.memory.episodic import Event, SimpleEpisodicMemory


class QueryRecord(BaseModel):
    """Record of a single query execution.
    
    Attributes:
        query_id: Unique identifier for this query
        natural_language: Original NL query from user
        intent: Structured query intent
        cypher_query: Generated Cypher query
        parameters: Query parameters
        result_count: Number of results returned
        execution_time_ms: Execution time in milliseconds
        timestamp: When the query was executed
        success: Whether the query succeeded
        error_message: Error message if query failed
    """
    
    query_id: str = Field(description="Unique query identifier")
    natural_language: str = Field(description="Original NL query")
    intent: Dict[str, Any] = Field(description="Query intent as dict")
    cypher_query: str = Field(description="Generated Cypher")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    result_count: int = Field(default=0, ge=0, description="Number of results")
    execution_time_ms: float = Field(default=0.0, ge=0, description="Execution time")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    success: bool = Field(default=True, description="Query success status")
    error_message: Optional[str] = Field(default=None, description="Error if failed")
    
    @classmethod
    def from_event(cls, event: Event) -> "QueryRecord":
        """Create QueryRecord from Event stored in episodic memory."""
        content = event.content
        return cls(
            query_id=event.event_id,
            natural_language=content.get("natural_language", ""),
            intent=content.get("intent", {}),
            cypher_query=content.get("cypher_query", ""),
            parameters=content.get("parameters", {}),
            result_count=content.get("result_count", 0),
            execution_time_ms=content.get("execution_time_ms", 0.0),
            timestamp=event.timestamp,
            success=content.get("success", True),
            error_message=content.get("error_message"),
        )
    
    def to_event(self) -> Event:
        """Convert QueryRecord to Event for storage in episodic memory."""
        return Event(
            event_id=self.query_id,
            event_type="query_executed",
            content={
                "natural_language": self.natural_language,
                "intent": self.intent,
                "cypher_query": self.cypher_query,
                "parameters": self.parameters,
                "result_count": self.result_count,
                "execution_time_ms": self.execution_time_ms,
                "success": self.success,
                "error_message": self.error_message,
            },
            timestamp=self.timestamp,
        )


class QueryHistory:
    """Manages query history using simple episodic memory.
    
    Stores and retrieves query execution records for pattern analysis
    and "show me again" functionality.
    """
    
    def __init__(self, episodic_memory: SimpleEpisodicMemory, max_size: Optional[int] = 100):
        """Initialize query history.
        
        Args:
            episodic_memory: Simple episodic memory instance for storage
            max_size: Maximum number of queries to retain
        """
        self.episodic_memory = episodic_memory
        self.max_size = max_size
    
    def add_query(self, record: QueryRecord) -> None:
        """Add a query record to history.
        
        Args:
            record: Query record to store
        """
        event = record.to_event()
        self.episodic_memory.store(event)
        
        # Prune old records if max_size exceeded
        if self.max_size:
            self._prune_history()
    
    def get_last_query(self) -> Optional[QueryRecord]:
        """Get the most recent query.
        
        Returns:
            Most recent QueryRecord or None if no history
        """
        events = self.episodic_memory.retrieve_recent(
            event_type="query_executed",
            limit=1
        )
        
        if not events:
            return None
        
        return QueryRecord.from_event(events[0])
    
    def get_history(self, limit: int = 10) -> List[QueryRecord]:
        """Get recent query history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of QueryRecords, most recent first
        """
        events = self.episodic_memory.retrieve_recent(
            event_type="query_executed",
            limit=limit
        )
        
        return [QueryRecord.from_event(event) for event in events]
    
    def get_successful_queries(self, limit: int = 10) -> List[QueryRecord]:
        """Get recent successful queries.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of successful QueryRecords
        """
        all_history = self.get_history(limit=limit * 2)  # Get more to filter
        successful = [r for r in all_history if r.success]
        return successful[:limit]
    
    def search_by_entity_type(self, entity_type: str, limit: int = 10) -> List[QueryRecord]:
        """Find queries related to a specific entity type.
        
        Args:
            entity_type: Entity type to search for (e.g., "Vendor")
            limit: Maximum number of records to return
            
        Returns:
            List of matching QueryRecords
        """
        all_history = self.get_history(limit=limit * 2)
        matches = [
            r for r in all_history
            if r.intent.get("entity_type") == entity_type
        ]
        return matches[:limit]
    
    def _prune_history(self) -> None:
        """Remove oldest records if history exceeds max_size."""
        if not self.max_size:
            return
        
        # Get all query events
        all_events = self.episodic_memory.retrieve_recent(
            event_type="query_executed",
            limit=self.max_size + 100  # Get extra to prune
        )
        
        # If we have more than max_size, remove oldest
        if len(all_events) > self.max_size:
            events_to_remove = all_events[self.max_size:]
            for event in events_to_remove:
                self.episodic_memory.memory_store.pop(event.event_id, None)
