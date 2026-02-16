"""Unit tests for Neo4jConfig."""

import pytest
from neo4j_orchestration.execution import Neo4jConfig


class TestNeo4jConfig:
    """Test Neo4jConfig class."""
    
    def test_valid_config(self):
        """Test creating valid configuration."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password123",
        )
        
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password == "password123"
        assert config.database == "neo4j"
    
    def test_missing_uri_raises_error(self):
        """Test missing URI raises ValueError."""
        with pytest.raises(ValueError, match="URI is required"):
            Neo4jConfig(uri="", username="neo4j", password="password")
    
    def test_invalid_uri_format_raises_error(self):
        """Test invalid URI format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URI format"):
            Neo4jConfig(
                uri="http://localhost:7687",
                username="neo4j",
                password="password",
            )
    
    def test_from_env(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
        monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
        monkeypatch.setenv("NEO4J_PASSWORD", "test_password")
        
        config = Neo4jConfig.from_env()
        
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password == "test_password"
