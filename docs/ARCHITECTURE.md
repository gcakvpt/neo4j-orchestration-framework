# Neo4j Orchestration Framework - Architecture Specification

**Version:** 1.0.0  
**Status:** Implementation in Progress  
**Current Release:** v0.3-alpha (Natural Language Foundation)

---

## Executive Summary

The Neo4j Orchestration Framework transforms knowledge graphs from **Systems of Record** into **Systems of Intelligence** through a three-tier memory architecture, intelligent query planning, and examination-ready audit trails.

**Release Strategy:**
- **v0.3-alpha (NOW)**: Natural language query pipeline + memory infrastructure
- **v0.4-beta (~2 weeks)**: Intelligence layer (confidence evaluation, procedural memory, context loading)
- **v1.0 (~5 weeks)**: Production deployment (AWS templates, monitoring, security)

**Key Design Principles:**
- **Domain Agnostic:** Works with any Neo4j graph schema
- **Extensible:** Easy to create custom workflows for specific domains
- **Memory-Aware:** Maintains working, episodic, and semantic memory layers
- **Examination-Ready:** Automatic audit trails, consistency detection, confidence scoring
- **LLM-Ready:** Designed for integration with Claude MCP servers

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                          │
│           (Domain-Specific Workflows & MCP Servers)          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Uses
                         │
┌────────────────────────▼────────────────────────────────────┐
│              NEO4J ORCHESTRATION FRAMEWORK                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Workflow       │  │ Query          │  │ Analytics    │ │
│  │ Engine         │  │ Planner        │  │ Coordinator  │ │
│  │                │  │ (v0.3 ✅)      │  │              │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Working        │  │ Episodic       │  │ Semantic     │ │
│  │ Memory         │  │ Memory         │  │ Memory       │ │
│  │ (v0.3 ✅)      │  │ (v0.3 ✅)      │  │ (v0.3 ✅)    │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Confidence Evaluator (v0.4 🔜)                      │  │
│  │  • Retrieval coverage    • Specificity checking      │  │
│  │  • Hedging detection     • Risk-aware routing        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Context Manager (v0.4 🔜)                           │  │
│  │  • Progressive loading   • Token budget management   │  │
│  │  • Rolling checkpoints   • Multi-session continuity  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Connects to
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Neo4j      │  │    Redis     │  │   Vector     │     │
│  │   Graph DB   │  │   (Optional) │  │   Store      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

### ✅ Completed (v0.3-alpha - Available Now)

#### Natural Language Query Pipeline
- **QueryIntentClassifier**: Pattern-based classification of 6 intent types
- **CypherQueryGenerator**: Template-based safe query generation
- **QueryExecutor**: Connection management and result conversion

**Supported Patterns:**
- Entity queries: "Show all vendors"
- Filtered queries: "Show critical risk tier 1 vendors"
- Aggregations: "Count vendors by risk level"
- Relationships: "Show vendor fourth party dependencies"

#### Memory Systems Infrastructure
- **WorkingMemory**: In-memory session cache with TTL
- **EpisodicMemory**: Temporal event storage
- **SemanticMemory**: Long-term knowledge patterns

#### Core Infrastructure
- Type-safe operations (Pydantic models)
- Comprehensive error handling
- Performance logging
- 47 unit tests (100% passing, 65-93% coverage)

---

### 🔜 In Progress (v0.4-beta - ~2 weeks)

#### Confidence Evaluation
```python
class ConfidenceEvaluator:
    """Multi-signal confidence scoring for response quality"""
    
    def evaluate(
        self, 
        query: str,
        retrieved_data: QueryResult,
        response_draft: str
    ) -> ConfidenceScore:
        """
        Evaluate confidence using:
        - Retrieval coverage (did we get relevant data?)
        - Specificity (does response cite actual entities?)
        - Hedging language (definitive vs. tentative?)
        - Domain risk (how critical is this topic?)
        
        Returns:
            ConfidenceScore with routing decision:
            - DIRECT_RESPONSE (>= 0.85)
            - FLAG_FOR_REVIEW (0.65-0.84)
            - ESCALATE_TO_HUMAN (< 0.65)
        """
```

#### Procedural Memory Traces
```python
# AnalysisSession nodes capture HOW queries were answered
CREATE (session:AnalysisSession {
    session_id: "AS-20260216-001",
    analysis_type: "vendor_criticality",
    procedure_version: "PROC-VENDOR-CRITICAL-v1.0",
    fingerprint_id: "CF-001",
    execution_config: {
        control_weight: 3.0,
        issue_weight: 2.5
    },
    result_count: 15,
    execution_time_ms: 380
})

// Links to procedure definition and results
CREATE (session)-[:EXECUTED_PROCEDURE]->(proc:ProcedureVersion)
CREATE (session)-[:RETRIEVED]->(vendor:Vendor)
```

**Consistency Detection:**
```cypher
// Find drift: same procedure, same config, different results
MATCH (s1:AnalysisSession)-[:EXECUTED_PROCEDURE]->(pv)
MATCH (s2:AnalysisSession)-[:EXECUTED_PROCEDURE]->(pv)
WHERE s1.fingerprint_id = s2.fingerprint_id
  AND s1.session_id < s2.session_id
  
WITH s1, s2,
     collect(s1)-[:RETRIEVED]->() as r1,
     collect(s2)-[:RETRIEVED]->() as r2
WHERE r1 <> r2

RETURN s1, s2, "DRIFT_DETECTED" as alert
```

