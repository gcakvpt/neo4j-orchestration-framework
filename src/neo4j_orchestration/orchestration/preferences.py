"""
User preference tracking for query optimization.
"""
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

from ..memory.query_patterns import QueryPatternMemory
from ..planning.intent import QueryIntent, QueryType, EntityType


class UserPreferenceTracker:
    """
    Tracks user preferences to optimize query suggestions.
    
    Learns from:
    - Entity types frequently queried
    - Common filter combinations
    - Successful query patterns
    """
    
    def __init__(
        self,
        pattern_memory: QueryPatternMemory,
        session_id: str
    ):
        """
        Initialize preference tracker.
        
        Args:
            pattern_memory: QueryPatternMemory instance for pattern storage
            session_id: Unique session identifier
        """
        self.pattern_memory = pattern_memory
        self.session_id = session_id
        
        # Track entity usage frequency
        self._entity_usage: Counter = Counter()
        
        # Track filter usage by query type
        self._filter_usage: Dict[QueryType, List[Dict[str, Any]]] = defaultdict(list)
    
    async def record_query_preference(
        self,
        intent: QueryIntent,
        result: Any,
        user_satisfied: bool = True
    ) -> None:
        """
        Record a query preference for learning.
        
        Args:
            intent: Query intent that was executed
            result: Query result
            user_satisfied: Whether user was satisfied with result
        """
        # Track entity usage
        for entity in intent.entities:
            self._entity_usage[entity] += 1
        
        # Track filter patterns
        if intent.filters:
            filter_dict = {f.field: f.value for f in intent.filters}
            self._filter_usage[intent.query_type].append(filter_dict)
        
        # Record pattern in memory
        await self.pattern_memory.record_pattern(
            query_type=intent.query_type,
            entities=intent.entities,
            filters={f.field: f.value for f in intent.filters},
            success=user_satisfied
        )
    
    async def get_preferred_filters(
        self,
        query_type: QueryType,
        min_frequency: int = 2
    ) -> Dict[str, Any]:
        """
        Get commonly used filters for a query type.
        
        Args:
            query_type: Type of query
            min_frequency: Minimum usage frequency
            
        Returns:
            Dictionary of common filter field -> value mappings
        """
        return await self.pattern_memory.get_common_filters(
            query_type=query_type,
            min_frequency=min_frequency
        )
    
    def get_preferred_entities(self, limit: int = 5) -> List[EntityType]:
        """
        Get most frequently queried entity types.
        
        Args:
            limit: Maximum number of entities to return
            
        Returns:
            List of entity types ordered by usage frequency
        """
        return [entity for entity, _ in self._entity_usage.most_common(limit)]
    
    async def suggest_enhancements(
        self,
        intent: QueryIntent
    ) -> List[Dict[str, Any]]:
        """
        Suggest query enhancements based on learned preferences.
        
        Args:
            intent: Current query intent
            
        Returns:
            List of suggested enhancements
        """
        suggestions = []
        
        # Get existing filter fields
        existing_fields = {f.field for f in intent.filters}
        
        # Check for common filters that could be applied
        common_filters = await self.get_preferred_filters(
            query_type=intent.query_type,
            min_frequency=2
        )
        
        # Suggest filters not already in the query
        for filter_key, filter_value in common_filters.items():
            if filter_key not in existing_fields:
                suggestions.append({
                    "type": "add_filter",
                    "key": filter_key,
                    "value": filter_value,
                    "reason": f"You often use this filter for {intent.query_type.value} queries"
                })
        
        return suggestions
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current session.
        
        Returns:
            Dictionary with session statistics
        """
        most_used = None
        if self._entity_usage:
            most_used_entity = self._entity_usage.most_common(1)[0][0]
            most_used = most_used_entity.value
        
        return {
            "session_id": self.session_id,
            "total_entities_used": sum(self._entity_usage.values()),
            "unique_entities": len(self._entity_usage),
            "most_used_entity": most_used,
            "query_types_tracked": list(self._filter_usage.keys())
        }
