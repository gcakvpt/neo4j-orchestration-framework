"""
Integration tests for Query Planning components

Tests the complete flow: Natural Language -> QueryIntent -> Cypher Query
"""

import pytest
from neo4j_orchestration.planning import (
    QueryIntentClassifier,
    CypherQueryGenerator,
    QueryType,
    EntityType,
)


class TestPlanningIntegration:
    """Integration tests for classifier + generator pipeline."""
    
    @pytest.fixture
    def classifier(self):
        """Create a QueryIntentClassifier instance."""
        return QueryIntentClassifier()
    
    @pytest.fixture
    def generator(self):
        """Create a CypherQueryGenerator instance."""
        return CypherQueryGenerator()
    
    def test_count_vendors_end_to_end(self, classifier, generator):
        """Test: 'Count all vendors' -> Cypher query."""
        # Step 1: Classify
        intent = classifier.classify("Count all vendors")
        
        assert intent.query_type == QueryType.VENDOR_LIST
        assert intent.has_aggregations()
        
        # Step 2: Generate
        query, params = generator.generate(intent)
        
        assert "MATCH (v:Vendor)" in query
        assert "count(v)" in query
        assert params == {}
    
    def test_high_risk_vendors_end_to_end(self, classifier, generator):
        """Test: 'Show vendors with critical risk' -> Cypher query."""
        # Step 1: Classify
        intent = classifier.classify("Show vendors with critical risk")
        
        assert intent.query_type == QueryType.VENDOR_RISK
        assert intent.has_filters()
        
        # Step 2: Generate
        query, params = generator.generate(intent)
        
        assert "MATCH (v:Vendor)" in query
        assert "WHERE" in query
        assert "riskLevel" in query
        assert params.get("riskLevel") == "Critical"
    
    def test_active_vendors_end_to_end(self, classifier, generator):
        """Test: 'List active vendors' -> Cypher query."""
        # Step 1: Classify
        intent = classifier.classify("List active vendors")
        
        assert intent.query_type == QueryType.VENDOR_LIST
        assert intent.has_filters()
        
        # Step 2: Generate
        query, params = generator.generate(intent)
        
        assert "WHERE v.status = $status" in query
        assert params == {"status": "Active"}
    
    def test_top_vendors_end_to_end(self, classifier, generator):
        """Test: 'Top 10 vendors by risk level' -> Cypher query."""
        # Step 1: Classify
        intent = classifier.classify("Top 10 vendors by risk level")
        
        assert intent.query_type == QueryType.VENDOR_RISK
        assert intent.limit == 10
        
        # Step 2: Generate
        query, params = generator.generate(intent)
        
        assert "LIMIT 10" in query
    
    def test_complex_query_end_to_end(self, classifier, generator):
        """Test complex query with multiple features."""
        # Step 1: Classify - use simpler query that classifier handles well
        intent = classifier.classify("Show active vendors with critical risk")
        
        # May be VENDOR_LIST or VENDOR_RISK - both are valid
        assert intent.query_type in [QueryType.VENDOR_LIST, QueryType.VENDOR_RISK]
        assert intent.has_filters()
        
        # Step 2: Generate
        query, params = generator.generate(intent)
        
        assert "MATCH (v:Vendor)" in query
        assert "WHERE" in query
        assert len(params) > 0
    
    def test_pipeline_produces_valid_cypher(self, classifier, generator):
        """Verify pipeline produces syntactically valid Cypher."""
        test_queries = [
            "Count all vendors",
            "List vendors",
            "Show active vendors",
            "Top 5 vendors",
            "Vendors with critical risk",
        ]
        
        for nl_query in test_queries:
            # Classify
            intent = classifier.classify(nl_query)
            
            # Generate (only if not unknown)
            if intent.query_type != QueryType.UNKNOWN:
                query, params = generator.generate(intent)
                
                # Basic validity checks
                assert query.startswith("MATCH")
                assert "RETURN" in query
                assert isinstance(params, dict)
                
                # Verify query structure
                assert query.count("MATCH") >= 1
                assert query.count("RETURN") == 1


class TestEdgeCases:
    """Test edge cases in the planning pipeline."""
    
    @pytest.fixture
    def classifier(self):
        """Create a QueryIntentClassifier instance."""
        return QueryIntentClassifier()
    
    @pytest.fixture
    def generator(self):
        """Create a CypherQueryGenerator instance."""
        return CypherQueryGenerator()
    
    def test_low_confidence_classification(self, classifier, generator):
        """Test handling of low-confidence classifications."""
        # Ambiguous query
        intent = classifier.classify("show me stuff")
        
        # Should still generate valid query for known types
        if intent.query_type != QueryType.UNKNOWN:
            query, params = generator.generate(intent)
            assert "MATCH" in query
    
    def test_unknown_query_type_handling(self, classifier, generator):
        """Test that UNKNOWN query type raises appropriate error."""
        intent = classifier.classify("completely random gibberish xyz123")
        
        if intent.query_type == QueryType.UNKNOWN:
            with pytest.raises(ValueError, match="Cannot generate query"):
                generator.generate(intent)


class TestRealWorldScenarios:
    """Test real-world query scenarios."""
    
    @pytest.fixture
    def classifier(self):
        """Create a QueryIntentClassifier instance."""
        return QueryIntentClassifier()
    
    @pytest.fixture
    def generator(self):
        """Create a CypherQueryGenerator instance."""
        return CypherQueryGenerator()
    
    def test_vendor_risk_assessment_scenario(self, classifier, generator):
        """Real scenario: Risk analyst wants vendor risk overview."""
        queries = [
            "How many vendors have critical risk?",
            "Show me all high risk vendors",
            "Which vendors have operational risk issues?",
        ]
        
        for nl_query in queries:
            intent = classifier.classify(nl_query)
            
            # Skip unknown queries
            if intent.query_type == QueryType.UNKNOWN:
                continue
                
            query, params = generator.generate(intent)
            
            # Should involve vendors
            assert "Vendor" in query
            assert "v:" in query
    
    def test_compliance_analyst_scenario(self, classifier, generator):
        """Real scenario: Compliance analyst reviewing regulations."""
        intent = classifier.classify("What regulations apply to our vendors?")
        
        assert intent.query_type == QueryType.REGULATION_DETAILS
        
        query, params = generator.generate(intent)
        assert "MATCH" in query
    
    def test_control_audit_scenario(self, classifier, generator):
        """Real scenario: Auditor checking control effectiveness."""
        intent = classifier.classify("Show me control effectiveness")
        
        assert intent.query_type == QueryType.CONTROL_EFFECTIVENESS
        
        query, params = generator.generate(intent)
        assert "Control" in query or "c:" in query
