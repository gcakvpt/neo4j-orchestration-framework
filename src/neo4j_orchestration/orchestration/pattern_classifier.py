"""
Pattern-enhanced query classification.
"""
from typing import Optional, Dict, Any

from ..planning.classifier import QueryIntentClassifier
from ..planning.intent import QueryIntent, FilterCondition, FilterOperator
from .preferences import UserPreferenceTracker


class PatternEnhancedClassifier:
    """
    Enhances query classification with learned patterns.
    
    Wraps QueryIntentClassifier and adds:
    - Automatic filter suggestions from user preferences
    - Entity inference from usage patterns
    - Confidence boosting for common patterns
    """
    
    def __init__(
        self,
        base_classifier: QueryIntentClassifier,
        preference_tracker: Optional[UserPreferenceTracker] = None
    ):
        """
        Initialize pattern-enhanced classifier.
        
        Args:
            base_classifier: Base QueryIntentClassifier instance
            preference_tracker: Optional UserPreferenceTracker for learning
        """
        self.base_classifier = base_classifier
        self.preference_tracker = preference_tracker
    
    async def classify(
        self,
        query: str,
        apply_enhancements: bool = True
    ) -> QueryIntent:
        """
        Classify query with optional pattern enhancements.
        
        Args:
            query: Natural language query
            apply_enhancements: Whether to apply learned patterns
            
        Returns:
            Enhanced QueryIntent
        """
        # Get base classification
        intent = self.base_classifier.classify(query)
        
        # Apply enhancements if enabled and tracker available
        if apply_enhancements and self.preference_tracker:
            intent = await self._enhance_with_patterns(intent)
        
        return intent
    
    async def _enhance_with_patterns(
        self,
        intent: QueryIntent
    ) -> QueryIntent:
        """
        Enhance intent with learned patterns.
        
        Args:
            intent: Base query intent
            
        Returns:
            Enhanced intent with suggested filters
        """
        # Get suggestions
        suggestions = await self.preference_tracker.suggest_enhancements(intent)
        
        # Apply filter suggestions
        for suggestion in suggestions:
            if suggestion["type"] == "add_filter":
                # Add suggested filter to intent
                new_filter = FilterCondition(
                    field=suggestion["key"],
                    operator=FilterOperator.EQUALS,
                    value=suggestion["value"]
                )
                
                # Add to filters list
                intent.filters.append(new_filter)
                
                # Add metadata about enhancement
                intent.metadata["pattern_enhancements"] = intent.metadata.get(
                    "pattern_enhancements", []
                ) + [suggestion["reason"]]
        
        return intent
    
    def get_enhancement_stats(self) -> Dict[str, Any]:
        """
        Get statistics about pattern enhancements.
        
        Returns:
            Dictionary with enhancement statistics
        """
        if not self.preference_tracker:
            return {
                "tracker_enabled": False,
                "session_stats": {}
            }
        
        return {
            "tracker_enabled": True,
            "session_stats": self.preference_tracker.get_session_stats()
        }
