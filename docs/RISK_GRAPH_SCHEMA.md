# Enterprise Risk Knowledge Graph Schema

## Core Entities

### Vendors
```cypher
(:Vendor {
  vendor_id: string,
  name: string,
  tier: string,  // "Tier 1", "Tier 2", "Tier 3"
  risk_score: integer,
  status: string
})
```

### Controls
```cypher
(:Control {
  control_id: string,
  name: string,
  effectiveness: float,  // 0-100
  category: string,
  status: string
})
```

### Regulations
```cypher
(:Regulation {
  regulation_id: string,
  name: string,  // "BSA/AML", "Fair Lending", "FCRA"
  authority: string,  // "OCC", "CFPB", "FDIC"
  type: string
})
```

### Risks
```cypher
(:Risk {
  risk_id: string,
  category: string,
  severity: string,  // "low", "medium", "high", "critical"
  likelihood: string,
  impact: string
})
```

## Key Relationships
```cypher
(:Vendor)-[:HAS_CONTROL]->(:Control)
(:Vendor)-[:HAS_RISK]->(:Risk)
(:Control)-[:MITIGATES]->(:Risk)
(:Regulation)-[:REQUIRES]->(:Control)
(:Vendor)-[:PROVIDES_SERVICE]->(:Service)
(:Control)-[:DEPENDS_ON]->(:Control)
```

## Common Query Patterns

### High-Risk Vendors
```cypher
MATCH (v:Vendor)-[:HAS_RISK]->(r:Risk)
WHERE r.severity IN ['high', 'critical']
RETURN v.name, v.tier, count(r) as risk_count
ORDER BY risk_count DESC
```

### Control Gaps
```cypher
MATCH (reg:Regulation)-[:REQUIRES]->(c:Control)
WHERE NOT exists((v:Vendor)-[:HAS_CONTROL]->(c))
RETURN v.name, reg.name, c.name as missing_control
```

### Control Effectiveness
```cypher
MATCH (v:Vendor)-[:HAS_CONTROL]->(c:Control)
RETURN v.tier, avg(c.effectiveness) as avg_effectiveness
ORDER BY avg_effectiveness
```
