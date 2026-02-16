"""
Query Intent Classifier

Analyzes natural language queries and classifies their intent
for routing to appropriate query execution strategies.
"""

import re
from typing import Dict, List, Optional, Tuple, Set

from neo4j_orchestration.planning.intent import (
    QueryType,
    QueryIntent,
    EntityType,
    FilterCondition,
    FilterOperator,
    Aggregation,
    AggregationType,
)


class QueryIntentClassifier:
    """
    Classifies natural language queries into structured query intents.
    
    Uses pattern matching and keyword analysis to determine:
    - Query type (vendor risk, compliance, control effectiveness, etc.)
    - Target entities (vendors, controls, regulations, etc.)
    - Filter conditions (risk levels, statuses, dates, etc.)
    - Aggregations (counts, groupings, etc.)
    
    Example:
        >>> classifier = QueryIntentClassifier()
        >>> intent = classifier.classify("Show me all vendors with critical risks")
        >>> print(intent.query_type)
        QueryType.VENDOR_RISK
    """
    
    def __init__(self):
        """Initialize the classifier with pattern definitions."""
        self._query_patterns = self._build_query_patterns()
        self._entity_keywords = self._build_entity_keywords()
        self._filter_patterns = self._build_filter_patterns()
        self._aggregation_keywords = self._build_aggregation_keywords()
    
    def classify(self, query: str) -> QueryIntent:
        """
        Classify a natural language query into structured intent.
        
        Args:
            query: Natural language query string
            
        Returns:
            QueryIntent object with classified components
        """
        query_lower = query.lower().strip()
        
        # Step 1: Determine query type
        query_type, confidence = self._classify_query_type(query_lower)
        
        # Step 2: Extract entities
        entities = self._extract_entities(query_lower)
        
        # Step 3: Extract filters
        filters = self._extract_filters(query_lower, entities)
        
        # Step 4: Extract aggregations
        aggregations = self._extract_aggregations(query_lower)
        
        # Step 5: Extract sorting and limits
        sort_by, sort_order = self._extract_sorting(query_lower)
        limit = self._extract_limit(query_lower)
        
        # Step 6: Check for relationship inclusion
        include_relationships = self._check_relationships(query_lower)
        
        # Create query intent
        intent = QueryIntent(
            query_type=query_type,
            entities=entities,
            filters=filters,
            aggregations=aggregations,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            include_relationships=include_relationships,
            confidence=confidence,
            metadata={"original_query": query}
        )
        
        return intent
    
    def _classify_query_type(self, query: str) -> Tuple[QueryType, float]:
        """
        Determine the query type from patterns.
        
        Returns:
            Tuple of (QueryType, confidence_score)
        """
        best_match = QueryType.UNKNOWN
        best_confidence = 0.5
        
        for query_type, patterns in self._query_patterns.items():
            for pattern, confidence in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    if confidence > best_confidence:
                        best_match = query_type
                        best_confidence = confidence
        
        return best_match, best_confidence
    
    def _extract_entities(self, query: str) -> List[EntityType]:
        """Extract entity types mentioned in the query."""
        entities = []
        seen = set()
        
        for entity_type, keywords in self._entity_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', query, re.IGNORECASE):
                    if entity_type not in seen:
                        entities.append(entity_type)
                        seen.add(entity_type)
        
        return entities
    
    def _extract_filters(
        self,
        query: str,
        entities: List[EntityType]
    ) -> List[FilterCondition]:
        """Extract filter conditions from the query."""
        filters = []
        
        for pattern_info in self._filter_patterns:
            field = pattern_info["field"]
            patterns = pattern_info["patterns"]
            operator = pattern_info["operator"]
            value_type = pattern_info.get("value_type", "string")
            entity_type = pattern_info.get("entity_type")
            
            for pattern, value in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    # Convert value based on type
                    if value_type == "boolean":
                        filter_value = value
                    elif value_type == "number":
                        filter_value = value
                    else:
                        filter_value = value
                    
                    filters.append(FilterCondition(
                        field=field,
                        operator=operator,
                        value=filter_value,
                        entity_type=entity_type
                    ))
        
        return filters
    
    def _extract_aggregations(self, query: str) -> Optional[List[Aggregation]]:
        """Extract aggregation operations from the query."""
        aggregations = []
        
        for agg_type, keywords in self._aggregation_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', query, re.IGNORECASE):
                    # Determine field based on context
                    field = None
                    if agg_type != AggregationType.COUNT:
                        # Try to extract field name
                        field = self._extract_aggregation_field(query, keyword)
                    
                    aggregations.append(Aggregation(
                        type=agg_type,
                        field=field,
                        alias=f"{agg_type.value}_result"
                    ))
        
        return aggregations if aggregations else None
    
    def _extract_aggregation_field(self, query: str, keyword: str) -> Optional[str]:
        """Extract the field name for an aggregation operation."""
        # Simple heuristic: look for common field names near the keyword
        common_fields = ["risk", "score", "count", "amount", "value", "rating"]
        
        for field in common_fields:
            if field in query.lower():
                return field
        
        return None
    
    def _extract_sorting(self, query: str) -> Tuple[Optional[str], str]:
        """Extract sorting information from the query."""
        sort_by = None
        sort_order = "ASC"
        
        # Check for sorting keywords
        if re.search(r'\b(sort(ed)?|order(ed)?)\s+(by|on)\b', query, re.IGNORECASE):
            # Extract sort field
            sort_match = re.search(
                r'\b(?:sort(?:ed)?|order(?:ed)?)\s+(?:by|on)\s+(\w+)',
                query,
                re.IGNORECASE
            )
            if sort_match:
                sort_by = sort_match.group(1)
        
        # Check for order direction
        if re.search(r'\b(descending|desc|highest|most)\b', query, re.IGNORECASE):
            sort_order = "DESC"
        
        return sort_by, sort_order
    
    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract result limit from the query."""
        # Look for "top N", "first N", "limit N"
        limit_match = re.search(
            r'\b(?:top|first|limit)\s+(\d+)\b',
            query,
            re.IGNORECASE
        )
        
        if limit_match:
            return int(limit_match.group(1))
        
        return None
    
    def _check_relationships(self, query: str) -> bool:
        """Check if query should include relationships."""
        relationship_keywords = [
            "relationship", "connection", "dependency", "impact",
            "related", "connected", "linked"
        ]
        
        return any(keyword in query for keyword in relationship_keywords)
    
    def _build_query_patterns(self) -> Dict[QueryType, List[Tuple[str, float]]]:
        """Build regex patterns for each query type."""
        return {
            QueryType.VENDOR_RISK: [
                (r'\b(vendor|supplier)s?\s+(with|having)\s+(critical|high|medium|low)?\s*risk', 0.95),
                (r'\brisk\w*\s+(vendor|supplier)', 0.9),
                (r'\b(vendor|supplier)\s+risk', 0.9),
            ],
            QueryType.VENDOR_LIST: [
                (r'\b(list|show|display|get)\s+(all\s+)?(vendor|supplier)s?', 0.9),
                (r'\b(vendor|supplier)s?\s+(list|directory)', 0.85),
            ],
            QueryType.VENDOR_DETAILS: [
                (r'\b(details?|information|info)\s+(about|for|on)\s+(vendor|supplier)', 0.95),
                (r'\b(vendor|supplier)\s+(details?|profile)', 0.9),
            ],
            QueryType.VENDOR_CONTROLS: [
                (r'\b(vendor|supplier)\s+control', 0.95),
                (r'\bcontrol\w*\s+(for|of)\s+(vendor|supplier)', 0.9),
            ],
            QueryType.VENDOR_CONCENTRATION: [
                (r'\b(vendor|supplier)\s+concentration', 0.95),
                (r'\bconcentration\s+(risk|analysis)', 0.9),
            ],
            QueryType.COMPLIANCE_STATUS: [
                (r'\bcompliance\s+status', 0.95),
                (r'\b(compliant|non-compliant)', 0.85),
            ],
            QueryType.REGULATION_DETAILS: [
                (r'\bregulation\s+(details?|information)', 0.95),
                (r'\b(bsa|aml|fcra|ecoa)\s+(requirement|rule)', 0.9),
            ],
            QueryType.COMPLIANCE_GAPS: [
                (r'\bcompliance\s+gap', 0.95),
                (r'\b(gap|deficienc)', 0.85),
            ],
            QueryType.CONTROL_EFFECTIVENESS: [
                (r'\bcontrol\s+effectiveness', 0.95),
                (r'\beffective\s+control', 0.85),
            ],
            QueryType.CONTROL_COVERAGE: [
                (r'\bcontrol\s+coverage', 0.95),
                (r'\bcoverage\s+analysis', 0.85),
            ],
            QueryType.CONTROL_BLAST_RADIUS: [
                (r'\bblast\s+radius', 0.95),
                (r'\bimpact\s+analysis', 0.8),
            ],
            QueryType.RISK_ASSESSMENT: [
                (r'\brisk\s+assessment', 0.95),
                (r'\bassess\w*\s+risk', 0.85),
            ],
            QueryType.ISSUE_TRACKING: [
                (r'\b(issue|finding|exception)', 0.9),
                (r'\b(track|monitor)\s+(issue|finding)', 0.85),
            ],
        }
    
    def _build_entity_keywords(self) -> Dict[EntityType, List[str]]:
        """Build keyword mappings for entity types."""
        return {
            EntityType.VENDOR: ["vendors?", "suppliers?", "third part(y|ies)", "providers?"],
            EntityType.CONTROL: ["controls?", "safeguards?", "measures?"],
            EntityType.REGULATION: [
                "regulations?", "rules?", "requirements?", "laws?",
                "bsa", "aml", "fcra", "ecoa", "fair lending"
            ],
            EntityType.RISK: ["risks?", "threats?", "exposures?", "vulnerabilit(y|ies)"],
            EntityType.ISSUE: ["issues?", "findings?", "exceptions?", "deficienc(y|ies)"],
            EntityType.ASSESSMENT: ["assessments?", "evaluations?", "reviews?"],
        }
    
    def _build_filter_patterns(self) -> List[Dict]:
        """Build filter patterns for extraction."""
        return [
            {
                "field": "riskLevel",
                "operator": FilterOperator.EQUALS,
                "patterns": [
                    (r'\bcritical\s+risk', "Critical"),
                    (r'\bhigh\s+risk', "High"),
                    (r'\bmedium\s+risk', "Medium"),
                    (r'\blow\s+risk', "Low"),
                ],
                "value_type": "string",
                "entity_type": EntityType.VENDOR
            },
            {
                "field": "status",
                "operator": FilterOperator.EQUALS,
                "patterns": [
                    (r'\bactive', "Active"),
                    (r'\binactive', "Inactive"),
                    (r'\bpending', "Pending"),
                ],
                "value_type": "string"
            },
            {
                "field": "compliant",
                "operator": FilterOperator.EQUALS,
                "patterns": [
                    (r'\bcompliant\b', True),
                    (r'\bnon-compliant', False),
                ],
                "value_type": "boolean"
            },
            {
                "field": "effectiveness",
                "operator": FilterOperator.EQUALS,
                "patterns": [
                    (r'\beffective', "Effective"),
                    (r'\bineffective', "Ineffective"),
                ],
                "value_type": "string",
                "entity_type": EntityType.CONTROL
            },
        ]
    
    def _build_aggregation_keywords(self) -> Dict[AggregationType, List[str]]:
        """Build keyword mappings for aggregation types."""
        return {
            AggregationType.COUNT: ["count", "number of", "how many", "total"],
            AggregationType.SUM: ["sum", "total amount", "add up"],
            AggregationType.AVG: ["average", "mean", "avg"],
            AggregationType.MAX: ["maximum", "max", "highest", "most"],
            AggregationType.MIN: ["minimum", "min", "lowest", "least"],
            AggregationType.GROUP_BY: ["group by", "grouped by", "by category"],
        }
