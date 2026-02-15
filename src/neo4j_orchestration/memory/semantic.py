"""
Semantic Memory Implementation.

Stores versioned business rules and knowledge in Neo4j.
Provides version history, rule relationships, and activation tracking.

Example:
    >>> from neo4j import AsyncGraphDatabase
    >>> driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    >>> memory = SemanticMemory(driver)
    >>> 
    >>> # Store a business rule
    >>> await memory.store_rule(
    ...     rule_id="RULE_VR_001",
    ...     category="vendor_risk",
    ...     content={
    ...         "name": "High Risk Score Threshold",
    ...         "condition": "risk_score >= 85",
    ...         "action": "require_executive_approval",
    ...         "description": "Vendors with risk score >= 85 need exec approval"
    ...     },
    ...     tags=["vendor", "approval", "risk"],
    ...     metadata={"created_by": "gokul", "department": "risk"}
    ... )
    >>> 
    >>> # Get current version
    >>> rule = await memory.get_current_rule("RULE_VR_001")
    >>> 
    >>> # Update rule (creates new version)
    >>> await memory.store_rule(
    ...     rule_id="RULE_VR_001",
    ...     category="vendor_risk",
    ...     content={"condition": "risk_score >= 90", ...},  # Updated threshold
    ...     tags=["vendor", "approval", "risk"],
    ...     previous_version=1
    ... )
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from neo4j import AsyncDriver

from ..core.types import MemoryEntry, MemoryType
from ..core.exceptions import (
    MemoryError,
    ValidationError,
)
from .base import BaseMemory


class SemanticMemory(BaseMemory):
    """
    Neo4j-backed semantic memory for versioned business rules.
    
    Stores business rules with:
    - Version history tracking
    - Category organization
    - Tag-based search
    - Rule relationships
    - Activation status
    
    Graph Schema:
        (:Rule {
            id: str,
            version: int,
            category: str,
            content: dict,
            is_active: bool,
            created_at: datetime,
            metadata: dict
        })
        
        (:Rule)-[:HAS_TAG]->(:Tag {name: str})
        (:Rule)-[:PREVIOUS_VERSION]->(:Rule)
        (:Rule)-[:DEPENDS_ON]->(:Rule)
    
    Attributes:
        driver: Neo4j async driver instance
        memory_type: Always MemoryType.SEMANTIC
    """
    
    def __init__(self, driver: AsyncDriver):
        """
        Initialize semantic memory.
        
        Args:
            driver: Neo4j async driver for database connection
        """
        super().__init__(memory_type=MemoryType.SEMANTIC)
        self.driver = driver
    
    async def store_rule(
        self,
        rule_id: str,
        category: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        previous_version: Optional[int] = None,
        is_active: bool = True,
        depends_on: Optional[List[str]] = None,
    ) -> int:
        """
        Store a business rule (creates new version if rule exists).
        
        Args:
            rule_id: Unique rule identifier
            category: Rule category (e.g., "vendor_risk", "compliance")
            content: Rule content (conditions, actions, etc.)
            tags: Optional tags for searching
            metadata: Optional metadata
            previous_version: If updating, the version being replaced
            is_active: Whether rule is currently active
            depends_on: Optional list of rule IDs this rule depends on
            
        Returns:
            Version number of the stored rule
            
        Raises:
            ValidationError: If rule_id or category is empty
            MemoryError: If database operation fails
        """
        if not rule_id or not category:
            raise ValidationError(
                f"Rule ID and category are required: rule_id='{rule_id}', category='{category}'",
                field="rule_id" if not rule_id else "category",
                value=rule_id if not rule_id else category
            )
        
        tags = tags or []
        metadata = metadata or {}
        depends_on = depends_on or []
        created_at = datetime.utcnow()
        
        # Determine version number
        if previous_version is not None:
            version = previous_version + 1
        else:
            # Get max version for this rule_id
            version_query = """
            MATCH (r:Rule {id: $rule_id})
            RETURN max(r.version) AS max_version
            """
            async with self.driver.session() as session:
                result = await session.run(version_query, rule_id=rule_id)
                record = await result.single()
                max_version = record["max_version"] if record and record["max_version"] else 0
                version = max_version + 1
        
        # Create rule with relationships
        query = """
        // Create rule node
        CREATE (r:Rule {
            id: $rule_id,
            version: $version,
            category: $category,
            content: $content,
            is_active: $is_active,
            created_at: datetime($created_at),
            metadata: $metadata
        })
        
        // Link to tags
        WITH r
        UNWIND $tags AS tag_name
        MERGE (t:Tag {name: tag_name})
        CREATE (r)-[:HAS_TAG]->(t)
        
        // Link to previous version if specified
        WITH r
        CALL {
            WITH r
            WITH r WHERE $previous_version IS NOT NULL
            MATCH (prev:Rule {id: $rule_id, version: $previous_version})
            CREATE (r)-[:PREVIOUS_VERSION]->(prev)
            // Deactivate previous version
            SET prev.is_active = false
            RETURN prev
        }
        
        // Link dependencies
        WITH r
        UNWIND $depends_on AS dep_id
        MATCH (dep:Rule {id: dep_id})
        WHERE dep.is_active = true
        WITH r, dep
        ORDER BY dep.version DESC
        LIMIT 1
        CREATE (r)-[:DEPENDS_ON]->(dep)
        
        RETURN r.version AS version
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    rule_id=rule_id,
                    version=version,
                    category=category,
                    content=content,
                    is_active=is_active,
                    created_at=created_at.isoformat(),
                    metadata=metadata,
                    tags=tags,
                    previous_version=previous_version,
                    depends_on=depends_on,
                )
                record = await result.single()
                return record["version"] if record else version
                
        except Exception as e:
            raise MemoryError(
                f"Failed to store rule: {rule_id}",
                details={"rule_id": rule_id, "error": str(e)}
            ) from e
    
    async def get_current_rule(self, rule_id: str) -> Optional[MemoryEntry]:
        """
        Get the current (latest active) version of a rule.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            MemoryEntry with current rule version, or None if not found
        """
        query = """
        MATCH (r:Rule {id: $rule_id, is_active: true})
        OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
        OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Rule)
        WITH r, collect(DISTINCT t.name) AS tags, collect(DISTINCT dep.id) AS dependencies
        RETURN r.id AS id,
               r.version AS version,
               r.category AS category,
               r.content AS content,
               r.is_active AS is_active,
               r.created_at AS created_at,
               r.metadata AS metadata,
               tags,
               dependencies
        ORDER BY r.version DESC
        LIMIT 1
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, rule_id=rule_id)
                record = await result.single()
                
                if not record:
                    return None
                
                return MemoryEntry(
                    key=f"{record['id']}_v{record['version']}",
                    value={
                        "id": record["id"],
                        "version": record["version"],
                        "category": record["category"],
                        "content": record["content"],
                        "is_active": record["is_active"],
                        "created_at": record["created_at"],
                        "tags": record["tags"],
                        "dependencies": record["dependencies"],
                    },
                    memory_type=self.memory_type,
                    metadata=record["metadata"],
                )
                
        except Exception as e:
            raise MemoryError(
                f"Failed to retrieve current rule: {rule_id}",
                details={"rule_id": rule_id, "error": str(e)}
            ) from e
    
    async def get_rule_version(
        self,
        rule_id: str,
        version: int
    ) -> Optional[MemoryEntry]:
        """
        Get a specific version of a rule.
        
        Args:
            rule_id: Rule identifier
            version: Version number
            
        Returns:
            MemoryEntry with specified rule version, or None if not found
        """
        query = """
        MATCH (r:Rule {id: $rule_id, version: $version})
        OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
        OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Rule)
        WITH r, collect(DISTINCT t.name) AS tags, collect(DISTINCT dep.id) AS dependencies
        RETURN r.id AS id,
               r.version AS version,
               r.category AS category,
               r.content AS content,
               r.is_active AS is_active,
               r.created_at AS created_at,
               r.metadata AS metadata,
               tags,
               dependencies
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    rule_id=rule_id,
                    version=version
                )
                record = await result.single()
                
                if not record:
                    return None
                
                return MemoryEntry(
                    key=f"{record['id']}_v{record['version']}",
                    value={
                        "id": record["id"],
                        "version": record["version"],
                        "category": record["category"],
                        "content": record["content"],
                        "is_active": record["is_active"],
                        "created_at": record["created_at"],
                        "tags": record["tags"],
                        "dependencies": record["dependencies"],
                    },
                    memory_type=self.memory_type,
                    metadata=record["metadata"],
                )
                
        except Exception as e:
            raise MemoryError(
                f"Failed to retrieve rule version: {rule_id} v{version}",
                details={"rule_id": rule_id, "version": version, "error": str(e)}
            ) from e
    
    async def get_rule_history(self, rule_id: str) -> List[MemoryEntry]:
        """
        Get all versions of a rule in chronological order.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            List of MemoryEntry objects for all rule versions
        """
        query = """
        MATCH (r:Rule {id: $rule_id})
        OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
        WITH r, collect(DISTINCT t.name) AS tags
        RETURN r.id AS id,
               r.version AS version,
               r.category AS category,
               r.content AS content,
               r.is_active AS is_active,
               r.created_at AS created_at,
               r.metadata AS metadata,
               tags
        ORDER BY r.version ASC
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, rule_id=rule_id)
                
                history = []
                async for record in result:
                    history.append(
                        MemoryEntry(
                            key=f"{record['id']}_v{record['version']}",
                            value={
                                "id": record["id"],
                                "version": record["version"],
                                "category": record["category"],
                                "content": record["content"],
                                "is_active": record["is_active"],
                                "created_at": record["created_at"],
                                "tags": record["tags"],
                            },
                            memory_type=self.memory_type,
                            metadata=record["metadata"],
                        )
                    )
                
                return history
                
        except Exception as e:
            raise MemoryError(
                f"Failed to get rule history: {rule_id}",
                details={"rule_id": rule_id, "error": str(e)}
            ) from e
    
    async def get_rules_by_category(
        self,
        category: str,
        active_only: bool = True
    ) -> List[MemoryEntry]:
        """
        Get all rules in a category.
        
        Args:
            category: Category name
            active_only: If True, only return active rules
            
        Returns:
            List of MemoryEntry objects for matching rules
        """
        if active_only:
            query = """
            MATCH (r:Rule {category: $category, is_active: true})
            OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
            WITH r, collect(DISTINCT t.name) AS tags
            RETURN r.id AS id,
                   r.version AS version,
                   r.category AS category,
                   r.content AS content,
                   r.is_active AS is_active,
                   r.created_at AS created_at,
                   r.metadata AS metadata,
                   tags
            ORDER BY r.id
            """
        else:
            query = """
            MATCH (r:Rule {category: $category})
            OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
            WITH r, collect(DISTINCT t.name) AS tags
            RETURN r.id AS id,
                   r.version AS version,
                   r.category AS category,
                   r.content AS content,
                   r.is_active AS is_active,
                   r.created_at AS created_at,
                   r.metadata AS metadata,
                   tags
            ORDER BY r.id, r.version DESC
            """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, category=category)
                
                rules = []
                async for record in result:
                    rules.append(
                        MemoryEntry(
                            key=f"{record['id']}_v{record['version']}",
                            value={
                                "id": record["id"],
                                "version": record["version"],
                                "category": record["category"],
                                "content": record["content"],
                                "is_active": record["is_active"],
                                "created_at": record["created_at"],
                                "tags": record["tags"],
                            },
                            memory_type=self.memory_type,
                            metadata=record["metadata"],
                        )
                    )
                
                return rules
                
        except Exception as e:
            raise MemoryError(
                f"Failed to get rules by category: {category}",
                details={"category": category, "error": str(e)}
            ) from e
    
    async def get_rules_by_tag(
        self,
        tag: str,
        active_only: bool = True
    ) -> List[MemoryEntry]:
        """
        Get all rules with a specific tag.
        
        Args:
            tag: Tag name
            active_only: If True, only return active rules
            
        Returns:
            List of MemoryEntry objects for matching rules
        """
        if active_only:
            where_clause = "WHERE r.is_active = true"
        else:
            where_clause = ""
        
        query = f"""
        MATCH (r:Rule)-[:HAS_TAG]->(t:Tag {{name: $tag}})
        {where_clause}
        OPTIONAL MATCH (r)-[:HAS_TAG]->(all_tags:Tag)
        WITH r, collect(DISTINCT all_tags.name) AS tags
        RETURN r.id AS id,
               r.version AS version,
               r.category AS category,
               r.content AS content,
               r.is_active AS is_active,
               r.created_at AS created_at,
               r.metadata AS metadata,
               tags
        ORDER BY r.id
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, tag=tag)
                
                rules = []
                async for record in result:
                    rules.append(
                        MemoryEntry(
                            key=f"{record['id']}_v{record['version']}",
                            value={
                                "id": record["id"],
                                "version": record["version"],
                                "category": record["category"],
                                "content": record["content"],
                                "is_active": record["is_active"],
                                "created_at": record["created_at"],
                                "tags": record["tags"],
                            },
                            memory_type=self.memory_type,
                            metadata=record["metadata"],
                        )
                    )
                
                return rules
                
        except Exception as e:
            raise MemoryError(
                f"Failed to get rules by tag: {tag}",
                details={"tag": tag, "error": str(e)}
            ) from e
    
    async def deactivate_rule(self, rule_id: str) -> bool:
        """
        Deactivate the current version of a rule.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            True if rule was deactivated, False if not found
        """
        query = """
        MATCH (r:Rule {id: $rule_id, is_active: true})
        WITH r ORDER BY r.version DESC LIMIT 1
        SET r.is_active = false
        RETURN count(r) > 0 AS deactivated
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, rule_id=rule_id)
                record = await result.single()
                return record["deactivated"] if record else False
                
        except Exception as e:
            raise MemoryError(
                f"Failed to deactivate rule: {rule_id}",
                details={"rule_id": rule_id, "error": str(e)}
            ) from e
    
    # BaseMemory interface implementations
    
    async def get(self, key: str) -> Optional[MemoryEntry]:
        """
        Get current version of a rule by ID.
        
        Delegates to get_current_rule().
        """
        return await self.get_current_rule(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        **kwargs
    ) -> None:
        """
        Not supported for semantic memory (use store_rule instead).
        
        Raises:
            MemoryError: Always - use store_rule() method
        """
        raise MemoryError(
            "Direct set() not supported for semantic memory. Use store_rule() instead.",
            details={"memory_type": self.memory_type.value}
        )
    
    async def delete(self, key: str) -> bool:
        """
        Not supported for semantic memory (use deactivate_rule instead).
        
        Raises:
            MemoryError: Always - use deactivate_rule() method
        """
        raise MemoryError(
            "Delete not supported for semantic memory. Use deactivate_rule() instead.",
            details={"memory_type": self.memory_type.value}
        )
    
    async def exists(self, key: str) -> bool:
        """
        Check if an active rule exists.
        
        Args:
            key: Rule ID
            
        Returns:
            True if active rule exists, False otherwise
        """
        query = """
        MATCH (r:Rule {id: $rule_id, is_active: true})
        RETURN count(r) > 0 AS exists
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, rule_id=key)
                record = await result.single()
                return record["exists"] if record else False
                
        except Exception as e:
            raise MemoryError(
                f"Failed to check rule existence: {key}",
                details={"rule_id": key, "error": str(e)}
            ) from e
    
    async def clear(self) -> None:
        """
        Clear all rules (use with caution!).
        
        Deletes all Rule and Tag nodes.
        """
        query = """
        MATCH (r:Rule) DETACH DELETE r
        WITH count(*) AS deleted_rules
        MATCH (t:Tag) WHERE NOT (t)<--()
        DELETE t
        """
        
        try:
            async with self.driver.session() as session:
                await session.run(query)
                
        except Exception as e:
            raise MemoryError(
                "Failed to clear semantic memory",
                details={"error": str(e)}
            ) from e
    
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        List active rule IDs, optionally filtered by category pattern.
        
        Args:
            pattern: Optional category pattern
            
        Returns:
            List of rule IDs
        """
        if pattern:
            query = """
            MATCH (r:Rule {is_active: true})
            WHERE r.category CONTAINS $pattern
            RETURN DISTINCT r.id AS rule_id
            ORDER BY r.id
            """
        else:
            query = """
            MATCH (r:Rule {is_active: true})
            RETURN DISTINCT r.id AS rule_id
            ORDER BY r.id
            """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, pattern=pattern)
                records = await result.values()
                return [record[0] for record in records]
                
        except Exception as e:
            raise MemoryError(
                "Failed to list rules",
                details={"pattern": pattern, "error": str(e)}
            ) from e
