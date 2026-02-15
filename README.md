# Neo4j Orchestration Framework

A production-ready orchestration layer for Neo4j graph databases with integrated memory systems, intelligent query planning, and workflow automation.

## Overview

The Neo4j Orchestration Framework provides a sophisticated abstraction layer over Neo4j, designed for enterprise applications requiring:

- **Three-tier memory architecture** (Working, Episodic, Semantic)
- **Intelligent query planning** with intent recognition
- **Graph analytics coordination** using Neo4j GDS
- **Context-aware business logic** integration
- **Automated workflow execution** with retry logic

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Client Application                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Workflow Engine (Orchestrator)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Context    │  │    Query     │  │  Analytics   │      │
│  │   Manager    │  │   Planner    │  │ Coordinator  │      │
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

## Installation

### From Source
```bash
# Clone the repository
git clone https://github.com/yourusername/neo4j-orchestration-framework.git
cd neo4j-orchestration-framework

# Install with core dependencies
pip install -e .

# Install with optional dependencies
pip install -e ".[redis,embeddings]"

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start
```python
from neo4j_orchestration import OrchestrationFramework

# Initialize framework
framework = OrchestrationFramework(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password"
)

# Execute a workflow
result = framework.execute_workflow(
    workflow_name="vendor_risk_assessment",
    entity_id="VEN001"
)

print(f"Risk Score: {result.results['risk_score']}")
```

## Features

### Memory Systems

- **Working Memory**: Fast cache for active session data (TTL: minutes-hours)
- **Episodic Memory**: Session-based analysis history (immutable)
- **Semantic Memory**: Business rules and learned patterns (versioned)

### Query Planning

Automatically classifies query intent and generates optimal execution plans:

- Entity lookups
- Relationship traversals
- Pattern matching
- Aggregations
- Analytics workflows

### Analytics Integration

Seamless integration with Neo4j Graph Data Science:

- PageRank for importance scoring
- Betweenness Centrality for bottleneck detection
- Community Detection (Louvain, WCC)
- Path algorithms
- Node similarity

### Workflow Automation

Define complex multi-step workflows with:

- Automatic retry logic
- Step dependencies
- Context preservation
- Error handling

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/neo4j_orchestration --cov-report=html

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m e2e
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Status

**Current Version**: 0.1.0 (Week 1 - Foundation)

### Completed
- ✅ Core type definitions
- ✅ Exception hierarchy
- ✅ Utility modules (logging, validation, Cypher)
- ✅ Unit tests
- ✅ Project structure

### In Progress
- 🚧 Memory systems implementation
- 🚧 Query planning engine
- 🚧 Analytics coordinator

### Planned
- 📋 Context manager
- 📋 Workflow engine
- 📋 Integration tests
- 📋 Documentation

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Author

Gokul Tripurneni (gokultripurneni@gmail.com)
xE

