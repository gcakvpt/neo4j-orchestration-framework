# Technical Debt & Future Work

## 🔴 CRITICAL - Must Complete Before Production

### 1. Week 4 - Refactor to Use Async Memory
**Status:** 🔴 Technical Debt (Quick Fix in Week 4 Session 1)  
**Created:** 2025-02-22  
**Priority:** HIGH  
**Estimated Effort:** 2-3 hours  
**Must Complete By:** End of Week 4 or Week 5 kickoff  

**Problem:**
Week 4 Session 1 used `SimpleEpisodicMemory` (sync, in-memory) as a quick fix to avoid async complexity. This means:
- ❌ Query history is **lost when application restarts** (not persisted)
- ❌ Not using the Neo4j-backed memory system built in Week 2
- ❌ Architecture inconsistency between weeks

**Impact:**
- Users lose their query history on restart
- Missing key feature (persistent memory)
- Technical debt compounds if not addressed

**Root Cause:**
In Week 4 Session 1, we discovered Week 2's `EpisodicMemory` was async/Neo4j-backed but Week 4's `QueryOrchestrator` was synchronous. Rather than refactor everything to async mid-session, we created `SimpleEpisodicMemory` as a temporary solution.

**Files Affected:**
- `src/neo4j_orchestration/memory/episodic.py` (lines 560-606)
- `src/neo4j_orchestration/orchestration/orchestrator.py`
- `src/neo4j_orchestration/orchestration/history.py`

**Required Changes:**
```python
# CURRENT (Week 4 Session 1 - Temporary):
class QueryOrchestrator:
    def query(self, nl: str) -> QueryResult:  # Sync ❌
        # ... uses SimpleEpisodicMemory (in-memory)

# TARGET (Week 4 Session 5 or Week 5):
class QueryOrchestrator:
    async def query(self, nl: str) -> QueryResult:  # Async ✅
        # ... uses EpisodicMemory (Neo4j-backed)
```

**Implementation Checklist:**
- [ ] Make `QueryOrchestrator.query()` async
- [ ] Update `QueryHistory` to use async `EpisodicMemory.save_session()`
- [ ] Refactor all orchestrator tests to use `pytest-asyncio`
- [ ] Add integration test proving Neo4j persistence works
- [ ] Remove `SimpleEpisodicMemory` and `Event` classes (lines 560-606 in episodic.py)
- [ ] Update all examples/docs to show async usage
- [ ] Test that query history persists across application restarts

**Acceptance Criteria:**
- All 33 tests still passing
- Query history persists to Neo4j
- No in-memory `SimpleEpisodicMemory` used
- Integration test proves persistence across "restarts"

**References:**
- Week 2 Memory Implementation: `src/neo4j_orchestration/memory/episodic.py` (lines 1-520)
- Architecture Mismatch Discussion: Week 4 Session 1 transcript
- Quick Fix Code: Lines 560-606 in `episodic.py`

---

## ⚠️ MEDIUM PRIORITY

### 2. Pydantic v2 Migration
**Status:** ⚠️ Warning  
**Priority:** MEDIUM  
**Estimated Effort:** 1-2 hours  

**Problem:**
```
PydanticDeprecatedSince20: Support for class-based `config` is deprecated, 
use ConfigDict instead.
```

**Location:** `src/neo4j_orchestration/core/types.py:60`

**Fix:**
```python
# Current:
class BaseConfig(BaseModel):
    class Config:
        arbitrary_types_allowed = True

# Target:
from pydantic import ConfigDict

class BaseConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
```

**Impact:** Low (just a warning, not blocking)  
**Timeline:** Week 5 or 6  

---

## 📋 PLANNED FEATURES

### Week 4 Session 2: Context-Aware Queries
**Status:** 📋 Not Started  
- Use Working Memory for recent query context
- Enable "show me more" and "refine that" queries
- Reference previous results

### Week 4 Session 3: Pattern Learning
**Status:** 📋 Not Started  
- Use Semantic Memory for common query patterns
- Auto-suggest similar queries
- Learn user preferences

### Week 4 Session 4: Result Caching
**Status:** 📋 Not Started  
- Cache frequent queries in Working Memory
- TTL-based invalidation
- Cache hit/miss metrics

---

## ✅ COMPLETED

### Week 4 Session 1: Query Orchestrator with History Tracking
**Status:** ✅ Complete (2025-02-22)  
**Tests:** 33/33 passing (27 unit + 6 integration)  
**Coverage:** 96% orchestrator, 80% history, 100% config  
**Files Created:**
- `orchestration/orchestrator.py` (48 lines, 192 original)
- `orchestration/history.py` (54 lines, 181 original) 
- `orchestration/config.py` (9 lines, 24 original)
- 4 test files (569 test lines)

**Known Issue:** Using SimpleEpisodicMemory (see item #1 above)

---

## 📝 NOTES

**Next Session:** Week 4 Session 2 (Context-aware queries)  
**Before Week 5:** Must complete async refactor (#1 above)  
**Test Command:** `python3 -m pytest tests/unit/orchestration/ tests/integration/orchestration/ -v`
