# Integration Tests for Pattern Learning

## Requirements

These tests require a Neo4j instance (Aura, Desktop, or Docker):

### Using Neo4j Aura
Set environment variables:
```bash
export NEO4J_URI="neo4j+s://xxxxx.databases.neo4j.io"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
```

### Using Local Neo4j
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"
```

## Running Tests
```bash
pytest tests/integration/orchestration/test_pattern_learning_integration.py -v
```

## Test Coverage

✅ test_orchestrator_backward_compatibility (no Neo4j required)
⚠️ Other tests require Neo4j connection

## Note

Integration tests validate end-to-end functionality with real Neo4j.
Unit tests (83 passing) verify core logic without external dependencies.
