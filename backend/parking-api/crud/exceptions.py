"""
Custom exceptions for CRUD operations.
"""

from typing import Optional, Any


class CRUDError(Exception):
    """Base exception for CRUD operations."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class RecordNotFoundError(CRUDError):
    """Exception raised when a record is not found."""
    
    def __init__(self, model_name: str, record_id: str):
        self.model_name = model_name
        self.record_id = record_id
        message = f"{model_name} with id {record_id} not found"
        super().__init__(message, {"model": model_name, "id": record_id})


class DuplicateRecordError(CRUDError):
    """Exception raised when trying to create a duplicate record."""
    
    def __init__(self, model_name: str, field: str, value: Any):
        self.model_name = model_name
        self.field = field
        self.value = value
        message = f"{model_name} with {field} '{value}' already exists"
        super().__init__(message, {"model": model_name, "field": field, "value": value})


class InvalidOperationError(CRUDError):
    """Exception raised when an operation is invalid."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, details)


class ValidationError(CRUDError):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str, errors: Optional[dict] = None):
        self.errors = errors or {}
        super().__init__(message, {"validation_errors": errors})