"""
Unit tests for exception hierarchy.
"""

import pytest
from neo4j_orchestration.core.exceptions import (
    OrchestrationError,
    ConfigurationError,
    Neo4jConnectionError,
    Neo4jQueryError,
    MemoryNotFoundError,
    ValidationError,
    WorkflowExecutionError,
)


def test_base_orchestration_error():
    """Test base OrchestrationError"""
    error = OrchestrationError("Test error", details={"key": "value"})
    
    assert str(error) == "Test error"
    assert error.details == {"key": "value"}


def test_configuration_error():
    """Test ConfigurationError"""
    error = ConfigurationError("Missing config", details={"file": "config.yml"})
    
    assert "Missing config" in str(error)
    assert error.details["file"] == "config.yml"


def test_neo4j_query_error():
    """Test Neo4jQueryError includes query details"""
    error = Neo4jQueryError(
        "Syntax error",
        query="MATCH (n RETURN n",
        parameters={"id": "123"}
    )
    
    assert "Syntax error" in str(error)
    assert error.details["query"] == "MATCH (n RETURN n"
    assert error.details["parameters"]["id"] == "123"


def test_memory_not_found_error():
    """Test MemoryNotFoundError includes key and type"""
    error = MemoryNotFoundError(
        key="test_key",
        memory_type="WORKING"
    )
    
    assert "test_key" in str(error)
    assert error.details["key"] == "test_key"
    assert error.details["memory_type"] == "WORKING"


def test_validation_error():
    """Test ValidationError includes field and value"""
    error = ValidationError(
        "Invalid value",
        field="email",
        value="not-an-email"
    )
    
    assert "Invalid value" in str(error)
    assert error.details["field"] == "email"
    assert error.details["value"] == "not-an-email"


def test_workflow_execution_error():
    """Test WorkflowExecutionError includes workflow context"""
    cause = ValueError("Step failed")
    error = WorkflowExecutionError(
        workflow_name="vendor_assessment",
        failed_step="calculate_risk",
        cause=cause
    )
    
    assert "vendor_assessment" in str(error)
    assert error.details["workflow_name"] == "vendor_assessment"
    assert error.details["failed_step"] == "calculate_risk"
    assert error.details["cause"] == cause


def test_exception_inheritance():
    """Test all exceptions inherit from OrchestrationError"""
    assert issubclass(ConfigurationError, OrchestrationError)
    assert issubclass(Neo4jConnectionError, OrchestrationError)
    assert issubclass(MemoryNotFoundError, OrchestrationError)
    assert issubclass(ValidationError, OrchestrationError)
    assert issubclass(WorkflowExecutionError, OrchestrationError)
