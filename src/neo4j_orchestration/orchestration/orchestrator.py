"""Query orchestrator integrating NL pipeline with memory systems."""

import time
from typing import Dict, Any, List, Optional
from uuid import uuid4
from dataclasses import asdict

from neo4j_orchestration.planning import QueryIntentClassifier, CypherQueryGenerator
from neo4j_orchestration.execution import QueryExecutor, QueryResult
from neo4j_orchestration.memory.episodic import SimpleEpisodicMemory
from neo4j_orchestration.memory.working import WorkingMemory
from neo4j_orchestration.memory.semantic import SemanticMemory
from neo4j_orchestration.orchestration.config import OrchestratorConfig
from neo4j_orchestration.orchestration.history import QueryHistory, QueryRecord


class QueryOrchestrator:
    """Orchestrates natural language queries with memory integration.
    
    Coordinates the complete pipeline:
    1. Natural language classification
    2. Cypher generation
    3. Query execution
    4. History tracking (Simple Episodic Memory)
    5. Result caching (Working Memory - future)
    6. Pattern learning (Semantic Memory - future)
    
    Example:
        >>> config = OrchestratorConfig()
        >>> orchestrator = QueryOrchestrator(executor, config)
        >>> result = orchestrator.query("Show critical vendors")
        >>> history = orchestrator.get_history(limit=5)
    """
    
    def __init__(
        self,
        executor: QueryExecutor,
        config: Optional[OrchestratorConfig] = None,
        episodic_memory: Optional[SimpleEpisodicMemory] = None,
        working_memory: Optional[WorkingMemory] = None,
        semantic_memory: Optional[SemanticMemory] = None,
    ):
        """Initialize query orchestrator.
        
        Args:
            executor: QueryExecutor for Neo4j operations
            config: Orchestrator configuration
            episodic_memory: Optional simple episodic memory instance
            working_memory: Optional working memory instance
            semantic_memory: Optional semantic memory instance
        """
        self.executor = executor
        self.config = config or OrchestratorConfig()
        
        # Initialize NL pipeline components
        self.classifier = QueryIntentClassifier()
        self.generator = CypherQueryGenerator()
        
        # Initialize memory systems
        self.episodic_memory = episodic_memory or SimpleEpisodicMemory()
        self.working_memory = working_memory
        self.semantic_memory = semantic_memory
        
        # Initialize query history
        self.history = QueryHistory(
            self.episodic_memory,
            max_size=self.config.max_history_size
        )
    
    def query(self, natural_language: str) -> QueryResult:
        """Execute a natural language query with full orchestration.
        
        Pipeline:
        1. Check cache (if enabled)
        2. Classify intent
        3. Generate Cypher
        4. Execute query
        5. Store in history (if enabled)
        6. Cache results (if enabled)
        7. Return results
        
        Args:
            natural_language: Natural language query from user
            
        Returns:
            QueryResult with data and metadata
            
        Raises:
            Exception: If query execution fails
        """
        query_id = str(uuid4())
        start_time = time.time()
        
        try:
            # Step 1: Check cache (future enhancement)
            # if self.config.enable_caching:
            #     cached = self._check_cache(natural_language)
            #     if cached:
            #         return cached
            
            # Step 2: Classify intent
            intent = self.classifier.classify(natural_language)
            
            # Step 3: Generate Cypher
            cypher_query, parameters = self.generator.generate(intent)
            
            # Step 4: Execute query
            result = self.executor.execute(cypher_query, parameters)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Step 5: Store in history
            if self.config.enable_history:
                # Convert dataclass to dict using asdict
                intent_dict = asdict(intent)
                
                record = QueryRecord(
                    query_id=query_id,
                    natural_language=natural_language,
                    intent=intent_dict,
                    cypher_query=cypher_query,
                    parameters=parameters,
                    result_count=len(result.records),
                    execution_time_ms=execution_time_ms,
                    success=True,
                )
                self.history.add_query(record)
            
            # Step 6: Cache results (future enhancement)
            # if self.config.enable_caching:
            #     self._cache_result(natural_language, result)
            
            return result
            
        except Exception as e:
            # Log failure to history
            execution_time_ms = (time.time() - start_time) * 1000
            
            if self.config.enable_history:
                record = QueryRecord(
                    query_id=query_id,
                    natural_language=natural_language,
                    intent={},
                    cypher_query="",
                    parameters={},
                    result_count=0,
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(e),
                )
                self.history.add_query(record)
            
            raise
    
    def get_history(self, limit: int = 10) -> List[QueryRecord]:
        """Get recent query history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of QueryRecords, most recent first
        """
        return self.history.get_history(limit=limit)
    
    def get_last_query(self) -> Optional[QueryRecord]:
        """Get the most recent query.
        
        Returns:
            Most recent QueryRecord or None if no history
        """
        return self.history.get_last_query()
    
    def get_successful_queries(self, limit: int = 10) -> List[QueryRecord]:
        """Get recent successful queries.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of successful QueryRecords
        """
        return self.history.get_successful_queries(limit=limit)
    
    def search_history_by_entity(self, entity_type: str, limit: int = 10) -> List[QueryRecord]:
        """Search query history by entity type.
        
        Args:
            entity_type: Entity type to search for
            limit: Maximum number of records to return
            
        Returns:
            List of matching QueryRecords
        """
        return self.history.search_by_entity_type(entity_type, limit=limit)
