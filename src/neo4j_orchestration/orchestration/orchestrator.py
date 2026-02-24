"""Query orchestrator integrating NL pipeline with memory systems."""

import time
import asyncio
from typing import Dict, Any, List, Optional
from uuid import uuid4
from dataclasses import asdict

from neo4j_orchestration.planning import QueryIntentClassifier, CypherQueryGenerator
from neo4j_orchestration.execution import QueryExecutor, QueryResult
from neo4j_orchestration.memory.episodic import SimpleEpisodicMemory
from neo4j_orchestration.memory.working import WorkingMemory
from neo4j_orchestration.memory.semantic import SemanticMemory
from neo4j_orchestration.memory.query_patterns import QueryPatternMemory
from neo4j_orchestration.orchestration.config import OrchestratorConfig
from neo4j_orchestration.orchestration.history import QueryHistory, QueryRecord
from neo4j_orchestration.orchestration.preferences import UserPreferenceTracker
from neo4j_orchestration.orchestration.pattern_classifier import PatternEnhancedClassifier
from neo4j_orchestration.planning.intent import EntityType


class QueryOrchestrator:
    """Orchestrates natural language queries with memory integration.
    
    Coordinates the complete pipeline:
    1. Natural language classification (with optional pattern enhancement)
    2. Cypher generation
    3. Query execution
    4. History tracking (Simple Episodic Memory)
    5. Pattern learning (QueryPatternMemory + UserPreferenceTracker)
    6. Result caching (Working Memory - future)
    
    Example:
        >>> config = OrchestratorConfig()
        >>> orchestrator = QueryOrchestrator(executor, config)
        >>> result = orchestrator.query("Show critical vendors")
        >>> history = orchestrator.get_history(limit=5)
        
    Example with pattern learning:
        >>> orchestrator = QueryOrchestrator(
        ...     executor, 
        ...     config,
        ...     enable_pattern_learning=True
        ... )
        >>> result = orchestrator.query("Show vendors")
        >>> stats = orchestrator.get_pattern_stats()
    """
    
    def __init__(
        self,
        executor: QueryExecutor,
        config: Optional[OrchestratorConfig] = None,
        episodic_memory: Optional[SimpleEpisodicMemory] = None,
        working_memory: Optional[WorkingMemory] = None,
        semantic_memory: Optional[SemanticMemory] = None,
        enable_pattern_learning: bool = False,
        pattern_memory: Optional[QueryPatternMemory] = None,
        preference_tracker: Optional[UserPreferenceTracker] = None,
    ):
        """Initialize query orchestrator.
        
        Args:
            executor: QueryExecutor for Neo4j operations
            config: Orchestrator configuration
            episodic_memory: Optional simple episodic memory instance
            working_memory: Optional working memory instance
            semantic_memory: Optional semantic memory instance
            enable_pattern_learning: Enable pattern-based query enhancement
            pattern_memory: Optional query pattern memory (created if None and enabled)
            preference_tracker: Optional preference tracker (created if None and enabled)
        """
        self.executor = executor
        self.config = config or OrchestratorConfig()
        self.enable_pattern_learning = enable_pattern_learning
        
        # Initialize memory systems
        self.episodic_memory = episodic_memory or SimpleEpisodicMemory()
        self.working_memory = working_memory
        self.semantic_memory = semantic_memory
        
        # Initialize pattern learning components
        if enable_pattern_learning:
            # Initialize pattern memory (needs Neo4j driver)
            self.pattern_memory = pattern_memory or QueryPatternMemory(
                driver=executor.driver
            )
            
            # Initialize preference tracker
            session_id = str(uuid4())
            self.preference_tracker = preference_tracker or UserPreferenceTracker(
                pattern_memory=self.pattern_memory,
                session_id=session_id
            )
            
            # Wrap classifier with pattern enhancement
            base_classifier = QueryIntentClassifier()
            self.classifier = PatternEnhancedClassifier(
                base_classifier=base_classifier,
                preference_tracker=self.preference_tracker
            )
        else:
            self.pattern_memory = None
            self.preference_tracker = None
            self.classifier = QueryIntentClassifier()
        
        # Initialize Cypher generator
        self.generator = CypherQueryGenerator()
        
        # Initialize query history
        self.history = QueryHistory(
            self.episodic_memory,
            max_size=self.config.max_history_size
        )
    
    def query(self, natural_language: str) -> QueryResult:
        """Execute a natural language query with full orchestration.
        
        Pipeline:
        1. Check cache (if enabled)
        2. Classify intent (with optional pattern enhancement)
        3. Generate Cypher
        4. Execute query
        5. Record preference pattern (if pattern learning enabled)
        6. Store in history (if enabled)
        7. Cache results (if enabled)
        8. Return results
        
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
            
            # Step 2: Classify intent (with optional pattern enhancement)
            if self.enable_pattern_learning:
                # Pattern-enhanced classifier uses async classify
                import inspect
                if inspect.iscoroutinefunction(self.classifier.classify):
                    intent = asyncio.run(self.classifier.classify(natural_language))
                else:
                    intent = self.classifier.classify(natural_language)
            else:
                # Base classifier uses sync classify
                intent = self.classifier.classify(natural_language)
            
            # Step 3: Generate Cypher
            cypher_query, parameters = self.generator.generate(intent)
            
            # Step 4: Execute query
            result = self.executor.execute(cypher_query, parameters)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Step 5: Record preference pattern (if enabled)
            if self.enable_pattern_learning and self.preference_tracker:
                asyncio.run(
                    self.preference_tracker.record_query_preference(
                        intent=intent,
                        result=result,
                        user_satisfied=True
                    )
                )
            
            # Step 6: Store in history
            if self.config.enable_history:
                # Convert dataclass to dict using asdict
                from dataclasses import is_dataclass
                if is_dataclass(intent):
                    intent_dict = asdict(intent)
                else:
                    # Fallback for non-dataclass (e.g., in tests with mocks)
                    intent_dict = {}
                
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
            
            # Step 7: Cache results (future enhancement)
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
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get pattern learning statistics.
        
        Returns:
            Dictionary with pattern learning stats, or disabled indicator
        """
        if not self.enable_pattern_learning or not self.preference_tracker:
            return {"enabled": False}
        
        return {
            "enabled": True,
            **self.preference_tracker.get_session_stats()
        }
    
    def get_preferred_entities(self, limit: int = 5) -> List[EntityType]:
        """Get most frequently queried entity types.
        
        Args:
            limit: Maximum number of entities to return
            
        Returns:
            List of EntityType objects ordered by frequency
        """
        if not self.enable_pattern_learning or not self.preference_tracker:
            return []
        
        return self.preference_tracker.get_preferred_entities(limit=limit)
