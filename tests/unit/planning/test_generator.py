"""
Unit tests for CypherQueryGenerator
"""

import pytest
from neo4j_orchestration.planning import (
    CypherQueryGenerator,
    generate_cypher,
    QueryIntent,
    QueryType,
    EntityType,
    FilterCondition,
    FilterOperator,
    Aggregation,
    AggregationType,
)


class TestCypherQueryGenerator:
    """Test suite for CypherQueryGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a CypherQueryGenerator instance."""
        return CypherQueryGenerator()
    
    # Basic query generation tests
    
    def test_simple_vendor_list_query(self, generator):
        """Test generating simple vendor list query."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        query, params = generator.generate(intent)
        
        assert "MATCH (v:Vendor)" in query
        assert "RETURN v" in query
        assert params == {}
    
    def test_vendor_risk_with_filter(self, generator):
        """Test vendor risk query with risk level filter."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("riskLevel", FilterOperator.EQUALS, "Critical")
            ]
        )
        
        query, params = generator.generate(intent)
        
        assert "MATCH (v:Vendor)" in query
        assert "WHERE v.riskLevel = $riskLevel" in query
        assert "RETURN v" in query
        assert params == {"riskLevel": "Critical"}
    
    def test_vendor_list_with_status_filter(self, generator):
        """Test vendor list with status filter."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("status", FilterOperator.EQUALS, "Active")
            ]
        )
        
        query, params = generator.generate(intent)
        
        assert "WHERE v.status = $status" in query
        assert params == {"status": "Active"}
    
    # Filter operator tests
    
    def test_not_equals_operator(self, generator):
        """Test NOT EQUALS filter operator."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("status", FilterOperator.NOT_EQUALS, "Inactive")
            ]
        )
        
        query, params = generator.generate(intent)
        assert "v.status <> $status" in query
    
    def test_greater_than_operator(self, generator):
        """Test GREATER THAN filter operator."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("score", FilterOperator.GREATER_THAN, 80)
            ]
        )
        
        query, params = generator.generate(intent)
        assert "v.score > $score" in query
        assert params == {"score": 80}
    
    def test_contains_operator(self, generator):
        """Test CONTAINS filter operator."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("name", FilterOperator.CONTAINS, "Tech")
            ]
        )
        
        query, params = generator.generate(intent)
        assert "v.name CONTAINS $name" in query
    
    def test_in_operator(self, generator):
        """Test IN filter operator."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("category", FilterOperator.IN, ["IT", "Finance"])
            ]
        )
        
        query, params = generator.generate(intent)
        assert "v.category IN $category" in query
        assert params == {"category": ["IT", "Finance"]}
    
    # Multiple filters test
    
    def test_multiple_filters(self, generator):
        """Test query with multiple filter conditions."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("riskLevel", FilterOperator.EQUALS, "High"),
                FilterCondition("status", FilterOperator.EQUALS, "Active"),
            ]
        )
        
        query, params = generator.generate(intent)
        
        assert "v.riskLevel = $riskLevel" in query
        assert "v.status = $status" in query
        assert "AND" in query
        assert params == {"riskLevel": "High", "status": "Active"}
    
    # Aggregation tests
    
    def test_count_aggregation(self, generator):
        """Test COUNT aggregation."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            aggregations=[
                Aggregation(AggregationType.COUNT, alias="total")
            ]
        )
        
        query, params = generator.generate(intent)
        
        assert "count(v)" in query
        assert "AS total" in query
    
    def test_sum_aggregation(self, generator):
        """Test SUM aggregation."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            aggregations=[
                Aggregation(AggregationType.SUM, field="amount", alias="totalAmount")
            ]
        )
        
        query, params = generator.generate(intent)
        
        assert "sum(v.amount)" in query
        assert "AS totalAmount" in query
    
    def test_avg_aggregation(self, generator):
        """Test AVG aggregation."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            aggregations=[
                Aggregation(AggregationType.AVG, field="score")
            ]
        )
        
        query, params = generator.generate(intent)
        assert "avg(v.score)" in query
    
    # Sorting tests
    
    def test_sort_ascending(self, generator):
        """Test sorting in ascending order."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            sort_by="name",
            sort_order="ASC"
        )
        
        query, params = generator.generate(intent)
        
        assert "ORDER BY v.name ASC" in query
    
    def test_sort_descending(self, generator):
        """Test sorting in descending order."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            sort_by="riskScore",
            sort_order="DESC"
        )
        
        query, params = generator.generate(intent)
        assert "ORDER BY v.riskScore DESC" in query
    
    # Limit tests
    
    def test_limit_clause(self, generator):
        """Test LIMIT clause."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            limit=10
        )
        
        query, params = generator.generate(intent)
        assert "LIMIT 10" in query
    
    # Complex query tests
    
    def test_complex_query_with_all_features(self, generator):
        """Test complex query with filters, sorting, and limit."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            filters=[
                FilterCondition("riskLevel", FilterOperator.EQUALS, "High"),
                FilterCondition("status", FilterOperator.EQUALS, "Active"),
            ],
            sort_by="name",
            sort_order="ASC",
            limit=5
        )
        
        query, params = generator.generate(intent)
        
        assert "MATCH (v:Vendor)" in query
        assert "WHERE v.riskLevel = $riskLevel AND v.status = $status" in query
        assert "RETURN v" in query
        assert "ORDER BY v.name ASC" in query
        assert "LIMIT 5" in query
        assert params == {"riskLevel": "High", "status": "Active"}
    
    # Entity type tests
    
    def test_control_entity_query(self, generator):
        """Test query with Control entity."""
        intent = QueryIntent(
            query_type=QueryType.CONTROL_EFFECTIVENESS,
            entities=[EntityType.CONTROL]
        )
        
        query, params = generator.generate(intent)
        assert "MATCH (c:Control)" in query
    
    def test_regulation_entity_query(self, generator):
        """Test query with Regulation entity."""
        intent = QueryIntent(
            query_type=QueryType.REGULATION_DETAILS,
            entities=[EntityType.REGULATION]
        )
        
        query, params = generator.generate(intent)
        assert "MATCH (r:Regulation)" in query
    
    # Error handling tests
    
    def test_unknown_query_type_raises_error(self, generator):
        """Test that unknown query type raises ValueError."""
        intent = QueryIntent(
            query_type=QueryType.UNKNOWN,
            entities=[EntityType.VENDOR]
        )
        
        with pytest.raises(ValueError, match="Cannot generate query for unknown"):
            generator.generate(intent)
    
    def test_no_entity_raises_error(self, generator):
        """Test that missing entity raises ValueError."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[]
        )
        
        with pytest.raises(ValueError, match="must have at least one entity"):
            generator.generate(intent)
    
    # Convenience function test
    
    def test_generate_cypher_convenience_function(self):
        """Test the generate_cypher convenience function."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        query, params = generate_cypher(intent)
        
        assert "MATCH (v:Vendor)" in query
        assert "RETURN v" in query
