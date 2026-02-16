"""Query execution result types."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionMetadata:
    """Metadata about query execution."""
    
    query: str
    parameters: Dict[str, Any]
    result_available_after: Optional[int] = None
    result_consumed_after: Optional[int] = None
    counters: Optional[Dict[str, int]] = None
    
    @classmethod
    def from_summary(cls, query: str, parameters: Dict[str, Any], summary: Any) -> "ExecutionMetadata":
        """Create metadata from Neo4j result summary."""
        counters = None
        if hasattr(summary, "counters") and summary.counters is not None:
            c = summary.counters
            counters = {
                "nodes_created": c.nodes_created,
                "nodes_deleted": c.nodes_deleted,
                "relationships_created": c.relationships_created,
                "relationships_deleted": c.relationships_deleted,
                "properties_set": c.properties_set,
                "labels_added": c.labels_added,
                "labels_removed": c.labels_removed,
            }
        
        return cls(
            query=query,
            parameters=parameters,
            result_available_after=getattr(summary, "result_available_after", None),
            result_consumed_after=getattr(summary, "result_consumed_after", None),
            counters=counters,
        )


@dataclass
class QueryResult:
    """Result of a query execution."""
    
    records: List[Dict[str, Any]]
    metadata: ExecutionMetadata
    summary: str
    
    def __len__(self) -> int:
        return len(self.records)
    
    def __iter__(self):
        return iter(self.records)
    
    def __getitem__(self, index: int) -> Dict[str, Any]:
        return self.records[index]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "records": self.records,
            "count": len(self.records),
            "summary": self.summary,
            "metadata": {
                "query": self.metadata.query,
                "parameters": self.metadata.parameters,
                "timing": {
                    "available_after_ms": self.metadata.result_available_after,
                    "consumed_after_ms": self.metadata.result_consumed_after,
                },
                "counters": self.metadata.counters,
            }
        }
