"""Neo4j connection configuration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Neo4jConfig:
    """Configuration for Neo4j database connection."""
    
    uri: str
    username: str
    password: str
    database: str = "neo4j"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_timeout: float = 30.0
    max_transaction_retry_time: float = 30.0
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.uri:
            raise ValueError("URI is required")
        if not self.username:
            raise ValueError("Username is required")
        if not self.password:
            raise ValueError("Password is required")
        
        valid_prefixes = ["bolt://", "neo4j://", "bolt+s://", "neo4j+s://"]
        if not any(self.uri.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"Invalid URI format: {self.uri}. "
                "Must start with bolt://, neo4j://, bolt+s://, or neo4j+s://"
            )
    
    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Create configuration from environment variables."""
        import os
        
        return cls(
            uri=os.environ.get("NEO4J_URI", ""),
            username=os.environ.get("NEO4J_USERNAME", ""),
            password=os.environ.get("NEO4J_PASSWORD", ""),
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        )
