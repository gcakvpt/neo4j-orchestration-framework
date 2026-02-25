"""
Query Pattern Memory Implementation.
Stores learned query patterns and user preferences in Neo4j.
Enables pattern matching, preference learning, and query suggestions.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from neo4j import AsyncDriver

from ..core.types import MemoryEntry, MemoryType
from ..planning.intent import QueryType, EntityType
from ..core.exceptions import MemoryError, ValidationError
from .base import BaseMemory


class QueryPatternMemory(BaseMemory):
    """
    Neo4j-backed memory for learned query patterns.
    
    Stores query patterns with:
    - Frequency tracking
    - Success rate calculation
    - Common filter detection
    - Pattern similarity matching
    
    Graph Schema:
        (:QueryPattern {
            pattern_id: str,
            query_type: str,
            entities: List[str],
            common_filters: dict,
            frequency: int,
            last_used: datetime,
            success_rate: float,
            created_at: datetime
        })
        
        (:QueryPattern)-[:SIMILAR_TO {similarity: float}]->(:QueryPattern)
    
    Attributes:
        driver: Neo4j async driver instance
        memory_type: Always MemoryType.SEMANTIC
    """
    
    def __init__(self, driver: AsyncDriver):
        """Initialize query pattern memory."""
        super().__init__(memory_type=MemoryType.SEMANTIC)
        self.driver = driver
    
    async def record_pattern(
        self,
        query_type: QueryType,
        entities: List[EntityType],
        filters: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> str:
        """
        Record a query pattern or update existing one.
        
        Args:
            query_type: Type of query (VENDOR_LIST, RISK_ASSESSMENT, etc.)
            entities: Entity types involved
            filters: Filter conditions used
            success: Whether query was successful
            
        Returns:
            Pattern ID (existing or newly created)
            
        Raises:
            MemoryError: If recording fails
        """
        filters = filters or {}
        entity_names = [e.value for e in entities]
        
        # Generate pattern signature for matching
        pattern_sig = f"{query_type.value}::{','.join(sorted(entity_names))}"
        
        query = """
        MERGE (p:QueryPattern {pattern_signature: $pattern_sig})
        ON CREATE SET
            p.pattern_id = randomUUID(),
            p.query_type = $query_type,
            p.entities = $entities,
            p.common_filters = $filters,
            p.frequency = 1,
            p.success_count = CASE WHEN $success THEN 1 ELSE 0 END,
            p.total_count = 1,
            p.success_rate = CASE WHEN $success THEN 1.0 ELSE 0.0 END,
            p.created_at = datetime(),
            p.last_used = datetime()
        ON MATCH SET
            p.frequency = p.frequency + 1,
            p.success_count = p.success_count + CASE WHEN $success THEN 1 ELSE 0 END,
            p.total_count = p.total_count + 1,
            p.success_rate = toFloat(p.success_count) / toFloat(p.total_count),
            p.last_used = datetime(),
            p.common_filters = CASE
                WHEN p.frequency < 3 THEN $filters
                ELSE p.common_filters
            END
        RETURN p.pattern_id as pattern_id
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(
                    query,
                    pattern_sig=pattern_sig,
                    query_type=query_type.value,
                    entities=entity_names,
                    filters=filters,
                    success=success
                )
                record = await result.single()
                return record["pattern_id"]
            except Exception as e:
                raise MemoryError(f"Failed to record pattern: {e}")
    
    async def get_pattern(self, pattern_id: str) -> Optional[MemoryEntry]:
        """Get a specific pattern by ID."""
        query = """
        MATCH (p:QueryPattern {pattern_id: $pattern_id})
        RETURN p
        """
        
        with self.driver.session() as session:
            result = session.run(query, pattern_id=pattern_id)
            record = await result.single()
            
            if not record:
                return None
            
            node = record["p"]
            return MemoryEntry(
                key=pattern_id,
                value={
                    "query_type": node["query_type"],
                    "entities": node["entities"],
                    "common_filters": node["common_filters"],
                    "frequency": node["frequency"],
                    "success_rate": node["success_rate"],
                    "last_used": node["last_used"]
                },
                memory_type=MemoryType.SEMANTIC,
                metadata={
                    "pattern_id": pattern_id,
                    "created_at": node["created_at"]
                }
            )
    
    async def get(self, key: str) -> Optional[MemoryEntry]:
        """Get pattern by ID (alias for get_pattern)."""
        return await self.get_pattern(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Not supported - use record_pattern instead."""
        raise NotImplementedError("Use record_pattern() to store patterns")
    
    async def delete(self, key: str) -> bool:
        """Delete a pattern by ID."""
        query = """
        MATCH (p:QueryPattern {pattern_id: $pattern_id})
        DELETE p
        RETURN count(p) as deleted
        """
        
        with self.driver.session() as session:
            result = session.run(query, pattern_id=key)
            record = await result.single()
            return record["deleted"] > 0 if record else False
    
    async def exists(self, key: str) -> bool:
        """Check if pattern exists."""
        pattern = await self.get_pattern(key)
        return pattern is not None
    
    async def clear(self) -> None:
        """Clear all query patterns."""
        query = "MATCH (p:QueryPattern) DELETE p"
        with self.driver.session() as session:
            await session.run(query)
    
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all pattern IDs."""
        query = "MATCH (p:QueryPattern) RETURN p.pattern_id as pattern_id"
        
        with self.driver.session() as session:
            result = session.run(query)
            return [record["pattern_id"] async for record in result]

    async def get_common_filters(
        self,
        query_type: QueryType,
        min_frequency: int = 2
    ) -> Dict[str, Any]:
        """
        Get common filters for a query type.
        
        Args:
            query_type: Type of query
            min_frequency: Minimum frequency threshold
            
        Returns:
            Dictionary of common filters
        """
        query = """
        MATCH (p:QueryPattern)
        WHERE p.query_type = $query_type
        AND p.frequency >= $min_frequency
        RETURN p.common_filters as filters
        ORDER BY p.frequency DESC
        LIMIT 1
        """
        
        try:
            # Use sync session since driver is sync
            with self.driver.session() as session:
                result = session.run(
                    query,
                    query_type=query_type.value,
                    min_frequency=min_frequency
                )
                record = result.single()
                return record["filters"] if record else {}
        except Exception as e:
            raise MemoryError(f"Failed to get common filters: {e}") from e
