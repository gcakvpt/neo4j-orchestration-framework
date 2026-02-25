# QueryType Refactoring - Impact Analysis

## 🎯 Problem Statement

Current QueryType enum is **domain-specific** and **not scalable**:
- Hard-coded for specific use cases (VENDOR_RISK, CONTROL_EFFECTIVENESS, etc.)
- Pattern learning only works for predefined query types
- New entities require code changes in multiple places
- Not generic for arbitrary knowledge graphs

## 📊 Impact Scope

### Source Files Impacted (8 files)
1. **src/neo4j_orchestration/planning/intent.py** - QueryType enum definition
2. **src/neo4j_orchestration/planning/classifier.py** - Maps NL to QueryType (15 usages)
3. **src/neo4j_orchestration/planning/generator.py** - Template mapping (17 usages)
4. **src/neo4j_orchestration/memory/query_patterns.py** - Pattern storage by QueryType
5. **src/neo4j_orchestration/orchestration/preferences.py** - Tracks patterns by QueryType
6. **src/neo4j_orchestration/orchestration/context.py** - Context-aware classification
7. **src/neo4j_orchestration/orchestration/context_classifier.py** - Uses QueryType
8. **src/neo4j_orchestration/orchestration/pattern_classifier.py** - Pattern enhancement

### Test Files Impacted (14 files)
- Unit tests: 10 files
- Integration tests: 4 files
- Total test updates needed: ~150+ test cases

## 🏗️ Current Architecture

### How It Works Now
```python
# Classifier returns domain-specific QueryType
intent = QueryIntent(
    query_type=QueryType.VENDOR_RISK,  # Hard-coded enum
    entities=[EntityType.VENDOR],
    filters=[...]
)

# Generator has template per QueryType
templates = {
    QueryType.VENDOR_RISK: "vendor_risk",
    QueryType.VENDOR_LIST: "vendor_list",
    QueryType.CONTROL_EFFECTIVENESS: "control_effectiveness",
    # ... 16 hard-coded mappings
}
```

### Problems
1. ❌ New entity type → Add N new QueryType enums (one per operation)
2. ❌ Pattern learning tied to specific QueryTypes
3. ❌ Generator has giant switch statement
4. ❌ Not reusable across different knowledge graphs

## 🎨 Proposed Architecture

### Generic QueryType Approach
```python
class QueryType(Enum):
    """Generic query operation types."""
    LIST = "list"              # Get all entities
    FILTER = "filter"          # Filter entities
    DETAILS = "details"        # Get entity details
    RELATIONSHIP = "relationship"  # Traverse relationships
    AGGREGATE = "aggregate"    # Aggregate data
    COMPARE = "compare"        # Compare entities
    ANALYZE = "analyze"        # Complex analysis
    UNKNOWN = "unknown"

# Usage
intent = QueryIntent(
    query_type=QueryType.LIST,         # Generic operation
    entities=[EntityType.VENDOR],      # What to list
    filters=[...]                       # How to filter
)
```

### Benefits
1. ✅ Works with ANY entity type in the graph
2. ✅ Pattern learning is entity-agnostic
3. ✅ Generator uses composable templates
4. ✅ Scales to new entities without code changes

## 📋 Refactoring Tasks

### Phase 1: Core Enum Refactoring
- [ ] Update QueryType enum to generic operations
- [ ] Add backward compatibility mapping (old → new)
- [ ] Update QueryIntent usage

### Phase 2: Classifier Refactoring
- [ ] Update keyword mapping to use generic types
- [ ] Separate entity detection from operation detection
- [ ] Update classifier tests (14 tests)

### Phase 3: Generator Refactoring
- [ ] Replace template mapping with composable builder
- [ ] Build queries from: operation + entity + filters
- [ ] Update generator tests (20 tests)

### Phase 4: Memory/Pattern System
- [ ] Update QueryPatternMemory to use generic types
- [ ] Update UserPreferenceTracker
- [ ] Update all pattern learning tests (13 tests)

### Phase 5: Context System
- [ ] Update ContextAwareClassifier
- [ ] Update ConversationContext
- [ ] Update context tests (10 tests)

### Phase 6: Integration Testing
- [ ] Update all integration tests (4 files, 11 tests)
- [ ] End-to-end testing
- [ ] Performance validation

## ⏱️ Effort Estimate

### Time Breakdown
- Phase 1 (Core): 30 minutes
- Phase 2 (Classifier): 45 minutes
- Phase 3 (Generator): 1 hour
- Phase 4 (Memory): 30 minutes
- Phase 5 (Context): 30 minutes
- Phase 6 (Integration): 45 minutes

**Total: ~4 hours of focused work**

## 🚨 Risks & Mitigation

### Risks
1. **Breaking Changes**: All existing code uses old QueryTypes
2. **Test Failures**: 150+ tests need updates
3. **Complex Generator Logic**: Template builder needs careful design

### Mitigation
1. **Backward Compatibility Layer**: Map old → new during transition
2. **Incremental Testing**: Update tests phase by phase
3. **Feature Flag**: Keep old path working until new path is complete

## �� Decision Point

### Option A: Full Refactor Now (Recommended)
- Do all 6 phases in one session (~4 hours)
- Clean, generic architecture
- Better for long-term maintainability
- **Best for production system**

### Option B: Quick Fix for Step 5
- Use existing VENDOR_LIST in tests
- Document limitation
- Plan refactor for Week 5
- **Gets Step 5 done quickly but leaves technical debt**

### Option C: Hybrid Approach
- Do Phase 1-3 now (core + classifier + generator) - 2 hours
- Keep pattern learning with old types for now
- Full migration in Week 5

## 💡 Recommendation

Given that:
1. You want a proper, scalable solution
2. Pattern learning is core to Week 4 goals
3. This affects the entire query pipeline

I recommend **Option A: Full Refactor Now**

This is the right time because:
- ✅ We're still in development (not production)
- ✅ Step 5 is integration testing (perfect time to fix architecture)
- ✅ Better to fix now than carry technical debt
- ✅ Makes pattern learning truly useful

**Estimated completion**: 4-5 hours total
**When to do it**: Either continue now OR schedule for next session

---

**What would you like to do?**
