# Neo4j Orchestration Framework

[![Tests](https://img.shields.io/badge/tests-47%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-65--93%25-green)]()
[![Python](https://img.shields.io/badge/python-3.9+-blue)]()

A production-ready orchestration layer for Neo4j graph databases with **natural language query support**, integrated memory systems, and intelligent query planning.

## 🚀 Quick Start (1 minute)
```python
from neo4j_orchestration.planning import QueryIntentClassifier, CypherQueryGenerator
from neo4j_orchestration.execution import QueryExecutor, Neo4jConfig

# Setup
config = Neo4jConfig(uri="bolt://localhost:7687", username="neo4j", password="password")
classifier = QueryIntentClassifier()
generator = CypherQueryGenerator()
executor = QueryExecutor(config)

# Natural language to results in 3 lines
intent = classifier.classify("Show critical risk vendors")
query, params = generator.generate(intent)
results = executor.execute(query, params)

print(f"Found {len(results)} vendors")
```

**See it in action:** `python demos/quick_start.py`

## ✨ What's New: Week 3 - Natural Language Pipeline

The framework now supports **natural language queries** that are automatically converted to safe, parameterized Cypher queries:
```python
# Instead of writing Cypher...
"MATCH (v:Vendor) WHERE v.riskLevel = 'Critical' AND v.tier = '1' RETURN v"

# Just say what you want:
"Show critical risk tier 1 vendors"
```

**Complete Pipeline:**
```
Natural Language
    ↓ QueryIntentClassifier (pattern-based NL understanding)
QueryIntent (structured representation)
    ↓ CypherQueryGenerator (template-based generation)
Cypher Query + Parameters (safe, parameterized)
    ↓ QueryExecutor (connection management, execution)
Python Results (List[Dict])
```

## 📦 Features

### Natural Language Querying (Week 3)
- **QueryIntentClassifier**: Convert natural language to structured intents
- **CypherQueryGenerator**: Generate safe, parameterized Cypher queries
- **QueryExecutor**: Execute queries and convert results to Python objects

### Memory Systems (Week 2)
- **Working Memory**: Short-term context with TTL expiration
- **Episodic Memory**: Temporal event storage and retrieval
- **Semantic Memory**: Long-term knowledge and pattern storage

### Core Infrastructure (Week 1)
- Type-safe operations with Pydantic
- Comprehensive error handling
- Performance logging
- 47 tests (100% passing)

## 🎯 Supported Query Types

### Entity Queries
```python
"Show all vendors"
"List tier 1 vendors"
"Find critical risk controls"
```

### Filtered Queries
```python
"Show critical risk vendors"
"Find active tier 1 vendors"
"List vendors in tier 1 or tier 2"
```

### Aggregations
```python
"Count all vendors"
"How many critical controls?"
"Average risk score by tier"
```

### Relationships
```python
"Show vendor relationships"
"Find fourth party vendors"
"List vendor control implementations"
```

## 📊 Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Client Application                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Natural Language Pipeline                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ NL Classifier│→ │    Query     │→ │   Query      │      │
│  │              │  │  Generator   │  │  Executor    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   Memory Systems                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Working    │  │   Episodic   │  │   Semantic   │      │
│  │    Memory    │  │    Memory    │  │    Memory    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Neo4j Database                            │
│              (Graph + GDS Algorithms)                        │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Installation

### From Source
```bash
git clone https://github.com/gcakvpt/neo4j-orchestration-framework.git
cd neo4j-orchestration-framework
pip install -e .
```

### Requirements
- Python 3.9+
- Neo4j 5.0+ (optional for demos - they use mocks)

## 🎮 Demos
```bash
# Quick start (1 minute)
python demos/quick_start.py

# Complete pipeline demo (5 minutes)
python demos/week3_complete_pipeline.py
```

See [demos/README.md](demos/README.md) for more examples.

## 🧪 Testing
```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific module
pytest tests/unit/planning/
```

**Current Status:** 47/47 tests passing (100%)

## 📚 Documentation

- [Quick Start Guide](docs/QUICK_START.md)
- [Week 3 Completion Report](docs/WEEK3_COMPLETION_REPORT.md)
- [Architecture Overview](docs/)
- [API Reference](docs/api_reference/)

## 🗺️ Roadmap

### Week 4 (Upcoming): Memory Integration
- [ ] Query history tracking
- [ ] Pattern learning from user queries
- [ ] Context-aware query refinement
- [ ] Memory-augmented generation

### Future Enhancements
- [ ] Query result caching
- [ ] Batch query execution
- [ ] Advanced relationship patterns
- [ ] Custom aggregation functions
- [ ] GraphQL interface

## 🤝 Contributing

Contributions welcome! This is an active development project.

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Built with:
- [Neo4j Python Driver](https://github.com/neo4j/neo4j-python-driver)
- [Pydantic](https://github.com/pydantic/pydantic)
- [pytest](https://github.com/pytest-dev/pytest)

---

**Status:** Week 3 Complete ✅ | Natural Language Pipeline Production-Ready

For questions or feedback, please open an issue on GitHub.
