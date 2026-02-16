"""
Tests for Query Intent Data Structures
"""

import pytest
from neo4j_orchestration.planning.intent import (
    QueryType,
    QueryIntent,
    EntityType,
    FilterCondition,
    FilterOperator,
    Aggregation,
    AggregationType,
)


class TestFilterCondition:
    """Tests for FilterCondition class."""
    
    def test_create_filter_condition(self):
        """Test creating a filter condition."""
        filter_cond = FilterCondition(
            field="riskLevel",
            operator=FilterOperator.EQUALS,
            value="Critical"
        )
        
        assert filter_cond.field == "riskLevel"
        assert filter_cond.operator == FilterOperator.EQUALS
        assert filter_cond.value == "Critical"
        assert filter_cond.entity_type is None
    
    def test_filter_condition_with_entity(self):
        """Test filter condition with entity type."""
        filter_cond = FilterCondition(
            field="status",
            operator=FilterOperator.EQUALS,
            value="Active",
            entity_type=EntityType.VENDOR
        )
        
        assert filter_cond.entity_type == EntityType.VENDOR
    
    def test_filter_condition_string_operator(self):
        """Test filter condition with string operator."""
        filter_cond = FilterCondition(
            field="name",
            operator="=",
            value="Test"
        )
        
        assert filter_cond.operator == FilterOperator.EQUALS
    
    def test_filter_condition_empty_field(self):
        """Test filter condition with empty field."""
        with pytest.raises(ValueError, match="field cannot be empty"):
            FilterCondition(
                field="",
                operator=FilterOperator.EQUALS,
                value="test"
            )


class TestAggregation:
    """Tests for Aggregation class."""
    
    def test_create_count_aggregation(self):
        """Test creating a count aggregation."""
        agg = Aggregation(type=AggregationType.COUNT)
        
        assert agg.type == AggregationType.COUNT
        assert agg.field is None
        assert agg.alias is None
    
    def test_create_sum_aggregation(self):
        """Test creating a sum aggregation."""
        agg = Aggregation(
            type=AggregationType.SUM,
            field="riskScore",
            alias="total_risk"
        )
        
        assert agg.type == AggregationType.SUM
        assert agg.field == "riskScore"
        assert agg.alias == "total_risk"
    
    def test_aggregation_string_type(self):
        """Test aggregation with string type."""
        agg = Aggregation(type="count")
        
        assert agg.type == AggregationType.COUNT
    
    def test_aggregation_requires_field(self):
        """Test aggregation requiring field."""
        with pytest.raises(ValueError, match="requires a field"):
            Aggregation(type=AggregationType.SUM)
    
    def test_aggregation_with_group_by(self):
        """Test aggregation with group by."""
        agg = Aggregation(
            type=AggregationType.COUNT,
            group_by=["category", "status"]
        )
        
        assert agg.group_by == ["category", "status"]


class TestQueryIntent:
    """Tests for QueryIntent class."""
    
    def test_create_basic_intent(self):
        """Test creating a basic query intent."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        assert intent.query_type == QueryType.VENDOR_LIST
        assert intent.entities == [EntityType.VENDOR]
        assert intent.filters == []
        assert intent.aggregations is None
        assert intent.confidence == 1.0
    
    def test_intent_with_filters(self):
        """Test intent with filter conditions."""
        filter_cond = FilterCondition(
            field="riskLevel",
            operator=FilterOperator.EQUALS,
            value="Critical"
        )
        
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            filters=[filter_cond]
        )
        
        assert len(intent.filters) == 1
        assert intent.filters[0].field == "riskLevel"
    
    def test_intent_with_aggregations(self):
        """Test intent with aggregations."""
        agg = Aggregation(type=AggregationType.COUNT)
        
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            aggregations=[agg]
        )
        
        assert len(intent.aggregations) == 1
        assert intent.aggregations[0].type == AggregationType.COUNT
    
    def test_intent_string_types(self):
        """Test intent with string types converted to enums."""
        intent = QueryIntent(
            query_type="vendor_list",
            entities=["Vendor", "Risk"]
        )
        
        assert intent.query_type == QueryType.VENDOR_LIST
        assert intent.entities == [EntityType.VENDOR, EntityType.RISK]
    
    def test_add_filter(self):
        """Test adding a filter to intent."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        intent.add_filter("status", FilterOperator.EQUALS, "Active")
        
        assert len(intent.filters) == 1
        assert intent.filters[0].field == "status"
    
    def test_add_aggregation(self):
        """Test adding an aggregation to intent."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        intent.add_aggregation(AggregationType.COUNT, alias="vendor_count")
        
        assert len(intent.aggregations) == 1
        assert intent.aggregations[0].alias == "vendor_count"
    
    def test_get_primary_entity(self):
        """Test getting primary entity."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR, EntityType.RISK]
        )
        
        assert intent.get_primary_entity() == EntityType.VENDOR
    
    def test_get_primary_entity_empty(self):
        """Test getting primary entity with no entities."""
        intent = QueryIntent(query_type=QueryType.UNKNOWN)
        
        assert intent.get_primary_entity() is None
    
    def test_has_filters(self):
        """Test checking for filters."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        assert not intent.has_filters()
        
        intent.add_filter("status", FilterOperator.EQUALS, "Active")
        assert intent.has_filters()
    
    def test_has_aggregations(self):
        """Test checking for aggregations."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR]
        )
        
        assert not intent.has_aggregations()
        
        intent.add_aggregation(AggregationType.COUNT)
        assert intent.has_aggregations()
    
    def test_intent_with_sorting(self):
        """Test intent with sorting."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            sort_by="name",
            sort_order="DESC"
        )
        
        assert intent.sort_by == "name"
        assert intent.sort_order == "DESC"
    
    def test_intent_with_limit(self):
        """Test intent with limit."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            limit=10
        )
        
        assert intent.limit == 10
    
    def test_intent_with_relationships(self):
        """Test intent with relationship inclusion."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            include_relationships=True
        )
        
        assert intent.include_relationships is True
    
    def test_intent_invalid_confidence(self):
        """Test intent with invalid confidence."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            QueryIntent(
                query_type=QueryType.VENDOR_LIST,
                confidence=1.5
            )
    
    def test_intent_invalid_sort_order(self):
        """Test intent with invalid sort order."""
        with pytest.raises(ValueError, match="Sort order must be"):
            QueryIntent(
                query_type=QueryType.VENDOR_LIST,
                sort_order="INVALID"
            )
    
    def test_to_dict(self):
        """Test converting intent to dictionary."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_RISK,
            entities=[EntityType.VENDOR],
            confidence=0.95
        )
        intent.add_filter("riskLevel", FilterOperator.EQUALS, "Critical")
        intent.add_aggregation(AggregationType.COUNT, alias="risk_count")
        
        result = intent.to_dict()
        
        assert result["query_type"] == "vendor_risk"
        assert result["entities"] == ["Vendor"]
        assert len(result["filters"]) == 1
        assert result["filters"][0]["field"] == "riskLevel"
        assert len(result["aggregations"]) == 1
        assert result["confidence"] == 0.95
    
    def test_intent_with_metadata(self):
        """Test intent with metadata."""
        intent = QueryIntent(
            query_type=QueryType.VENDOR_LIST,
            entities=[EntityType.VENDOR],
            metadata={"original_query": "Show all vendors", "user": "test"}
        )
        
        assert intent.metadata["original_query"] == "Show all vendors"
        assert intent.metadata["user"] == "test"
