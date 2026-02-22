"""
Conversation Context for Multi-Turn Query Understanding
Tracks conversation state across queries using Working Memory:
- Recent queries and their intents
- Entity references (for pronoun resolution)
- Query type history (for topic tracking)
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from neo4j_orchestration.memory.working import WorkingMemory
from neo4j_orchestration.planning.intent import QueryIntent, QueryType, EntityType
from neo4j_orchestration.execution.result import QueryResult
from neo4j_orchestration.utils.logging import get_logger
logger = get_logger(__name__)
class ConversationContext:
    """
    Manages conversation state for context-aware query understanding.
    Stores recent queries, intents, and results in Working Memory for:
    - Pronoun resolution ("them", "those vendors", "it")
    - Follow-up query understanding ("only critical ones", "in technology")
    - Entity tracking across conversation turns
    Example:
        >>> context = ConversationContext(working_memory, session_id="conv_123")
        >>> await context.add_query(
        ...     query="Show all vendors",
        ...     intent=intent,
        ...     result=result
        ... )
        >>> entities = await context.get_last_entities()
        >>> # Returns: [EntityType.VENDOR]
    """
    def __init__(self, working_memory: WorkingMemory, session_id: str, max_history: int = 5):
        """
        Initialize conversation context.
        Args:
            working_memory: WorkingMemory instance for storage
            session_id: Unique session identifier
            max_history: Maximum number of queries to track (default: 5)
        """
        self.working_memory = working_memory
        self.session_id = session_id
        self.max_history = max_history
        self._history_key = f"conversation:{session_id}:history"
        logger.info(f"ConversationContext initialized: session={session_id}, max_history={max_history}")
    async def add_query(
        self,
        query: str,
        intent: QueryIntent,
        result: Optional[QueryResult] = None
    ) -> None:
        """
        Add a query and its intent to conversation history.
        Args:
            query: Natural language query string
            intent: Classified query intent
            result: Optional query result
        """
        # Get existing history
        history_entry = await self.working_memory.get(self._history_key)
        history = history_entry.value if history_entry else []
        # Create new entry
        entry = {
            "query": query,
            "intent": self._serialize_intent(intent),
            "timestamp": datetime.now().isoformat(),
            "result_summary": self._summarize_result(result) if result else None
        }
        # Add to history (keep last max_history entries)
        history.append(entry)
        if len(history) > self.max_history:
            history = history[-self.max_history:]
        # Store back
        await self.working_memory.set(
            key=self._history_key,
            value=history,
            ttl=3600  # 1 hour TTL
        )
        logger.debug(f"Added query to context: session={self.session_id}, query='{query[:50]}...'")
    async def get_last_entities(self, n: int = 1) -> List[EntityType]:
        """
        Get entities from the last N queries.
        Args:
            n: Number of recent queries to check (default: 1)
        Returns:
            List of entity types from recent queries
        """
        history_entry = await self.working_memory.get(self._history_key)
        if not history_entry:
            return []
        history = history_entry.value[-n:]
        entities = []
        for entry in reversed(history):  # Most recent first
            intent_data = entry.get("intent", {})
            entity_strs = intent_data.get("entities", [])
            # Convert string back to EntityType
            for entity_str in entity_strs:
                try:
                    entities.append(EntityType[entity_str])
                except KeyError:
                    logger.warning(f"Unknown entity type: {entity_str}")
        return entities
    async def get_last_query_type(self) -> Optional[QueryType]:
        """
        Get the query type of the most recent query.
        Returns:
            QueryType of last query, or None if no history
        """
        history_entry = await self.working_memory.get(self._history_key)
        if not history_entry or not history_entry.value:
            return None
        last_entry = history_entry.value[-1]
        intent_data = last_entry.get("intent", {})
        query_type_str = intent_data.get("query_type")
        if query_type_str:
            try:
                return QueryType[query_type_str]
            except KeyError:
                logger.warning(f"Unknown query type: {query_type_str}")
        return None
    async def get_last_query(self) -> Optional[str]:
        """
        Get the most recent query string.
        Returns:
            Last query string, or None if no history
        """
        history_entry = await self.working_memory.get(self._history_key)
        if not history_entry or not history_entry.value:
            return None
        return history_entry.value[-1].get("query")
    async def clear(self) -> None:
        """Clear conversation history."""
        await self.working_memory.delete(self._history_key)
        logger.info(f"Cleared conversation context: session={self.session_id}")
    def _serialize_intent(self, intent: QueryIntent) -> Dict[str, Any]:
        """Convert QueryIntent to serializable dict."""
        return {
            "query_type": intent.query_type.name,
            "entities": [e.name for e in intent.entities],
            "confidence": intent.confidence,
            "has_filters": len(intent.filters) > 0,
            "has_aggregations": len(intent.aggregations) > 0
        }
    def _summarize_result(self, result: QueryResult) -> Dict[str, Any]:
        """Create summary of query result."""
        return {
            "record_count": len(result.records),
            "has_data": len(result.records) > 0
        }
