# Neo4j Orchestration Framework

[![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-56%25-green)]()
[![Python](https://img.shields.io/badge/python-3.9+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

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

## ✨ What's New: Week 4 - Pattern Learning System

The framework now includes **intelligent pattern learning** that makes queries smarter over time:

```python
# The system learns from your query patterns
"Show critical risk tier 1 vendors"  # First time
"Show critical risk tier 1 vendors"  # Second time - faster, pattern recognized
"Show critical risk tier 1 vendors"  # Third time - enhanced with learned filters

# Pattern memory tracks:
# - Query frequency and common patterns
# - Entity-specific preferences
# - Cross-session persistence
# - <50ms performance overhead
```

**Complete Pattern Learning Pipeline:**
```
User Query
    ↓ QueryPatternMemory (frequency tracking)
Pattern Recognition (common filters extracted)
    ↓ UserPreferenceMemory (entity-specific learning)
Enhanced Query Intent (learned optimizations applied)
    ↓ CypherQueryGenerator (optimized query generation)
Results + Pattern Update (continuous learning)
```

## ✨ Week 3: Natural Language Pipeline

The framework supports **natural language queries** that are automatically converted to safe, parameterized Cypher queries:

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

### Pattern Learning (Week 4)
- **QueryPatternMemory**: Learns from query execution patterns
- **UserPreferenceMemory**: Entity-specific preference tracking
- **Pattern Convergence**: Queries improve with repetition
- **Multi-entity Isolation**: Separate patterns per entity type
- **Performance**: <50ms overhead per query

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
- 83 tests (100% passing)

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
│                 Pattern Learning Layer                       │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   Query      │  │     User     │                         │
│  │   Pattern    │  │  Preference  │                         │
│  │   Memory     │  │    Memory    │                         │
│  └──────────────┘  └──────────────┘                         │
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

# Integration tests (requires Neo4j)
pytest tests/integration/
```

**Current Status:** 83/83 unit tests passing (100%)  
**Integration Tests:** 8 tests (require Neo4j instance)  
**Coverage:** 56% overall

## 📚 Documentation

- [Quick Start Guide](docs/QUICK_START.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Week 3 Completion Report](docs/WEEK3_COMPLETION_REPORT.md)
- [Week 4 Session 3 Summary](WEEK4_SESSION3_SUMMARY.md)
- [API Reference](docs/api_reference/)

## 📰 Blog Series

This framework is documented in a 5-part technical series on Substack:

1. **Why AI Needs Procedural Memory** - The foundational problem
2. **Building the Enterprise Risk Knowledge Graph** - The data layer
3. **The Orchestration Framework** - The intelligence layer architecture
4. **Coming Soon:** Pattern Learning & Confidence Evaluation
5. **Coming Soon:** Production Deployment at Scale

📖 Read the series at [gtripur.substack.com](https://gtripur.substack.com)

## 🗺️ Roadmap

### Week 4 (Complete ✅): Pattern Learning
- [x] QueryPatternMemory implementation
- [x] UserPreferenceMemory integration
- [x] Pattern convergence mechanics
- [x] Multi-entity isolation
- [x] Cross-session persistence
- [x] 8 comprehensive integration tests
- [x] <50ms performance overhead validation

### Week 5 (In Progress): QueryType Refactoring
- [ ] Generic operation types (LIST, FILTER, DETAILS, AGGREGATE)
- [ ] Entity-agnostic query handling
- [ ] Backward compatibility layer
- [ ] 150+ test migrations

### Future Enhancements (v0.4-v1.0)
- [ ] Confidence evaluation system
- [ ] Progressive context loading
- [ ] AnalysisSession tracking (procedural memory)
- [ ] Rolling checkpoints (multi-session continuity)
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

MIT License - See [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

Built with:
- [Neo4j Python Driver](https://github.com/neo4j/neo4j-python-driver)
- [Pydantic](https://github.com/pydantic/pydantic)
- [pytest](https://github.com/pytest-dev/pytest)

Inspired by:
- [Sanjay Kotagiri's work on Systems of Intelligence](https://lnkd.in/d8MiNZj4)
- Cognitive science research on human memory systems
- Enterprise risk management best practices

---

**Status:** Week 4 Complete ✅ | Pattern Learning System Integration-Ready

For questions or feedback, please open an issue on GitHub or subscribe to the [blog series](https://gtripur.substack.com).
