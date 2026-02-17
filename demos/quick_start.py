#!/usr/bin/env python3
"""5-Minute Quick Start Demo"""

from unittest.mock import MagicMock, patch
from neo4j_orchestration.planning import QueryIntentClassifier, CypherQueryGenerator
from neo4j_orchestration.execution import QueryExecutor, Neo4jConfig

# Setup (with mock for demo)
config = Neo4jConfig(uri="bolt://localhost:7687", username="neo4j", password="pass")

with patch('neo4j_orchestration.execution.executor.GraphDatabase'):
    classifier = QueryIntentClassifier()
    generator = CypherQueryGenerator()
    executor = QueryExecutor(config)
    executor._mock_driver = MagicMock()
    executor._mock_driver.verify_connectivity.return_value = None
    
    # Pipeline
    intent = classifier.classify("Count all vendors")
    query, params = generator.generate(intent)
    
    print("Input:  'Count all vendors'")
    print(f"Output: {query[:50]}...")
    print("✅ Pipeline working!")
