"""
Pytest configuration and shared fixtures.
"""

import pytest
from datetime import datetime, timedelta


@pytest.fixture
def sample_timestamp():
    """Provide a sample timestamp for testing"""
    return datetime(2024, 1, 15, 10, 30, 0)


@pytest.fixture
def sample_entity_id():
    """Provide a sample entity ID"""
    return "VEN001"


@pytest.fixture
def sample_metadata():
    """Provide sample metadata dictionary"""
    return {
        "source": "test",
        "created_by": "pytest",
        "version": "1.0"
    }


@pytest.fixture
def sample_query_context():
    """Provide a sample QueryContext for testing"""
    from neo4j_orchestration.core.types import QueryContext, QueryIntent
    
    return QueryContext(
        intent=QueryIntent.ENTITY_LOOKUP,
        entity_type="Vendor",
        filters={"criticality": "Critical"}
    )


@pytest.fixture
def sample_cypher_query():
    """Provide a sample Cypher query"""
    return "MATCH (v:Vendor {id: $vendor_id}) RETURN v"


@pytest.fixture
def sample_cypher_parameters():
    """Provide sample Cypher parameters"""
    return {"vendor_id": "VEN001"}
