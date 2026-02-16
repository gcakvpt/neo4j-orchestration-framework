"""
Additional tests for CypherQueryGenerator coverage
"""

import pytest
from neo4j_orchestration.planning import (
    CypherQueryGenerator,
    QueryIntent,
    QueryType,
    EntityType,
    FilterCondition,
    FilterOperator,
    Aggregation,
    AggregationType,
)


class TestGeneratorCoverage:
    """Additional tests to improve coverage."""
    
    @pytest.fixture
    def generator(self):
        """Create a CypherQueryGenerator instance."""
        return CypherQueryGenerator()
    
    def test_all_filter_operators(self, generator):
        """Test all filter operators for completeness."""
        operators_tests = [
            (FilterOperator.LESS_EQUAL, "<="),
            (FilterOperator.STARTS_WITH, "STARTS WITH"),
            (FilterOperator.ENDS_WITH, "ENDS WITH"),
            (FilterOperator.NOT_IN, "NOT"),
        ]
        
        for operator, expected_text in operators_tests:
            intent = QueryIntent(
                query_type=QueryType.VENDOR_LIST,
                entities=[EntityType.VENDOR],
                filters=[
                    FilterCondition("field", operator, "value")
                ]
            )
            
            query, _ = generator.generate(intent)
            assert expected_text in query
    
    def test_all_aggregation_types(self, generator):
        """Test all aggregation types."""
        agg_tests = [
            (AggregationType.MIN, "min(v.field)"),
            (AggregationType.MAX, "max(v.field)"),
        ]
        
        for agg_type, expected in agg_tests:
            intent = QueryIntent(
                query_type=QueryType.VENDOR_LIST,
                entities=[EntityType.VENDOR],
                aggregations=[
                    Aggregation(agg_type, field="field")
                ]
            )
            
            query, _ = generator.generate(intent)
            assert expected in query
    
    def test_aggregation_without_alias(self, generator):
        """Test aggregation without alias."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            aggregations=[
                Aggregation(AggregationType.COUNT)  # No alias
            ]
        )
        
        query, _ = generator.generate(intent)
        assert "count(v)" in query
        assert "AS" not in query
    
    def test_all_entity_types(self, generator):
        """Test all entity type mappings."""
        entity_tests = [
            (EntityType.RISK, "r:Risk"),
            (EntityType.ISSUE, "i:Issue"),
            (EntityType.ASSESSMENT, "a:Assessment"),
            (EntityType.BUSINESS_UNIT, "b:BusinessUnit"),
            (EntityType.TECHNOLOGY, "t:Technology"),
        ]
        
        for entity_type, expected_pattern in entity_tests:
            intent = QueryIntent(
                query_type=QueryType.RISK_ASSESSMENT,
                entities=[entity_type]
            )
            
            query, _ = generator.generate(intent)
            assert expected_pattern in query
    
    def test_query_without_sort(self, generator):
        """Test query with no sorting specified."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            sort_by=None  # Explicitly no sorting
        )
        
        query, _ = generator.generate(intent)
        assert "ORDER BY" not in query
    
    def test_query_without_limit(self, generator):
        """Test query with no limit specified."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            limit=None  # Explicitly no limit
        )
        
        query, _ = generator.generate(intent)
        assert "LIMIT" not in query
    
    def test_query_without_filters(self, generator):
        """Test query with no filters."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[]  # No filters
        )
        
        query, _ = generator.generate(intent)
        assert "WHERE" not in query
    
    def test_multiple_aggregations(self, generator):
        """Test query with multiple aggregations."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            aggregations=[
                Aggregation(AggregationType.COUNT, alias="total"),
                Aggregation(AggregationType.AVG, field="score", alias="avgScore"),
            ]
        )
        
        query, _ = generator.generate(intent)
        assert "count(v) AS total" in query
        assert "avg(v.score) AS avgScore" in query
        assert ", " in query  # Multiple aggregations separated by comma
    
    def test_relationship_patterns_placeholder(self, generator):
        """Test include_relationships flag (placeholder functionality)."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_CONTROLS,
            entities=[EntityType.VENDOR],
            include_relationships=True
        )
        
        # Currently returns basic match - placeholder for future enhancement
        query, _ = generator.generate(intent)
        assert "MATCH (v:Vendor)" in query
    
    def test_all_query_types_have_templates(self, generator):
        """Verify all query types (except UNKNOWN) have templates."""
        for query_type in QueryType:
            if query_type == QueryType.UNKNOWN:
                continue
            
            assert query_type in generator.templates, \
                f"Missing template for {query_type.value}"
    
    def test_parameter_extraction_with_no_filters(self, generator):
        """Test parameter extraction with empty filters."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[]
        )
        
        _, params = generator.generate(intent)
        assert params == {}
    
    def test_unsupported_filter_operator_raises_error(self, generator):
        """Test that unsupported filter operator raises ValueError."""
        # Create a mock unsupported operator by using string casting trick
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
        )
        
        # Manually add a filter with invalid operator for testing
        # This would normally be caught by enum validation
        # Just verify the error handling exists
        filter_cond = FilterCondition("field", FilterOperator.EQUALS, "value")
        filter_cond.operator = "INVALID_OPERATOR"  # Force invalid
        
        with pytest.raises((ValueError, AttributeError)):
            generator._build_filter_condition("v", filter_cond)


class TestIntegrationScenarios:
    """Integration test scenarios combining classifier concepts."""
    
    @pytest.fixture
    def generator(self):
        """Create a CypherQueryGenerator instance."""
        return CypherQueryGenerator()
    
    def test_count_all_vendors_scenario(self, generator):
        """Test 'Count all vendors' scenario."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            aggregations=[Aggregation(AggregationType.COUNT, alias="total")]
        )
        
        query, params = generator.generate(intent)
        
        assert query == "MATCH (v:Vendor)\nRETURN count(v) AS total"
        assert params == {}
    
    def test_top_10_vendors_by_risk_scenario(self, generator):
        """Test 'Top 10 vendors by risk level' scenario."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            sort_by="riskScore",
            sort_order="DESC",
            limit=10
        )
        
        query, params = generator.generate(intent)
        
        assert "ORDER BY v.riskScore DESC" in query
        assert "LIMIT 10" in query
    
    def test_active_high_risk_vendors_scenario(self, generator):
        """Test 'Show active vendors with high risk' scenario."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("status", FilterOperator.EQUALS, "Active"),
                FilterCondition("riskLevel", FilterOperator.EQUALS, "High"),
            ]
        )
        
        query, params = generator.generate(intent)
        
        assert "WHERE v.status = $status AND v.riskLevel = $riskLevel" in query
        assert params == {"status": "Active", "riskLevel": "High"}
