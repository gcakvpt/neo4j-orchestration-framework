#!/usr/bin/env python3
"""
Demo: CypherQueryGenerator in Action

Shows the complete pipeline from natural language to Cypher queries.
"""

from neo4j_orchestration.planning import (
    QueryIntentClassifier,
    CypherQueryGenerator,
    QueryIntent,
    QueryType,
    EntityType,
    FilterCondition,
    FilterOperator,
    Aggregation,
    AggregationType,
)


def demo_basic_queries():
    """Demonstrate basic query generation."""
    print("=" * 70)
    print("DEMO 1: Basic Query Generation")
    print("=" * 70)
    
    generator = CypherQueryGenerator()
    
    # Simple vendor list
    intent = QueryIntent(
        query_type=QueryType.VENDOR_LIST,
        entities=[EntityType.VENDOR]
    )
    
    query, params = generator.generate(intent)
    print("\n1. Simple Vendor List:")
    print(f"   Query: {query}")
    print(f"   Params: {params}")


def demo_filters():
    """Demonstrate filtering."""
    print("\n" + "=" * 70)
    print("DEMO 2: Filtered Queries")
    print("=" * 70)
    
    generator = CypherQueryGenerator()
    
    # High risk vendors
    intent = QueryIntent(
        query_type=QueryType.VENDOR_RISK,
        entities=[EntityType.VENDOR],
        filters=[
            FilterCondition("riskLevel", FilterOperator.EQUALS, "Critical"),
            FilterCondition("status", FilterOperator.EQUALS, "Active"),
        ]
    )
    
    query, params = generator.generate(intent)
    print("\n2. High Risk + Active Vendors:")
    print(f"   Query:\n{query}")
    print(f"   Params: {params}")


def demo_aggregations():
    """Demonstrate aggregations."""
    print("\n" + "=" * 70)
    print("DEMO 3: Aggregation Queries")
    print("=" * 70)
    
    generator = CypherQueryGenerator()
    
    # Count vendors
    intent = QueryIntent(
        query_type=QueryType.VENDOR_LIST,
        entities=[EntityType.VENDOR],
        aggregations=[
            Aggregation(AggregationType.COUNT, alias="total")
        ]
    )
    
    query, params = generator.generate(intent)
    print("\n3. Count All Vendors:")
    print(f"   Query: {query}")
    print(f"   Params: {params}")


def demo_complex_query():
    """Demonstrate complex query with all features."""
    print("\n" + "=" * 70)
    print("DEMO 4: Complex Query (Filters + Sort + Limit)")
    print("=" * 70)
    
    generator = CypherQueryGenerator()
    
    intent = QueryIntent(
        query_type=QueryType.VENDOR_RISK,
        entities=[EntityType.VENDOR],
        filters=[
            FilterCondition("riskLevel", FilterOperator.EQUALS, "High"),
        ],
        sort_by="name",
        sort_order="ASC",
        limit=10
    )
    
    query, params = generator.generate(intent)
    print("\n4. Top 10 High Risk Vendors (Sorted):")
    print(f"   Query:\n{query}")
    print(f"   Params: {params}")


def demo_end_to_end():
    """Demonstrate end-to-end pipeline."""
    print("\n" + "=" * 70)
    print("DEMO 5: End-to-End Pipeline (Classifier → Generator)")
    print("=" * 70)
    
    classifier = QueryIntentClassifier()
    generator = CypherQueryGenerator()
    
    test_queries = [
        "Count all vendors",
        "Show active vendors with critical risk",
        "Top 5 vendors",
    ]
    
    for nl_query in test_queries:
        print(f"\n📝 Natural Language: '{nl_query}'")
        
        # Step 1: Classify
        intent = classifier.classify(nl_query)
        print(f"   ├─ Query Type: {intent.query_type.value}")
        print(f"   ├─ Confidence: {intent.confidence:.2f}")
        
        # Step 2: Generate
        if intent.query_type != QueryType.UNKNOWN:
            query, params = generator.generate(intent)
            print(f"   ├─ Cypher: {query.replace(chr(10), chr(10) + '   │         ')}")
            print(f"   └─ Params: {params}")
        else:
            print("   └─ ⚠️  Query type unknown - cannot generate")


if __name__ == "__main__":
    print("\n🚀 Neo4j Orchestration Framework - Query Generator Demo\n")
    
    demo_basic_queries()
    demo_filters()
    demo_aggregations()
    demo_complex_query()
    demo_end_to_end()
    
    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)
    print("\nNext: Run this against actual Neo4j database in Session 3!")
    print()
