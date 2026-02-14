"""
Core type definitions for the orchestration framework.

These types are used across all components to ensure consistency
and provide type safety. They define the fundamental data structures
that flow through the system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ENUMS: Define valid choices for certain fields
# ============================================================================

class MemoryType(str, Enum):
    """Type of memory system
    
    Used by: Orchestrator to route queries to correct memory system
    """
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class AnalyticsAlgorithm(str, Enum):
    """Available graph analytics algorithms
    
    Used by: AnalyticsCoordinator to select algorithm
    """
    PAGERANK = "pagerank"
    BETWEENNESS = "betweenness"
    DEGREE_CENTRALITY = "degree_centrality"
    LOUVAIN = "louvain"
    WCC = "wcc"
    SHORTEST_PATH = "shortest_path"
    NODE_SIMILARITY = "node_similarity"


class QueryIntent(str, Enum):
    """User query intent classification
    
    Used by: IntentRecognizer to determine query type
    """
    ENTITY_LOOKUP = "entity_lookup"
    RELATIONSHIP_TRAVERSAL = "traversal"
    PATTERN_MATCH = "pattern_match"
    AGGREGATION = "aggregation"
    ANALYTICS = "analytics"
    TEMPORAL = "temporal"


# ============================================================================
# BASE MODELS: Common patterns used by multiple components
# ============================================================================

class BaseConfig(BaseModel):
    """Base configuration with common validation"""
    
    class Config:
        extra = "allow"
        use_enum_values = True


class Metadata(BaseModel):
    """Generic metadata container"""
    
    data: Dict[str, Any] = Field(default_factory=dict)
    
    def set(self, key: str, value: Any) -> None:
        """Set metadata value"""
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get metadata value with default"""
        return self.data.get(key, default)


# ============================================================================
# MEMORY TYPES
# ============================================================================

class AnalysisSession(BaseModel):
    """Represents a single analysis session
    
    Used by: Episodic memory to store historical analyses
    """
    
    session_id: str = Field(..., description="Unique session identifier")
    timestamp: datetime = Field(..., description="When analysis was performed")
    entity_id: Optional[str] = Field(None, description="Primary entity analyzed")
    workflow_name: str = Field(..., description="Workflow that created this session")
    query_text: Optional[str] = Field(None, description="Original user query")
    results: Dict[str, Any] = Field(default_factory=dict, description="Analysis results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        """Parse string timestamps to datetime"""
        if isinstance(v, str):
            from dateutil.parser import parse
            return parse(v)
        return v


class MemoryEntry(BaseModel):
    """Generic memory entry"""
    
    key: str = Field(..., description="Unique key for this entry")
    value: Any = Field(..., description="The stored value")
    memory_type: MemoryType = Field(..., description="Type of memory")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="When entry expires (TTL)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# QUERY PLANNING TYPES
# ============================================================================

class QueryContext(BaseModel):
    """Context information for query planning"""
    
    intent: QueryIntent = Field(..., description="Classified user intent")
    entity_type: Optional[str] = Field(None, description="Primary entity type")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter conditions")
    scope: Optional[str] = Field(None, description="Business context scope")
    temporal_range: Optional[Dict[str, datetime]] = Field(None, description="Time range filter")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryStep(BaseModel):
    """Single step in query execution plan"""
    
    step_id: str = Field(..., description="Step identifier")
    operation: str = Field(..., description="Operation type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Step parameters")
    depends_on: List[str] = Field(default_factory=list, description="Required previous steps")
    memory_type: Optional[MemoryType] = Field(None, description="Which memory to use")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryPlan(BaseModel):
    """Execution plan for a query"""
    
    query_id: str = Field(..., description="Unique query identifier")
    intent: QueryIntent = Field(..., description="Query intent")
    steps: List[QueryStep] = Field(default_factory=list, description="Execution steps")
    cypher_query: Optional[str] = Field(None, description="Generated Cypher query")
    estimated_cost: float = Field(0.0, description="Estimated execution cost (0-1)")
    requires_analytics: bool = Field(False, description="Whether GDS algorithms needed")
    context: Optional[QueryContext] = Field(None, description="Query context")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# ANALYTICS TYPES
# ============================================================================

class GraphProjection(BaseModel):
    """Graph Data Science projection configuration"""
    
    name: str = Field(..., description="Projection name")
    node_projection: Union[str, List[str], Dict] = Field(..., description="Node labels to project")
    relationship_projection: Union[str, List[str], Dict] = Field(..., description="Relationship types")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Additional GDS config")


class AnalyticsResult(BaseModel):
    """Result from graph analytics algorithm"""
    
    algorithm: AnalyticsAlgorithm = Field(..., description="Algorithm executed")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Algorithm results")
    projection_name: Optional[str] = Field(None, description="Graph projection used")
    execution_time_ms: Optional[float] = Field(None, description="Execution time")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# WORKFLOW TYPES
# ============================================================================

class WorkflowStep(BaseModel):
    """Single step in a workflow"""
    
    name: str = Field(..., description="Step name")
    description: Optional[str] = Field(None, description="Step description")
    function: Optional[str] = Field(None, description="Function name to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required: bool = Field(True, description="Whether step is required")
    retry_on_failure: bool = Field(False, description="Retry if step fails")


class WorkflowResult(BaseModel):
    """Result from workflow execution"""
    
    workflow_name: str = Field(..., description="Workflow that executed")
    success: bool = Field(..., description="Whether workflow succeeded")
    results: Dict[str, Any] = Field(default_factory=dict, description="Workflow results")
    steps_executed: List[str] = Field(default_factory=list, description="Steps completed")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    execution_time_ms: Optional[float] = Field(None, description="Total execution time")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# CONTEXT TYPES
# ============================================================================

class BusinessContext(BaseModel):
    """Business context for query execution"""
    
    scope: str = Field(..., description="Business scope")
    domain: Optional[str] = Field(None, description="Specific domain within scope")
    business_rules: List[str] = Field(default_factory=list, description="Active business rules")
    temporal_scope: Optional[Dict[str, Any]] = Field(None, description="Time constraints")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Context-specific filters")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Update forward references
QueryPlan.model_rebuild()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_session_id() -> str:
    """Generate unique session ID"""
    from uuid import uuid4
    return f"sess_{uuid4().hex[:8]}"


def create_query_id() -> str:
    """Generate unique query ID"""
    from uuid import uuid4
    return f"qry_{uuid4().hex[:8]}"


# Export all types
__all__ = [
    # Enums
    "MemoryType",
    "AnalyticsAlgorithm",
    "QueryIntent",
    # Base Models
    "BaseConfig",
    "Metadata",
    # Memory Types
    "AnalysisSession",
    "MemoryEntry",
    # Query Planning
    "QueryContext",
    "QueryPlan",
    "QueryStep",
    # Analytics
    "GraphProjection",
    "AnalyticsResult",
    # Workflow
    "WorkflowStep",
    "WorkflowResult",
    # Context
    "BusinessContext",
    # Helpers
    "create_session_id",
    "create_query_id",
]
