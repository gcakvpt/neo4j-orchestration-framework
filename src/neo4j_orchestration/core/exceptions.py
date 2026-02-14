"""
Custom exceptions for the orchestration framework.

Exception hierarchy:
    OrchestrationError (base)
    ├── ConfigurationError
    ├── Neo4jError
    │   ├── Neo4jConnectionError
    │   ├── Neo4jQueryError
    │   └── GraphProjectionError
    ├── MemoryError
    │   ├── MemoryNotFoundError
    │   └── MemoryExpiredError
    ├── PlanningError
    │   ├── IntentRecognitionError
    │   └── QueryPlanningError
    ├── WorkflowError
    │   ├── WorkflowExecutionError
    │   └── StepExecutionError
    └── ValidationError
"""


class OrchestrationError(Exception):
    """Base exception for all orchestration framework errors"""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(OrchestrationError):
    """Raised when configuration is invalid or missing"""
    pass


# ============================================================================
# NEO4J ERRORS
# ============================================================================

class Neo4jError(OrchestrationError):
    """Base exception for Neo4j-related errors"""
    pass


class Neo4jConnectionError(Neo4jError):
    """Cannot connect to Neo4j database"""
    pass


class Neo4jQueryError(Neo4jError):
    """Error executing Cypher query"""
    
    def __init__(self, message: str, query: str = None, parameters: dict = None):
        super().__init__(message, details={"query": query, "parameters": parameters})
        self.query = query
        self.parameters = parameters


class GraphProjectionError(Neo4jError):
    """Error creating or managing GDS graph projection"""
    pass


# ============================================================================
# MEMORY ERRORS
# ============================================================================

class MemoryError(OrchestrationError):
    """Base exception for memory system errors"""
    pass


class MemoryNotFoundError(MemoryError):
    """Requested memory entry not found"""
    
    def __init__(self, message: str, key: str = None, memory_type: str = None):
        super().__init__(
            message,
            details={"key": key, "memory_type": memory_type}
        )
        self.key = key
        self.memory_type = memory_type


class MemoryExpiredError(MemoryError):
    """Memory entry has expired (TTL)"""
    pass


# ============================================================================
# PLANNING ERRORS
# ============================================================================

class PlanningError(OrchestrationError):
    """Base exception for query planning errors"""
    pass


class IntentRecognitionError(PlanningError):
    """Cannot determine user intent from query"""
    
    def __init__(self, message: str, query_text: str = None):
        super().__init__(message, details={"query_text": query_text})
        self.query_text = query_text


class QueryPlanningError(PlanningError):
    """Cannot generate execution plan for query"""
    pass


# ============================================================================
# WORKFLOW ERRORS
# ============================================================================

class WorkflowError(OrchestrationError):
    """Base exception for workflow execution errors"""
    pass


class WorkflowExecutionError(WorkflowError):
    """Error during workflow execution"""
    
    def __init__(
        self,
        message: str,
        workflow_name: str = None,
        failed_step: str = None,
        cause: Exception = None
    ):
        super().__init__(
            message,
            details={
                "workflow_name": workflow_name,
                "failed_step": failed_step,
                "cause": str(cause) if cause else None
            }
        )
        self.workflow_name = workflow_name
        self.failed_step = failed_step
        self.cause = cause


class StepExecutionError(WorkflowError):
    """Error executing specific workflow step"""
    
    def __init__(
        self,
        message: str,
        step_name: str = None,
        cause: Exception = None
    ):
        super().__init__(
            message,
            details={"step_name": step_name, "cause": str(cause) if cause else None}
        )
        self.step_name = step_name
        self.cause = cause


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(OrchestrationError):
    """Data validation failed"""
    
    def __init__(self, message: str, field: str = None, value: any = None):
        super().__init__(
            message,
            details={"field": field, "value": str(value) if value else None}
        )
        self.field = field
        self.value = value


# Export all exceptions
__all__ = [
    "OrchestrationError",
    "ConfigurationError",
    "Neo4jError",
    "Neo4jConnectionError",
    "Neo4jQueryError",
    "GraphProjectionError",
    "MemoryError",
    "MemoryNotFoundError",
    "MemoryExpiredError",
    "PlanningError",
    "IntentRecognitionError",
    "QueryPlanningError",
    "WorkflowError",
    "WorkflowExecutionError",
    "StepExecutionError",
    "ValidationError",
]
