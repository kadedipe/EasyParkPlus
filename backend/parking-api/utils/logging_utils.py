"""
Logging utility functions.
"""

import logging
import json
import sys
from typing import Optional, Dict, Any, Union
from datetime import datetime
from contextvars import ContextVar
from contextlib import contextmanager
import traceback
from pythonjsonlogger import jsonlogger

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging.
    """
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        
        # Add request context
        request_id = request_id_var.get()
        if request_id:
            log_record['request_id'] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_record['user_id'] = user_id


def setup_logging(
    app_name: str = "parking-api",
    log_level: str = "INFO",
    json_format: bool = True
) -> None:
    """
    Setup logging configuration.
    
    Args:
        app_name: Application name
        log_level: Logging level
        json_format: Use JSON format
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter
    if json_format:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set application name in logs
    logging.Logger.root.name = app_name


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    user_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log HTTP request.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        ip: Client IP address
        user_agent: User agent
        user_id: User ID
        extra: Extra data to log
    """
    log_data = {
        "type": "request",
        "method": method,
        "path": path,
        "ip": ip,
        "user_agent": user_agent,
        "user_id": user_id
    }
    
    if extra:
        log_data.update(extra)
    
    logger.info(f"HTTP Request: {method} {path}", extra=log_data)


def log_response(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log HTTP response.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user_id: User ID
        extra: Extra data to log
    """
    log_data = {
        "type": "response",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "user_id": user_id
    }
    
    if extra:
        log_data.update(extra)
    
    log_level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(log_level, f"HTTP Response: {method} {path} - {status_code}", extra=log_data)


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    include_traceback: bool = True
) -> None:
    """
    Log error with context.
    
    Args:
        logger: Logger instance
        error: Exception object
        context: Error context
        include_traceback: Include traceback in log
    """
    log_data = {
        "type": "error",
        "error_type": error.__class__.__name__,
        "error_message": str(error),
    }
    
    if context:
        log_data["context"] = context
    
    if include_traceback:
        log_data["traceback"] = traceback.format_exc()
    
    logger.error(f"Error: {error.__class__.__name__}: {error}", extra=log_data)


def audit_log(
    logger: logging.Logger,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log audit event.
    
    Args:
        logger: Logger instance
        action: Action performed
        resource: Resource type
        resource_id: Resource ID
        user_id: User ID
        old_value: Old value
        new_value: New value
        extra: Extra data to log
    """
    log_data = {
        "type": "audit",
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if old_value is not None:
        # Mask sensitive data if needed
        if isinstance(old_value, dict):
            old_value = mask_sensitive_dict(old_value)
        log_data["old_value"] = old_value
    
    if new_value is not None:
        if isinstance(new_value, dict):
            new_value = mask_sensitive_dict(new_value)
        log_data["new_value"] = new_value
    
    if extra:
        log_data.update(extra)
    
    logger.info(f"AUDIT: {action} on {resource}", extra=log_data)


def mask_sensitive_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive fields in dictionary.
    
    Args:
        data: Dictionary to mask
        
    Returns:
        Dict[str, Any]: Masked dictionary
    """
    sensitive_fields = ['password', 'token', 'secret', 'api_key', 'credit_card']
    masked_data = data.copy()
    
    for field in sensitive_fields:
        if field in masked_data:
            masked_data[field] = '********'
    
    return masked_data


class LogContext:
    """
    Context manager for logging context.
    """
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize log context.
        
        Args:
            request_id: Request ID
            user_id: User ID
            **kwargs: Additional context variables
        """
        self.request_id = request_id
        self.user_id = user_id
        self.extra_context = kwargs
        self.token = None
    
    def __enter__(self):
        """Enter context."""
        if self.request_id:
            self.token = request_id_var.set(self.request_id)
        if self.user_id:
            user_id_var.set(self.user_id)
        
        # Set additional context variables
        for key, value in self.extra_context.items():
            var = ContextVar(key, default=None)
            var.set(value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if self.token:
            request_id_var.reset(self.token)


class RequestLogger:
    """
    Request logger middleware helper.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize request logger.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    @contextmanager
    def log_request_response(
        self,
        method: str,
        path: str,
        request_id: str,
        user_id: Optional[str] = None
    ):
        """
        Context manager to log request and response.
        
        Args:
            method: HTTP method
            path: Request path
            request_id: Request ID
            user_id: User ID
        """
        import time
        
        start_time = time.time()
        
        # Set context
        token = request_id_var.set(request_id)
        if user_id:
            user_id_var.set(user_id)
        
        try:
            # Log request
            log_request(self.logger, method, path, user_id=user_id)
            
            yield
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            log_response(
                self.logger,
                method,
                path,
                500,
                duration_ms,
                user_id=user_id
            )
            log_error(self.logger, e)
            raise
        
        finally:
            # Log response
            duration_ms = (time.time() - start_time) * 1000
            log_response(
                self.logger,
                method,
                path,
                200,  # This should be actual status code
                duration_ms,
                user_id=user_id
            )
            
            # Reset context
            request_id_var.reset(token)