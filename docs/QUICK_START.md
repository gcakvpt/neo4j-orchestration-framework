# Quick Start Guide

## Running Tests
```bash
# All tests
python3 -m pytest tests/ -v

# Memory tests only
python3 -m pytest tests/unit/test_*memory*.py -v

# With coverage
python3 -m pytest tests/ -v --cov=src/neo4j_orchestration --cov-report=html
```

## Project Structure
```
neo4j-orchestration-framework/
├── src/neo4j_orchestration/
│   ├── core/           # Types, exceptions, base classes
│   ├── memory/         # Week 2: Memory system (COMPLETE)
│   ├── planning/       # Week 3: Query planning (TODO)
│   ├── workflow/       # Week 4+: Orchestration
│   └── utils/          # Utilities
├── tests/
│   ├── unit/           # Unit tests
│   └── fixtures/       # Test data
└── docs/               # Documentation
```

## Memory System Usage
See: project_context/MEMORY_SYSTEM_REFERENCE.md
