"""Configuration for query orchestrator."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class OrchestratorConfig(BaseModel):
    """Configuration for QueryOrchestrator.
    
    Attributes:
        enable_history: Whether to track query history in episodic memory
        enable_caching: Whether to cache results in working memory
        enable_context: Whether to use working memory for query context
        cache_ttl_seconds: TTL for cached results (default: 300 = 5 minutes)
        max_history_size: Maximum number of queries to keep in history
    """
    
    model_config = ConfigDict(frozen=True)
    
    enable_history: bool = Field(default=True, description="Track query history")
    enable_caching: bool = Field(default=True, description="Cache query results")
    enable_context: bool = Field(default=True, description="Maintain query context")
    cache_ttl_seconds: int = Field(default=300, ge=0, description="Cache TTL in seconds")
    max_history_size: Optional[int] = Field(default=100, ge=1, description="Max history entries")
