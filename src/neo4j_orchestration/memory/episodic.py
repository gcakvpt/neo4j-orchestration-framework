"""
Episodic Memory Implementation.

Stores session-based interaction history in Neo4j with temporal queries.
Provides immutable append-only history of analysis sessions.

Example:
    >>> from neo4j import AsyncGraphDatabase
    >>> driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    >>> memory = EpisodicMemory(driver)
    >>> 
    >>> # Save a session
    >>> await memory.save_session(
    ...     session_id="sess_20260214_001",
    ...     workflow="vendor_risk_analysis",
    ...     entities=["VEN001", "VEN002"],
    ...     results={"risk_score": 85, "findings": [...]},
    ...     metadata={"analyst": "gokul", "duration_ms": 2500}
    ... )
    >>> 
    >>> # Query sessions
    >>> sessions = await memory.get_sessions_by_entity("VEN001", limit=10)
    >>> recent = await memory.get_recent_sessions(days=7)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from neo4j import AsyncDriver

from ..core.types import MemoryEntry, MemoryType
from ..core.exceptions import (
    MemoryError,
    MemoryNotFoundError,
    ValidationError,
)
from .base import BaseMemory


class EpisodicMemory(BaseMemory):
    """
    Neo4j-backed episodic memory for session history.
    
    Stores immutable session records with:
    - Temporal indexing
    - Entity relationships
    - Workflow categorization
    - Full result preservation
    
    Graph Schema:
        (:Session {
            id: str,
            workflow: str,
            timestamp: datetime,
            results: dict,
            metadata: dict
        })
        
        (:Session)-[:ANALYZED]->(:Entity {id: str})
        (:Session)-[:FOLLOWED_BY]->(:Session)
    
    Attributes:
        driver: Neo4j async driver instance
        memory_type: Always MemoryType.EPISODIC
    """
    
    def __init__(self, driver: AsyncDriver):
        """
        Initialize episodic memory.
        
        Args:
            driver: Neo4j async driver for database connection
        """
        super().__init__(memory_type=MemoryType.EPISODIC)
        self.driver = driver
    
    async def save_session(
        self,
        session_id: str,
        workflow: str,
        entities: List[str],
        results: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        previous_session_id: Optional[str] = None,
    ) -> str:
        """
        Save a new session to episodic memory.
        
        Args:
            session_id: Unique session identifier
            workflow: Workflow type (e.g., "vendor_risk_analysis")
            entities: List of entity IDs analyzed in session
            results: Session results/findings
            metadata: Optional session metadata
            previous_session_id: Optional link to previous session
            
        Returns:
            The session_id that was saved
            
        Raises:
            ValidationError: If session_id or workflow is empty
            MemoryError: If database operation fails
        """
        if not session_id or not workflow:
            raise ValidationError(
                f"Session ID and workflow are required: session_id='{session_id}', workflow='{workflow}'",
                field="session_id" if not session_id else "workflow",
                value=session_id if not session_id else workflow
            )
        
        timestamp = datetime.utcnow()
        metadata = metadata or {}
        
        query = """
        // Create session node
        CREATE (s:Session {
            id: $session_id,
            workflow: $workflow,
            timestamp: datetime($timestamp),
            results: $results,
            metadata: $metadata
        })
        
        // Link to entities
        WITH s
        UNWIND $entities AS entity_id
        MERGE (e:Entity {id: entity_id})
        CREATE (s)-[:ANALYZED]->(e)
        
        // Link to previous session if provided
        WITH s
        CALL {
            WITH s
            WITH s WHERE $previous_session_id IS NOT NULL
            MATCH (prev:Session {id: $previous_session_id})
            CREATE (prev)-[:FOLLOWED_BY]->(s)
            RETURN prev
        }
        
        RETURN s.id AS session_id
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    session_id=session_id,
                    workflow=workflow,
                    timestamp=timestamp.isoformat(),
                    results=results,
                    metadata=metadata,
                    entities=entities,
                    previous_session_id=previous_session_id,
                )
                record = await result.single()
                return record["session_id"]
                
        except Exception as e:
            raise MemoryError(
                f"Failed to save session: {session_id}",
                details={"session_id": session_id, "error": str(e)}
            ) from e
    
    async def get(self, key: str) -> Optional[MemoryEntry]:
        """
        Get a session by ID.
        
        Args:
            key: Session ID to retrieve
            
        Returns:
            MemoryEntry containing session data, or None if not found
        """
        query = """
        MATCH (s:Session {id: $session_id})
        OPTIONAL MATCH (s)-[:ANALYZED]->(e:Entity)
        RETURN s.id AS id,
               s.workflow AS workflow,
               s.timestamp AS timestamp,
               s.results AS results,
               s.metadata AS metadata,
               collect(e.id) AS entities
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, session_id=key)
                record = await result.single()
                
                if not record:
                    return None
                
                return MemoryEntry(
                    key=record["id"],
                    value={
                        "workflow": record["workflow"],
                        "timestamp": record["timestamp"],
                        "results": record["results"],
                        "entities": record["entities"],
                    },
                    memory_type=self.memory_type,
                    metadata=record["metadata"],
                )
                
        except Exception as e:
            raise MemoryError(
                f"Failed to retrieve session: {key}",
                details={"session_id": key, "error": str(e)}
            ) from e
    
    async def set(
        self,
        key: str,
        value: Any,
        **kwargs
    ) -> None:
        """
        Not supported for episodic memory (use save_session instead).
        
        Raises:
            MemoryError: Always - episodic memory is append-only
        """
        raise MemoryError(
            "Direct set() not supported for episodic memory. Use save_session() instead.",
            details={"memory_type": self.memory_type.value}
        )
    
    async def delete(self, key: str) -> bool:
        """
        Not supported for episodic memory (immutable history).
        
        Raises:
            MemoryError: Always - episodic memory is immutable
        """
        raise MemoryError(
            "Delete not supported for episodic memory (immutable history)",
            details={"memory_type": self.memory_type.value}
        )
    
    async def exists(self, key: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            key: Session ID to check
            
        Returns:
            True if session exists, False otherwise
        """
        query = "MATCH (s:Session {id: $session_id}) RETURN count(s) > 0 AS exists"
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, session_id=key)
                record = await result.single()
                return record["exists"] if record else False
                
        except Exception as e:
            raise MemoryError(
                f"Failed to check session existence: {key}",
                details={"session_id": key, "error": str(e)}
            ) from e
    
    async def clear(self) -> None:
        """
        Clear all sessions (use with caution!).
        
        Deletes all Session nodes and relationships.
        """
        query = "MATCH (s:Session) DETACH DELETE s"
        
        try:
            async with self.driver.session() as session:
                await session.run(query)
                
        except Exception as e:
            raise MemoryError(
                "Failed to clear episodic memory",
                details={"error": str(e)}
            ) from e
    
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        List session IDs, optionally filtered by workflow pattern.
        
        Args:
            pattern: Optional workflow pattern (e.g., "vendor_*")
            
        Returns:
            List of session IDs
        """
        if pattern:
            query = """
            MATCH (s:Session)
            WHERE s.workflow CONTAINS $pattern
            RETURN s.id AS session_id
            ORDER BY s.timestamp DESC
            """
        else:
            query = """
            MATCH (s:Session)
            RETURN s.id AS session_id
            ORDER BY s.timestamp DESC
            """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, pattern=pattern)
                records = await result.values()
                return [record[0] for record in records]
                
        except Exception as e:
            raise MemoryError(
                "Failed to list sessions",
                details={"pattern": pattern, "error": str(e)}
            ) from e
    
    async def get_sessions_by_entity(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        Get sessions that analyzed a specific entity.
        
        Args:
            entity_id: Entity ID to search for
            limit: Maximum number of sessions to return
            
        Returns:
            List of MemoryEntry objects for matching sessions
        """
        query = """
        MATCH (s:Session)-[:ANALYZED]->(e:Entity {id: $entity_id})
        OPTIONAL MATCH (s)-[:ANALYZED]->(other:Entity)
        WITH s, collect(DISTINCT other.id) AS entities
        RETURN s.id AS id,
               s.workflow AS workflow,
               s.timestamp AS timestamp,
               s.results AS results,
               s.metadata AS metadata,
               entities
        ORDER BY s.timestamp DESC
        LIMIT $limit
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    entity_id=entity_id,
                    limit=limit
                )
                
                sessions = []
                async for record in result:
                    sessions.append(
                        MemoryEntry(
                            key=record["id"],
                            value={
                                "workflow": record["workflow"],
                                "timestamp": record["timestamp"],
                                "results": record["results"],
                                "entities": record["entities"],
                            },
                            memory_type=self.memory_type,
                            metadata=record["metadata"],
                        )
                    )
                
                return sessions
                
        except Exception as e:
            raise MemoryError(
                f"Failed to get sessions for entity: {entity_id}",
                details={"entity_id": entity_id, "error": str(e)}
            ) from e
    
    async def get_recent_sessions(
        self,
        days: int = 7,
        workflow: Optional[str] = None,
        limit: int = 50
    ) -> List[MemoryEntry]:
        """
        Get recent sessions within a time window.
        
        Args:
            days: Number of days to look back
            workflow: Optional workflow filter
            limit: Maximum number of sessions
            
        Returns:
            List of MemoryEntry objects for recent sessions
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        if workflow:
            query = """
            MATCH (s:Session)
            WHERE s.timestamp >= datetime($cutoff)
              AND s.workflow = $workflow
            OPTIONAL MATCH (s)-[:ANALYZED]->(e:Entity)
            WITH s, collect(e.id) AS entities
            RETURN s.id AS id,
                   s.workflow AS workflow,
                   s.timestamp AS timestamp,
                   s.results AS results,
                   s.metadata AS metadata,
                   entities
            ORDER BY s.timestamp DESC
            LIMIT $limit
            """
        else:
            query = """
            MATCH (s:Session)
            WHERE s.timestamp >= datetime($cutoff)
            OPTIONAL MATCH (s)-[:ANALYZED]->(e:Entity)
            WITH s, collect(e.id) AS entities
            RETURN s.id AS id,
                   s.workflow AS workflow,
                   s.timestamp AS timestamp,
                   s.results AS results,
                   s.metadata AS metadata,
                   entities
            ORDER BY s.timestamp DESC
            LIMIT $limit
            """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    cutoff=cutoff.isoformat(),
                    workflow=workflow,
                    limit=limit
                )
                
                sessions = []
                async for record in result:
                    sessions.append(
                        MemoryEntry(
                            key=record["id"],
                            value={
                                "workflow": record["workflow"],
                                "timestamp": record["timestamp"],
                                "results": record["results"],
                                "entities": record["entities"],
                            },
                            memory_type=self.memory_type,
                            metadata=record["metadata"],
                        )
                    )
                
                return sessions
                
        except Exception as e:
            raise MemoryError(
                f"Failed to get recent sessions",
                details={"days": days, "workflow": workflow, "error": str(e)}
            ) from e
    
    async def get_session_chain(
        self,
        session_id: str,
        max_depth: int = 10
    ) -> List[MemoryEntry]:
        """
        Get a session and its history chain.
        
        Follows FOLLOWED_BY relationships backwards to reconstruct
        the conversation/analysis thread.
        
        Args:
            session_id: Starting session ID
            max_depth: Maximum chain depth to traverse
            
        Returns:
            List of MemoryEntry objects in chronological order
        """
        query = """
        MATCH path = (start:Session {id: $session_id})<-[:FOLLOWED_BY*0..%d]-(s:Session)
        WITH s
        ORDER BY s.timestamp ASC
        OPTIONAL MATCH (s)-[:ANALYZED]->(e:Entity)
        WITH s, collect(e.id) AS entities
        RETURN s.id AS id,
               s.workflow AS workflow,
               s.timestamp AS timestamp,
               s.results AS results,
               s.metadata AS metadata,
               entities
        """ % max_depth
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, session_id=session_id)
                
                chain = []
                async for record in result:
                    chain.append(
                        MemoryEntry(
                            key=record["id"],
                            value={
                                "workflow": record["workflow"],
                                "timestamp": record["timestamp"],
                                "results": record["results"],
                                "entities": record["entities"],
                            },
                            memory_type=self.memory_type,
                            metadata=record["metadata"],
                        )
                    )
                
                return chain
                
        except Exception as e:
            raise MemoryError(
                f"Failed to get session chain: {session_id}",
                details={"session_id": session_id, "error": str(e)}
            ) from e