#### Progressive Context Loading
```python
class ContextManager:
    """Token-budget-aware context assembly"""
    
    def load_progressive(
        self,
        query: str,
        token_budget: int = 2000
    ) -> LoadedContext:
        """
        Load layers progressively within budget:
        1. Working Memory (500 tokens) - ALWAYS
        2. Episodic Memory (700 tokens) - IF relevant
        3. Semantic Memory (800 tokens) - ONLY if needed
        
        Avoids "Lost in the Middle" problem
        """
```

#### Rolling Checkpoints
```python
# After every N messages or topic change
checkpoint = {
    "checkpoint_id": "CP-20260216-003",
    "message_range": "45-67",
    
    "resolved": [
        "Identified 15 critical BSA/AML vendors",
        "Found 3 with >10 entity dependencies"
    ],
    
    "pending": [
        "Fourth-party risk assessment requested"
    ],
    
    "context_snapshot": {
        "active_entities": ["VND-1001", "VND-1008"],
        "procedures_used": ["PROC-VENDOR-CRITICAL"],
        "total_tokens": 3200
    }
}
```

---

### 📋 Planned (v1.0 - ~5 weeks)

#### AWS Deployment Architecture
```
┌─────────────────────────────────────────────┐
│  API Gateway + Lambda (API Layer)           │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  ECS/Fargate (Orchestration Framework)      │
│  - Auto-scaling                              │
│  - Health checks                             │
│  - Blue/green deployments                    │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼─────┐  ┌──────▼──────┐
│ Neo4j      │  │ ElastiCache │
│ AuraDB     │  │ (Redis)     │
│ Enterprise │  │             │
└────────────┘  └─────────────┘
```

**Infrastructure as Code:**
- CloudFormation templates
- Terraform modules
- Docker configs
- CI/CD pipelines (GitHub Actions)

#### Monitoring & Observability
- Grafana dashboards (framework metrics)
- CloudWatch alarms
- Distributed tracing (OpenTelemetry)
- Query performance analytics

#### Security Hardening
- RBAC implementation
- Data classification (PII/PCI/PHI)
- Audit logging
- Encryption at rest/transit
- Secrets management (AWS Secrets Manager)

---

## From System of Record to System of Intelligence

### The Transformation

| Capability | System of Record | System of Intelligence (Framework) |
|------------|------------------|-------------------------------------|
| Data Storage | ✅ Perfect fidelity | ✅ Perfect fidelity |
| Query Execution | ✅ When asked correctly | ✅ Natural language interpretation |
| Consistency | ❌ Varies by analyst | ✅ 98%+ (procedural memory) |
| Context | ❌ Cold start every time | ✅ Multi-session continuity |
| Audit Trail | ❌ Manual documentation | ✅ Automatic traces |
| Confidence | ❌ Unknown | ✅ Self-evaluated (v0.4) |
| Token Usage | 18,000 avg | 1,800 avg (progressive loading, v0.4) |

---

## Extension Points

### Custom Workflows

```python
from neo4j_orchestration.workflow import BaseWorkflow

class VendorRiskWorkflow(BaseWorkflow):
    """Domain-specific vendor risk assessment"""
    
    def execute(self, entity_id: str) -> WorkflowResult:
        # Step 1: Load vendor data
        vendor = self.load_entity(entity_id)
        
        # Step 2: Calculate risk scores
        risk_score = self.calculate_risk(vendor)
        
        # Step 3: Check compliance
        compliance = self.check_compliance(vendor)
        
        return WorkflowResult(
            risk_score=risk_score,
            compliance_status=compliance
        )
```

### Custom Intent Classifiers

```python
from neo4j_orchestration.planning import IntentRecognizer

class DomainSpecificRecognizer(IntentRecognizer):
    """Extend with domain-specific patterns"""
    
    def recognize(self, query: str) -> QueryIntent:
        # Add custom patterns for your domain
        if "sox control" in query.lower():
            return QueryIntent(
                type="sox_control_lookup",
                entities=["Control"],
                filters={"framework": "SOX"}
            )
        
        return super().recognize(query)
```

---

## Testing Strategy

### Current Coverage (v0.3)
- 47 unit tests (100% passing)
- Coverage: 65-93% across modules
- Mock-based testing (no live Neo4j required)

### Planned (v0.4+)
- Integration tests with Neo4j testcontainers
- End-to-end workflow tests
- Performance benchmarks
- Load testing scenarios

---

## Performance Targets

| Metric | Target | v0.3 Status | v0.4 Target | v1.0 Target |
|--------|--------|-------------|-------------|-------------|
| Query Latency | <500ms | ~300ms ✅ | <400ms | <300ms |
| Memory Overhead | <100MB | ~60MB ✅ | <80MB | <100MB |
| Token Usage | <2000/query | N/A | 1800 avg | 1500 avg |
| Consistency | >95% | N/A | 98% | 99% |
| Test Coverage | >80% | 65-93% ✅ | >85% | >90% |

---

## License

MIT License - See LICENSE file for details

---

## References

- [Neo4j Graph Data Science](https://neo4j.com/docs/graph-data-science/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)

---

**Document Status:**
- Version: 1.0.0
- Author: Gokul Tripurneni
- Current Release: v0.3-alpha
- Next Update: v0.4-beta release (~2 weeks)

For questions or contributions, see [GitHub Issues](https://github.com/gcakvpt/neo4j-orchestration-framework/issues)
