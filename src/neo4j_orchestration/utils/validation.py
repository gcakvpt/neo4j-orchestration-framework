"""
Validation utilities for data validation and type checking.
"""

from typing import Any, Dict, List, Optional
from neo4j_orchestration.core.exceptions import ValidationError


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str],
    context: str = "data"
) -> None:
    """Validate that required fields are present
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        context: Description of what's being validated
    
    Raises:
        ValidationError: If any required field is missing
    """
    missing = [f for f in required_fields if f not in data]
    
    if missing:
        raise ValidationError(
            f"Missing required fields in {context}: {', '.join(missing)}",
            field="multiple",
            value=missing
        )


def validate_type(
    value: Any,
    expected_type: type,
    field_name: str = "value"
) -> None:
    """Validate value is of expected type
    
    Args:
        value: Value to validate
        expected_type: Expected type
        field_name: Name of field being validated
    
    Raises:
        ValidationError: If value is not of expected type
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"Field '{field_name}' must be {expected_type.__name__}, "
            f"got {type(value).__name__}",
            field=field_name,
            value=value
        )


def validate_non_empty(
    value: Any,
    field_name: str = "value"
) -> None:
    """Validate value is not empty
    
    Args:
        value: Value to validate
        field_name: Name of field being validated
    
    Raises:
        ValidationError: If value is empty
    """
    if not value:
        raise ValidationError(
            f"Field '{field_name}' cannot be empty",
            field=field_name,
            value=value
        )


__all__ = [
    "validate_required_fields",
    "validate_type",
    "validate_non_empty",
]
