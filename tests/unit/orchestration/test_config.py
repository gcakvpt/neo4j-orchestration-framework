"""Unit tests for orchestrator configuration."""

import pytest
from neo4j_orchestration.orchestration.config import OrchestratorConfig


class TestOrchestratorConfig:
    """Test suite for OrchestratorConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestratorConfig()
        
        assert config.enable_history is True
        assert config.enable_caching is True
        assert config.enable_context is True
        assert config.cache_ttl_seconds == 300
        assert config.max_history_size == 100
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = OrchestratorConfig(
            enable_history=False,
            enable_caching=False,
            cache_ttl_seconds=600,
            max_history_size=50,
        )
        
        assert config.enable_history is False
        assert config.enable_caching is False
        assert config.cache_ttl_seconds == 600
        assert config.max_history_size == 50
    
    def test_config_is_frozen(self):
        """Test that config is immutable."""
        config = OrchestratorConfig()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            config.enable_history = False
    
    def test_cache_ttl_validation(self):
        """Test cache TTL must be non-negative."""
        with pytest.raises(Exception):
            OrchestratorConfig(cache_ttl_seconds=-1)
    
    def test_max_history_validation(self):
        """Test max history must be positive."""
        with pytest.raises(Exception):
            OrchestratorConfig(max_history_size=0)
