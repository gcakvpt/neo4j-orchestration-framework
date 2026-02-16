"""
Cypher Query Generator

Converts QueryIntent objects into executable Cypher queries using
template-based generation with parameter binding.
"""

from typing import Dict, List, Optional, Any, Tuple
from .intent import (
    QueryIntent,
    QueryType,
    EntityType,
    FilterCondition,
    FilterOperator,
    Aggregation,
    AggregationType
)


class CypherQueryGenerator:
    """
    Generates Cypher queries from QueryIntent objects.
    
    Uses template-based generation with parameter binding for
    safety and performance.
    """
    
    def __init__(self):
        """Initialize the Cypher query generator."""
        self.templates = self._build_query_templates()
        self.entity_labels = self._build_entity_label_map()
    
    def generate(self, intent: QueryIntent) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a Cypher query from a QueryIntent.
        
        Args:
            intent: The classified query intent
            
        Returns:
            Tuple of (cypher_query, parameters)
            
        Raises:
            ValueError: If query type is not supported
        """
        if intent.query_type == QueryType.UNKNOWN:
            raise ValueError("Cannot generate query for unknown intent type")
        
        # Get base template for query type
        template = self.templates.get(intent.query_type)
        if not template:
            raise ValueError(f"No template found for {intent.query_type.value}")
        
        # Build query components
        match_clause = self._build_match_clause(intent)
        where_clause = self._build_where_clause(intent)
        return_clause = self._build_return_clause(intent)
        
        # Build optional clauses
        order_clause = self._build_order_clause(intent)
        limit_clause = self._build_limit_clause(intent)
        
        # Combine clauses
        query_parts = [match_clause]
        if where_clause:
            query_parts.append(where_clause)
        query_parts.append(return_clause)
        if order_clause:
            query_parts.append(order_clause)
        if limit_clause:
            query_parts.append(limit_clause)
        
        query = "\n".join(query_parts)
        
        # Extract parameters
        parameters = self._extract_parameters(intent)
        
        return query, parameters
    
    def _build_query_templates(self) -> Dict[QueryType, str]:
        """Build Cypher query templates for each query type."""
        return {
            QueryType.VENDOR_RISK: "vendor_risk",
            QueryType.VENDOR_LIST: "vendor_list",
            QueryType.VENDOR_DETAILS: "vendor_details",
            QueryType.VENDOR_CONTROLS: "vendor_controls",
            QueryType.VENDOR_CONCENTRATION: "vendor_concentration",
            QueryType.COMPLIANCE_STATUS: "compliance_status",
            QueryType.REGULATION_DETAILS: "regulation_details",
            QueryType.COMPLIANCE_GAPS: "compliance_gaps",
            QueryType.CONTROL_EFFECTIVENESS: "control_effectiveness",
            QueryType.CONTROL_COVERAGE: "control_coverage",
            QueryType.CONTROL_BLAST_RADIUS: "control_blast_radius",
            QueryType.RISK_ASSESSMENT: "risk_assessment",
            QueryType.RISK_TRENDS: "risk_trends",
            QueryType.ISSUE_TRACKING: "issue_tracking",
            QueryType.DEPENDENCY_ANALYSIS: "dependency_analysis",
            QueryType.IMPACT_ANALYSIS: "impact_analysis",
        }
    
    def _build_entity_label_map(self) -> Dict[EntityType, str]:
        """Map entity types to Neo4j node labels."""
        return {
            EntityType.VENDOR: "Vendor",
            EntityType.CONTROL: "Control",
            EntityType.REGULATION: "Regulation",
            EntityType.RISK: "Risk",
            EntityType.ISSUE: "Issue",
            EntityType.ASSESSMENT: "Assessment",
            EntityType.BUSINESS_UNIT: "BusinessUnit",
            EntityType.TECHNOLOGY: "Technology",
        }
    
    def _build_match_clause(self, intent: QueryIntent) -> str:
        """Build MATCH clause based on query type and entities."""
        primary_entity = intent.get_primary_entity()
        if not primary_entity:
            raise ValueError("Query intent must have at least one entity")
        
        label = self.entity_labels[primary_entity]
        var = label[0].lower()  # Use first letter as variable
        
        # Build basic MATCH
        match = f"MATCH ({var}:{label})"
        
        # Add relationships if needed
        if intent.include_relationships:
            match = self._add_relationship_patterns(match, intent)
        
        return match
    
    def _add_relationship_patterns(self, match: str, intent: QueryIntent) -> str:
        """Add relationship patterns to MATCH clause."""
        # This will be expanded based on query type
        # For now, return basic match
        return match
    
    def _build_where_clause(self, intent: QueryIntent) -> str:
        """Build WHERE clause from filters."""
        if not intent.has_filters():
            return ""
        
        conditions = []
        primary_entity = intent.get_primary_entity()
        var = self.entity_labels[primary_entity][0].lower()
        
        for filter_cond in intent.filters:
            condition = self._build_filter_condition(var, filter_cond)
            conditions.append(condition)
        
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""
    
    def _build_filter_condition(
        self, 
        var: str, 
        filter_cond: FilterCondition
    ) -> str:
        """Build a single filter condition."""
        field = f"{var}.{filter_cond.field}"
        param_name = f"{filter_cond.field}"
        
        if filter_cond.operator == FilterOperator.EQUALS:
            return f"{field} = ${param_name}"
        elif filter_cond.operator == FilterOperator.NOT_EQUALS:
            return f"{field} <> ${param_name}"
        elif filter_cond.operator == FilterOperator.GREATER_THAN:
            return f"{field} > ${param_name}"
        elif filter_cond.operator == FilterOperator.LESS_THAN:
            return f"{field} < ${param_name}"
        elif filter_cond.operator == FilterOperator.GREATER_EQUAL:
            return f"{field} >= ${param_name}"
        elif filter_cond.operator == FilterOperator.LESS_EQUAL:
            return f"{field} <= ${param_name}"
        elif filter_cond.operator == FilterOperator.CONTAINS:
            return f"{field} CONTAINS ${param_name}"
        elif filter_cond.operator == FilterOperator.STARTS_WITH:
            return f"{field} STARTS WITH ${param_name}"
        elif filter_cond.operator == FilterOperator.ENDS_WITH:
            return f"{field} ENDS WITH ${param_name}"
        elif filter_cond.operator == FilterOperator.IN:
            return f"{field} IN ${param_name}"
        elif filter_cond.operator == FilterOperator.NOT_IN:
            return f"NOT {field} IN ${param_name}"
        else:
            raise ValueError(f"Unsupported operator: {filter_cond.operator}")
    
    def _build_return_clause(self, intent: QueryIntent) -> str:
        """Build RETURN clause based on aggregations and query type."""
        primary_entity = intent.get_primary_entity()
        var = self.entity_labels[primary_entity][0].lower()
        
        if intent.has_aggregations():
            return self._build_aggregation_return(var, intent)
        
        # Default return for different query types
        return f"RETURN {var}"
    
    def _build_aggregation_return(self, var: str, intent: QueryIntent) -> str:
        """Build RETURN clause with aggregations."""
        return_parts = []
        
        for agg in intent.aggregations:
            if agg.type == AggregationType.COUNT:
                part = f"count({var})"
            elif agg.type == AggregationType.SUM:
                part = f"sum({var}.{agg.field})"
            elif agg.type == AggregationType.AVG:
                part = f"avg({var}.{agg.field})"
            elif agg.type == AggregationType.MAX:
                part = f"max({var}.{agg.field})"
            elif agg.type == AggregationType.MIN:
                part = f"min({var}.{agg.field})"
            else:
                continue
            
            if agg.alias:
                part = f"{part} AS {agg.alias}"
            
            return_parts.append(part)
        
        return "RETURN " + ", ".join(return_parts)
    
    def _build_order_clause(self, intent: QueryIntent) -> str:
        """Build ORDER BY clause if sorting is specified."""
        if not intent.sort_by:
            return ""
        
        primary_entity = intent.get_primary_entity()
        var = self.entity_labels[primary_entity][0].lower()
        
        return f"ORDER BY {var}.{intent.sort_by} {intent.sort_order}"
    
    def _build_limit_clause(self, intent: QueryIntent) -> str:
        """Build LIMIT clause if limit is specified."""
        if not intent.limit:
            return ""
        
        return f"LIMIT {intent.limit}"
    
    def _extract_parameters(self, intent: QueryIntent) -> Dict[str, Any]:
        """Extract query parameters from intent."""
        parameters = {}
        
        for filter_cond in intent.filters:
            parameters[filter_cond.field] = filter_cond.value
        
        return parameters


def generate_cypher(intent: QueryIntent) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function to generate Cypher from QueryIntent.
    
    Args:
        intent: The query intent
        
    Returns:
        Tuple of (cypher_query, parameters)
    """
    generator = CypherQueryGenerator()
    return generator.generate(intent)
