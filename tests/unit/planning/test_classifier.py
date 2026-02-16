"""
Tests for Query Intent Classifier
"""

import pytest
from neo4j_orchestration.planning.classifier import QueryIntentClassifier
from neo4j_orchestration.planning.intent import (
    QueryType,
    EntityType,
    FilterOperator,
    AggregationType,
)


class TestQueryIntentClassifier:
    """Tests for QueryIntentClassifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create a classifier instance."""
        return QueryIntentClassifier()
    
    # Vendor query tests
    
    def test_classify_vendor_risk_query(self, classifier):
        """Test classifying vendor risk query."""
        query = "Show me all vendors with critical risks"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.VENDOR_RISK
        assert EntityType.VENDOR in intent.entities
        assert intent.confidence > 0.9
    
    def test_classify_vendor_list_query(self, classifier):
        """Test classifying vendor list query."""
        query = "List all vendors"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.VENDOR_LIST
        assert EntityType.VENDOR in intent.entities
    
    def test_classify_vendor_details_query(self, classifier):
        """Test classifying vendor details query."""
        query = "Get details for vendor XYZ"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.VENDOR_DETAILS
        assert EntityType.VENDOR in intent.entities
    
    def test_classify_vendor_controls_query(self, classifier):
        """Test classifying vendor controls query."""
        query = "Show vendor controls"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.VENDOR_CONTROLS
        assert EntityType.VENDOR in intent.entities
    
    # Compliance query tests
    
    def test_classify_compliance_status_query(self, classifier):
        """Test classifying compliance status query."""
        query = "What is the compliance status?"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.COMPLIANCE_STATUS
    
    def test_classify_compliance_gaps_query(self, classifier):
        """Test classifying compliance gaps query."""
        query = "Show me compliance gaps"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.COMPLIANCE_GAPS
    
    def test_classify_regulation_query(self, classifier):
        """Test classifying regulation details query."""
        query = "Get BSA regulation details"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.REGULATION_DETAILS
        assert EntityType.REGULATION in intent.entities
    
    # Control query tests
    
    def test_classify_control_effectiveness_query(self, classifier):
        """Test classifying control effectiveness query."""
        query = "Show control effectiveness"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.CONTROL_EFFECTIVENESS
        assert EntityType.CONTROL in intent.entities
    
    def test_classify_control_coverage_query(self, classifier):
        """Test classifying control coverage query."""
        query = "Analyze control coverage"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.CONTROL_COVERAGE
    
    def test_classify_blast_radius_query(self, classifier):
        """Test classifying blast radius query."""
        query = "What is the blast radius for this control?"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.CONTROL_BLAST_RADIUS
    
    # Filter extraction tests
    
    def test_extract_critical_risk_filter(self, classifier):
        """Test extracting critical risk filter."""
        query = "Show vendors with critical risk"
        intent = classifier.classify(query)
        
        assert len(intent.filters) > 0
        risk_filter = next(
            (f for f in intent.filters if f.field == "riskLevel"),
            None
        )
        assert risk_filter is not None
        assert risk_filter.value == "Critical"
    
    def test_extract_high_risk_filter(self, classifier):
        """Test extracting high risk filter."""
        query = "List vendors with high risk"
        intent = classifier.classify(query)
        
        risk_filter = next(
            (f for f in intent.filters if f.field == "riskLevel"),
            None
        )
        assert risk_filter is not None
        assert risk_filter.value == "High"
    
    def test_extract_active_status_filter(self, classifier):
        """Test extracting active status filter."""
        query = "Show active vendors"
        intent = classifier.classify(query)
        
        status_filter = next(
            (f for f in intent.filters if f.field == "status"),
            None
        )
        assert status_filter is not None
        assert status_filter.value == "Active"
    
    def test_extract_compliant_filter(self, classifier):
        """Test extracting compliant filter."""
        query = "Show compliant vendors"
        intent = classifier.classify(query)
        
        compliant_filter = next(
            (f for f in intent.filters if f.field == "compliant"),
            None
        )
        assert compliant_filter is not None
        assert compliant_filter.value is True
    
    def test_extract_non_compliant_filter(self, classifier):
        """Test extracting non-compliant filter."""
        query = "Find non-compliant controls"
        intent = classifier.classify(query)
        
        compliant_filter = next(
            (f for f in intent.filters if f.field == "compliant"),
            None
        )
        assert compliant_filter is not None
        assert compliant_filter.value is False
    
    # Aggregation extraction tests
    
    def test_extract_count_aggregation(self, classifier):
        """Test extracting count aggregation."""
        query = "Count all vendors"
        intent = classifier.classify(query)
        
        assert intent.aggregations is not None
        assert len(intent.aggregations) > 0
        assert intent.aggregations[0].type == AggregationType.COUNT
    
    def test_extract_total_aggregation(self, classifier):
        """Test extracting total aggregation."""
        query = "What is the total number of vendors?"
        intent = classifier.classify(query)
        
        assert intent.aggregations is not None
        count_agg = next(
            (a for a in intent.aggregations if a.type == AggregationType.COUNT),
            None
        )
        assert count_agg is not None
    
    def test_extract_average_aggregation(self, classifier):
        """Test extracting average aggregation."""
        query = "What is the average risk score?"
        intent = classifier.classify(query)
        
        assert intent.aggregations is not None
        avg_agg = next(
            (a for a in intent.aggregations if a.type == AggregationType.AVG),
            None
        )
        assert avg_agg is not None
    
    def test_extract_maximum_aggregation(self, classifier):
        """Test extracting maximum aggregation."""
        query = "Show the highest risk vendors"
        intent = classifier.classify(query)
        
        assert intent.aggregations is not None
        max_agg = next(
            (a for a in intent.aggregations if a.type == AggregationType.MAX),
            None
        )
        assert max_agg is not None
    
    # Sorting and limit tests
    
    def test_extract_sorting(self, classifier):
        """Test extracting sorting information."""
        query = "List vendors sorted by name"
        intent = classifier.classify(query)
        
        assert intent.sort_by == "name"
        assert intent.sort_order == "ASC"
    
    def test_extract_descending_sort(self, classifier):
        """Test extracting descending sort."""
        query = "Show vendors ordered by risk descending"
        intent = classifier.classify(query)
        
        assert intent.sort_by == "risk"
        assert intent.sort_order == "DESC"
    
    def test_extract_limit(self, classifier):
        """Test extracting result limit."""
        query = "Show top 10 vendors"
        intent = classifier.classify(query)
        
        assert intent.limit == 10
    
    def test_extract_first_limit(self, classifier):
        """Test extracting limit with 'first'."""
        query = "Display first 5 vendors"
        intent = classifier.classify(query)
        
        assert intent.limit == 5
    
    # Relationship tests
    
    def test_detect_relationship_inclusion(self, classifier):
        """Test detecting relationship inclusion."""
        query = "Show vendor relationships"
        intent = classifier.classify(query)
        
        assert intent.include_relationships is True
    
    def test_detect_dependency_relationships(self, classifier):
        """Test detecting dependency relationships."""
        query = "Analyze vendor dependencies"
        intent = classifier.classify(query)
        
        assert intent.include_relationships is True
    
    # Multiple entity tests
    
    def test_extract_multiple_entities(self, classifier):
        """Test extracting multiple entities."""
        query = "Show vendors with controls and risks"
        intent = classifier.classify(query)
        
        assert EntityType.VENDOR in intent.entities
        assert EntityType.CONTROL in intent.entities
        assert EntityType.RISK in intent.entities
    
    def test_vendor_and_regulation_entities(self, classifier):
        """Test vendor and regulation entities."""
        query = "List vendors subject to BSA regulations"
        intent = classifier.classify(query)
        
        assert EntityType.VENDOR in intent.entities
        assert EntityType.REGULATION in intent.entities
    
    # Complex query tests
    
    def test_complex_query_with_filters_and_aggregations(self, classifier):
        """Test complex query with filters and aggregations."""
        query = "Count active vendors with critical risk"
        intent = classifier.classify(query)
        
        assert EntityType.VENDOR in intent.entities
        assert len(intent.filters) >= 2
        assert intent.aggregations is not None
    
    def test_complex_query_with_sorting_and_limit(self, classifier):
        """Test complex query with sorting and limit."""
        query = "Show top 5 vendors with high risk sorted by name"
        intent = classifier.classify(query)
        
        assert intent.limit == 5
        assert intent.sort_by == "name"
        assert len(intent.filters) > 0
    
    # Unknown query tests
    
    def test_unknown_query_type(self, classifier):
        """Test query with unknown type."""
        query = "Hello, how are you?"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.UNKNOWN
        assert intent.confidence <= 0.5
    
    def test_ambiguous_query(self, classifier):
        """Test ambiguous query."""
        query = "Show me the data"
        intent = classifier.classify(query)
        
        # Should return something, even if unknown
        assert intent is not None
        assert intent.metadata["original_query"] == "Show me the data"
    
    # Edge cases
    
    def test_empty_query(self, classifier):
        """Test empty query."""
        query = ""
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.UNKNOWN
    
    def test_whitespace_query(self, classifier):
        """Test whitespace-only query."""
        query = "   "
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.UNKNOWN
    
    def test_case_insensitive_matching(self, classifier):
        """Test case-insensitive query matching."""
        query = "SHOW ME ALL VENDORS WITH CRITICAL RISKS"
        intent = classifier.classify(query)
        
        assert intent.query_type == QueryType.VENDOR_RISK
        assert EntityType.VENDOR in intent.entities
    
    def test_metadata_preservation(self, classifier):
        """Test that original query is preserved in metadata."""
        query = "Show vendors with critical risk"
        intent = classifier.classify(query)
        
        assert intent.metadata["original_query"] == query
    
    # Specific risk level tests
    
    def test_medium_risk_filter(self, classifier):
        """Test medium risk level filter."""
        query = "Find vendors with medium risk"
        intent = classifier.classify(query)
        
        risk_filter = next(
            (f for f in intent.filters if f.field == "riskLevel"),
            None
        )
        assert risk_filter is not None
        assert risk_filter.value == "Medium"
    
    def test_low_risk_filter(self, classifier):
        """Test low risk level filter."""
        query = "Show vendors with low risk"
        intent = classifier.classify(query)
        
        risk_filter = next(
            (f for f in intent.filters if f.field == "riskLevel"),
            None
        )
        assert risk_filter is not None
        assert risk_filter.value == "Low"
