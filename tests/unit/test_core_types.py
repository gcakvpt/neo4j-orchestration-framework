"""
Unit tests for core type definitions.
"""

import pytest
from datetime import datetime
from neo4j_orchestration.core.types import (
    MemoryType,
    QueryIntent,
    AnalyticsAlgorithm,
    MemoryEntry,
    QueryContext,
    QueryPlan,
    AnalysisSession,
    create_session_id,
    create_query_id,
)


def test_memory_entry_creation():
    """Test MemoryEntry creation with required fields"""
    entry = MemoryEntry(
        key="test_key",
        value={"data": "test"},
        memory_type=MemoryType.WORKING
    )
    
    assert entry.key == "test_key"
    assert entry.value == {"data": "test"}
    assert entry.memory_type == MemoryType.WORKING
    assert isinstance(entry.created_at, datetime)
    assert entry.expires_at is None


def test_query_context_with_filters():
    """Test QueryContext with filters"""
    context = QueryContext(
        intent=QueryIntent.ENTITY_LOOKUP,
        entity_type="Vendor",
        filters={"criticality": "Critical"}
    )
    
    assert context.intent == QueryIntent.ENTITY_LOOKUP
    assert context.entity_type == "Vendor"
    assert context.filters["criticality"] == "Critical"


def test_query_plan_creation():
    """Test QueryPlan with steps"""
    plan = QueryPlan(
        intent=QueryIntent.PATTERN_MATCH,
        cypher_query="MATCH (n) RETURN n",
        estimated_cost=100
    )
    
    assert plan.intent == QueryIntent.PATTERN_MATCH
    assert plan.cypher_query == "MATCH (n) RETURN n"
    assert plan.estimated_cost == 100
    assert len(plan.steps) == 0  # Default empty list


def test_analysis_session_creation():
    """Test AnalysisSession creation"""
    session = AnalysisSession(
        entity_id="VEN001",
        workflow_name="vendor_risk_assessment",
        query_text="Analyze vendor VEN001",
        results={"risk_score": 75}
    )
    
    assert session.entity_id == "VEN001"
    assert session.workflow_name == "vendor_risk_assessment"
    assert session.results["risk_score"] == 75
    assert session.session_id.startswith("sess_")


def test_create_session_id():
    """Test session ID generation"""
    sid1 = create_session_id()
    sid2 = create_session_id()
    
    assert sid1.startswith("sess_")
    assert sid2.startswith("sess_")
    assert sid1 != sid2  # Should be unique


def test_create_query_id():
    """Test query ID generation"""
    qid1 = create_query_id()
    qid2 = create_query_id()
    
    assert qid1.startswith("qry_")
    assert qid2.startswith("qry_")
    assert qid1 != qid2  # Should be unique
