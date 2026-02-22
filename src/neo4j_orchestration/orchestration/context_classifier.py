"""
Context-Aware Query Intent Classifier

Enhances QueryIntentClassifier with conversation context for:
- Pronoun resolution ("them", "those", "it")
- Follow-up query understanding
- Entity reference tracking
"""
import asyncio
import re
from typing import Optional, List
from neo4j_orchestration.planning.classifier import QueryIntentClassifier
from neo4j_orchestration.planning.intent import QueryIntent, QueryType, EntityType
from neo4j_orchestration.orchestration.context import ConversationContext
from neo4j_orchestration.utils.logging import get_logger

logger = get_logger(__name__)


class ContextAwareClassifier:
    """
    Enhances intent classification with conversation context.
    
    Wraps QueryIntentClassifier to add context-aware features:
    - Resolves pronouns using entity history
    - Infers entities from previous queries
    - Detects follow-up queries
    
    Example:
        >>> classifier = ContextAwareClassifier(base_classifier)
        >>> # First query
        >>> intent1 = classifier.classify_with_context(
        ...     "Show all vendors",
        ...     context
        ... )
        >>> # Follow-up with pronoun
        >>> intent2 = classifier.classify_with_context(
        ...     "Which ones have critical risks?",
        ...     context
        ... )
        >>> # intent2 inherits VENDOR entity from intent1
    """
    
    # Pronouns that trigger context resolution
    PRONOUNS = {
        "it", "them", "those", "these", "that", "this",
        "they", "which", "what", "who"
    }
    
    # Follow-up indicators
    FOLLOWUP_PATTERNS = [
        r"\b(which|what|how many)\b",
        r"\b(show|find|get|list)\s+(me\s+)?(the\s+)?ones?\b",
        r"\b(only|just|filter|narrow)\b",
        r"\b(also|additionally|and)\b"
    ]
    
    def __init__(self, base_classifier: QueryIntentClassifier):
        """
        Initialize context-aware classifier.
        
        Args:
            base_classifier: Base QueryIntentClassifier instance
        """
        self.base_classifier = base_classifier
        logger.info("ContextAwareClassifier initialized")
    
    def classify_with_context(
        self,
        query: str,
        context: Optional[ConversationContext] = None
    ) -> QueryIntent:
        """
        Classify query with conversation context.
        
        Args:
            query: Natural language query string
            context: Optional conversation context
            
        Returns:
            Enhanced QueryIntent with context-resolved entities
        """
        # Get base classification
        intent = self.base_classifier.classify(query)
        
        # If no context, return base intent
        if not context:
            logger.debug("No context provided, using base intent")
            return intent
        
        # Check if this is a follow-up query
        is_followup = self._is_followup_query(query)
        
        if is_followup:
            logger.debug(f"Detected follow-up query: '{query[:50]}...'")
            # Enhance intent with context
            intent = self._enhance_with_context(intent, query, context)
        
        return intent
    
    def _is_followup_query(self, query: str) -> bool:
        """
        Detect if query is a follow-up to previous conversation.
        
        Args:
            query: Query string
            
        Returns:
            True if query appears to be a follow-up
        """
        query_lower = query.lower()
        
        # Check for pronouns
        words = set(query_lower.split())
        if words & self.PRONOUNS:
            return True
        
        # Check for follow-up patterns
        for pattern in self.FOLLOWUP_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def _enhance_with_context(
        self,
        intent: QueryIntent,
        query: str,
        context: ConversationContext
    ) -> QueryIntent:
        """
        Enhance intent with conversation context.
        
        Args:
            intent: Base intent from classifier
            query: Original query string
            context: Conversation context
            
        Returns:
            Enhanced QueryIntent
        """
        # Run async context lookup in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create new task
            last_entities = []
            last_query_type = None
            logger.warning("Running in async context, skipping context enhancement")
        else:
            # Safe to run in sync context
            last_entities = loop.run_until_complete(context.get_last_entities(n=2))
            last_query_type = loop.run_until_complete(context.get_last_query_type())
        
        # If intent has no entities but context has recent entities, inherit them
        if not intent.entities and last_entities:
            logger.info(f"Inheriting entities from context: {[e.name for e in last_entities]}")
            intent.entities = last_entities[:3]  # Take up to 3 most recent
        
        # If intent query type is UNKNOWN but we have context, try to infer
        if intent.query_type == QueryType.UNKNOWN and last_query_type:
            # For simple follow-ups, keep same query type
            if self._is_simple_followup(query):
                logger.info(f"Inferring query type from context: {last_query_type.name}")
                intent.query_type = last_query_type
        
        return intent
    
    def _is_simple_followup(self, query: str) -> bool:
        """
        Check if query is a simple follow-up (filter/refinement).
        
        Args:
            query: Query string
            
        Returns:
            True if query appears to be a simple filter/refinement
        """
        query_lower = query.lower()
        
        # Simple follow-ups start with filtering words
        simple_patterns = [
            r"^(only|just|filter|show)\b",
            r"^(which|what)\s+(ones?|about)\b",
            r"^(in|with|for|by)\b"
        ]
        
        return any(re.match(pattern, query_lower) for pattern in simple_patterns)


def classify_with_context(
    query: str,
    base_classifier: QueryIntentClassifier,
    context: Optional[ConversationContext] = None
) -> QueryIntent:
    """
    Convenience function for context-aware classification.
    
    Args:
        query: Natural language query
        base_classifier: Base classifier instance
        context: Optional conversation context
        
    Returns:
        QueryIntent with context enhancement
    """
    classifier = ContextAwareClassifier(base_classifier)
    return classifier.classify_with_context(query, context)
