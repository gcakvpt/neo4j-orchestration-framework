#!/usr/bin/env python3
"""
Week 3 Complete Pipeline Demo
==============================

Demonstrates the full Natural Language → Neo4j Results pipeline:
1. QueryIntentClassifier: NL → Intent
2. CypherQueryGenerator: Intent → Cypher + Parameters  
3. QueryExecutor: Execute → Results

Usage:
    python demos/week3_complete_pipeline.py
"""

from unittest.mock import MagicMock, patch
from neo4j_orchestration.planning import QueryIntentClassifier, CypherQueryGenerator
from neo4j_orchestration.execution import QueryExecutor, Neo4jConfig


def setup_mock_executor():
    """Setup executor with mocked Neo4j for demo."""
    config = Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )
    
    with patch('neo4j_orchestration.execution.executor.GraphDatabase') as mock_gdb:
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        mock_gdb.driver.return_value = mock_driver
        
        executor = QueryExecutor(config)
        executor._mock_driver = mock_driver
        return executor


def demo_vendor_count():
    """Demo: Count all vendors."""
    print("\n" + "="*70)
    print("DEMO 1: Count Query")
    print("="*70)
    
    # Initialize pipeline
    classifier = QueryIntentClassifier()
    generator = CypherQueryGenerator()
    executor = setup_mock_executor()
    
    # Mock result
    session = MagicMock()
    record = MagicMock()
    record.keys.return_value = ['count']
    record.__getitem__ = lambda self, k: 42
    result = MagicMock()
    result.__iter__.return_value = [record]
    summary = MagicMock()
    summary.counters = None
    result.consume.return_value = summary
    session.run.return_value = result
    executor._mock_driver.session.return_value.__enter__.return_value = session
    
    # Execute pipeline
    nl_query = "How many vendors do we have?"
    print(f"\n📝 Input: '{nl_query}'")
    
    intent = classifier.classify(nl_query)
    print(f"🎯 Intent: {intent.query_type.value}")
    
    query, params = generator.generate(intent)
    print(f"⚙️  Cypher Generated:\n    {query[:60]}...")
    
    result = executor.execute(query, params)
    print(f"✅ Result: {result.records[0]['count']} vendors")
    
    executor.close()


def demo_filtered_query():
    """Demo: Filter vendors by risk level."""
    print("\n" + "="*70)
    print("DEMO 2: Filtered Query")
    print("="*70)
    
    classifier = QueryIntentClassifier()
    generator = CypherQueryGenerator()
    executor = setup_mock_executor()
    
    # Mock vendor results
    session = MagicMock()
    records = []
    for i in range(3):
        node = MagicMock()
        node.id = i
        node.labels = ['Vendor']
        node.items.return_value = [
            ('name', f'Vendor{i}'),
            ('riskLevel', 'Critical')
        ]
        rec = MagicMock()
        rec.keys.return_value = ['v']
        rec.__getitem__ = lambda self, k, n=node: n
        records.append(rec)
    
    result = MagicMock()
    result.__iter__.return_value = records
    summary = MagicMock()
    summary.counters = None
    result.consume.return_value = summary
    session.run.return_value = result
    executor._mock_driver.session.return_value.__enter__.return_value = session
    
    # Execute
    nl_query = "Show critical risk vendors"
    print(f"\n📝 Input: '{nl_query}'")
    
    intent = classifier.classify(nl_query)
    print(f"🎯 Filters: riskLevel = {intent.filters[0].value}")
    
    query, params = generator.generate(intent)
    print(f"⚙️  Parameters: {params}")
    
    result = executor.execute(query, params)
    print(f"✅ Found: {len(result)} vendors")
    
    executor.close()


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("Neo4j Orchestration Framework - Week 3 Pipeline Demo")
    print("Natural Language → Intent → Cypher → Results")
    print("="*70)
    
    demo_vendor_count()
    demo_filtered_query()
    
    print("\n" + "="*70)
    print("🎉 Demo Complete!")
    print("="*70)
    print("\n💡 Key Features:")
    print("   • Natural language understanding")
    print("   • Automatic Cypher generation")
    print("   • Parameter binding")
    print("   • Type-safe results")
    print()


if __name__ == "__main__":
    main()
