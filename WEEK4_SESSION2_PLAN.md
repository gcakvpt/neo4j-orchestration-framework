# Week 4 Session 2 - Context-Aware Queries

## Architecture Decision

**Hybrid Sync/Async Approach:**
- QueryOrchestrator: **SYNC** (CPU-bound logic)
- Memory operations: **ASYNC** (I/O-bound storage)
- Use async wrappers for memory calls

**Why This Works:**
- Classifier/Generator are pure functions (no I/O)
- Only memory storage needs async
- Clean separation of concerns
- Easy to test

## Components to Build

### 1. ConversationContext (orchestration/context.py)
```python
class ConversationContext:
    def __init__(self, working_memory: WorkingMemory, session_id: str)
    
    async def add_query(self, query: str, intent: QueryIntent, result: QueryResult)
    async def get_last_entities(self) -> List[str]
    async def get_last_query_type(self) -> Optional[QueryType]
    async def clear(self)
```

### 2. ContextAwareClassifier (orchestration/context_classifier.py)
```python
class ContextAwareClassifier:
    def __init__(self, base_classifier: QueryIntentClassifier)
    
    def classify_with_context(
        self, 
        query: str, 
        context: ConversationContext
    ) -> QueryIntent:
        # Sync method that resolves pronouns
        # Uses context.get_last_entities() via asyncio.run()
```

### 3. Update QueryOrchestrator
- Add optional context parameter
- Use context-aware classification when context provided
- Store results in context

## Implementation Strategy

1. Build ConversationContext (async methods)
2. Build ContextAwareClassifier (sync wrapper)
3. Update QueryOrchestrator (add context support)
4. Comprehensive tests

## Success Criteria

- Resolve pronouns: "Show vendors" → "Which ones have critical risks?"
- Track entities across queries
- 40+ tests passing
- Clean async/sync separation

## Next Session

Week 4 Session 3: Semantic Memory for pattern learning
