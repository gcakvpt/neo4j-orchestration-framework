"""
Query Intent Types and Data Structures

Defines the types of queries supported and data structures for
representing classified query intent.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class QueryType(Enum):
    """Generic query operation types for knowledge graph queries."""
    
    # Generic operations (new architecture)
    LIST = "list"
    FILTER = "filter"
    DETAILS = "details"
    RELATIONSHIP = "relationship"
    AGGREGATE = "aggregate"
    COMPARE = "compare"
    ANALYZE = "analyze"
    UNKNOWN = "unknown"
    
    # Legacy domain-specific types (backward compatibility)
    VENDOR_RISK = "vendor_risk"
    VENDOR_LIST = "vendor_list"
    VENDOR_DETAILS = "vendor_details"
    VENDOR_CONTROLS = "vendor_controls"
    VENDOR_CONCENTRATION = "vendor_concentration"
    COMPLIANCE_STATUS = "compliance_status"
    REGULATION_DETAILS = "regulation_details"
    COMPLIANCE_GAPS = "compliance_gaps"
    CONTROL_EFFECTIVENESS = "control_effectiveness"
    CONTROL_COVERAGE = "control_coverage"
    CONTROL_BLAST_RADIUS = "control_blast_radius"
    RISK_ASSESSMENT = "risk_assessment"
    RISK_TRENDS = "risk_trends"
    ISSUE_TRACKING = "issue_tracking"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    IMPACT_ANALYSIS = "impact_analysis"
    
    @property
    def is_generic(self) -> bool:
        return self in {QueryType.LIST, QueryType.FILTER, QueryType.DETAILS, QueryType.RELATIONSHIP, QueryType.AGGREGATE, QueryType.COMPARE, QueryType.ANALYZE, QueryType.UNKNOWN}
    
    @property
    def is_legacy(self) -> bool:
        return not self.is_generic
    
    def to_generic(self) -> "QueryType":
        mapping = {QueryType.VENDOR_LIST: QueryType.LIST, QueryType.VENDOR_DETAILS: QueryType.DETAILS, QueryType.VENDOR_CONTROLS: QueryType.RELATIONSHIP, QueryType.VENDOR_CONCENTRATION: QueryType.AGGREGATE, QueryType.VENDOR_RISK: QueryType.ANALYZE, QueryType.COMPLIANCE_STATUS: QueryType.FILTER, QueryType.REGULATION_DETAILS: QueryType.DETAILS, QueryType.COMPLIANCE_GAPS: QueryType.ANALYZE, QueryType.CONTROL_EFFECTIVENESS: QueryType.ANALYZE, QueryType.CONTROL_COVERAGE: QueryType.AGGREGATE, QueryType.CONTROL_BLAST_RADIUS: QueryType.ANALYZE, QueryType.RISK_ASSESSMENT: QueryType.ANALYZE, QueryType.RISK_TRENDS: QueryType.AGGREGATE, QueryType.ISSUE_TRACKING: QueryType.FILTER, QueryType.DEPENDENCY_ANALYSIS: QueryType.RELATIONSHIP, QueryType.IMPACT_ANALYSIS: QueryType.RELATIONSHIP}
        return mapping.get(self, self)


class EntityType(Enum):
    """Types of entities in the knowledge graph."""
    
    VENDOR = "Vendor"
    CONTROL = "Control"
    REGULATION = "Regulation"
    RISK = "Risk"
    ISSUE = "Issue"
    ASSESSMENT = "Assessment"
    BUSINESS_UNIT = "BusinessUnit"
    TECHNOLOGY = "Technology"


class AggregationType(Enum):
    """Types of aggregations supported."""
    
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    GROUP_BY = "group_by"


class FilterOperator(Enum):
    """Operators for filter conditions."""
    
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS WITH"
    ENDS_WITH = "ENDS WITH"
    IN = "IN"
    NOT_IN = "NOT IN"


@dataclass
class FilterCondition:
    """Represents a single filter condition."""
    
    field: str
    operator: FilterOperator
    value: Any
    entity_type: Optional[EntityType] = None
    
    def __post_init__(self):
        """Validate filter condition."""
        if not self.field:
            raise ValueError("Filter field cannot be empty")
        
        if isinstance(self.operator, str):
            self.operator = FilterOperator(self.operator)


@dataclass
class Aggregation:
    """Represents an aggregation operation."""
    
    type: AggregationType
    field: Optional[str] = None
    alias: Optional[str] = None
    group_by: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate aggregation."""
        if isinstance(self.type, str):
            self.type = AggregationType(self.type)
        
        if self.type != AggregationType.COUNT and not self.field:
            raise ValueError(f"Aggregation type {self.type} requires a field")


@dataclass
class QueryIntent:
    """
    Represents the classified intent of a natural language query.
    
    This is the output of the QueryIntentClassifier and the input
    to the CypherGenerator.
    """
    
    query_type: QueryType
    entities: List[EntityType] = field(default_factory=list)
    filters: List[FilterCondition] = field(default_factory=list)
    aggregations: Optional[List[Aggregation]] = None
    sort_by: Optional[str] = None
    sort_order: str = "ASC"
    limit: Optional[int] = None
    include_relationships: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    
    def __post_init__(self):
        """Validate query intent."""
        if isinstance(self.query_type, str):
            self.query_type = QueryType(self.query_type)
        
        # Convert entity strings to EntityType enums
        self.entities = [
            EntityType(e) if isinstance(e, str) else e
            for e in self.entities
        ]
        
        # Validate confidence
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        # Validate sort order
        if self.sort_order not in ["ASC", "DESC"]:
            raise ValueError("Sort order must be 'ASC' or 'DESC'")
    
    def add_filter(
        self,
        field: str,
        operator: FilterOperator,
        value: Any,
        entity_type: Optional[EntityType] = None
    ) -> None:
        """Add a filter condition to the query intent."""
        self.filters.append(
            FilterCondition(field, operator, value, entity_type)
        )
    
    def add_aggregation(
        self,
        agg_type: AggregationType,
        field: Optional[str] = None,
        alias: Optional[str] = None,
        group_by: Optional[List[str]] = None
    ) -> None:
        """Add an aggregation to the query intent."""
        if self.aggregations is None:
            self.aggregations = []
        
        self.aggregations.append(
            Aggregation(agg_type, field, alias, group_by)
        )
    
    def get_primary_entity(self) -> Optional[EntityType]:
        """Get the primary entity type for this query."""
        return self.entities[0] if self.entities else None
    
    def has_filters(self) -> bool:
        """Check if query has any filters."""
        return len(self.filters) > 0
    
    def has_aggregations(self) -> bool:
        """Check if query has any aggregations."""
        return self.aggregations is not None and len(self.aggregations) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query intent to dictionary."""
        return {
            "query_type": self.query_type.value,
            "entities": [e.value for e in self.entities],
            "filters": [
                {
                    "field": f.field,
                    "operator": f.operator.value,
                    "value": f.value,
                    "entity_type": f.entity_type.value if f.entity_type else None
                }
                for f in self.filters
            ],
            "aggregations": [
                {
                    "type": a.type.value,
                    "field": a.field,
                    "alias": a.alias,
                    "group_by": a.group_by
                }
                for a in self.aggregations
            ] if self.aggregations else None,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "limit": self.limit,
            "include_relationships": self.include_relationships,
            "metadata": self.metadata,
            "confidence": self.confidence
        }
