# Week 4 Session 3 - Step 3: PatternEnhancedClassifier

## Goal
Create a classifier wrapper that enhances queries using learned patterns.

## File to Create

**src/neo4j_orchestration/orchestration/pattern_classifier.py**
```python
"""
Pattern-enhanced query classification.
"""
from typing import Optional, Dict, Any
from ..planning.classifier import QueryIntentClassifier
from ..planning.intent import QueryIntent
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
                from ..planning.intent import FilterCondition, FilterOperator
                
                new_filter = FilterCondition(
                    field=suggestion["key"],
                    operator=FilterOperator.EQUALS,
                    value=suggestion["value"]
                )
                
                # Create new intent with added filter
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
```

## Test File to Create

**tests/unit/orchestration/test_pattern_classifier.py**

### Test Cases

1. **test_initialization** - Basic setup
2. **test_classify_without_tracker** - No enhancement
3. **test_classify_without_enhancements** - Tracker but disabled
4. **test_classify_with_enhancements** - Apply suggestions
5. **test_enhancement_adds_filters** - Verify filter addition
6. **test_enhancement_metadata** - Check metadata tracking
7. **test_no_enhancements_needed** - All filters already present
8. **test_get_stats_without_tracker** - Stats when disabled
9. **test_get_stats_with_tracker** - Stats when enabled

## Implementation Notes

### Key Design Decisions

1. **Wrapper Pattern**
   - Wraps QueryIntentClassifier (composition)
   - Delegates base classification
   - Adds enhancement layer

2. **Optional Enhancement**
   - `apply_enhancements` parameter for control
   - Can disable for testing/comparison

3. **Metadata Tracking**
   - Records which enhancements were applied
   - Useful for debugging and analysis

4. **Filter Addition**
   - Creates FilterCondition objects
   - Appends to intent.filters list
   - Preserves existing filters

### Testing Strategy

1. Mock both dependencies:
   - QueryIntentClassifier
   - UserPreferenceTracker

2. Verify filter addition logic

3. Check metadata correctly recorded

4. Test with/without tracker

## Expected Outcome

- New PatternEnhancedClassifier class
- 9+ passing tests
- 95%+ coverage
- Ready for orchestrator integration

## Estimated Time

30-45 minutes
