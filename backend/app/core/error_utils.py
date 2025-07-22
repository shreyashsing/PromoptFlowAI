"""
Utility functions for applying error handling to existing services.
"""
import asyncio
import logging
from typing import Any, Dict, Optional, Callable, TypeVar
from functools import wraps

from app.core.error_handler import with_retry, with_error_handling, RetryConfig, global_error_handler
from app.core.exceptions import (
    PromptFlowException, ConnectorException, ExternalAPIException,
    RateLimitException, TimeoutException, DatabaseException
)
from app.core.monitoring import record_error_for_monitoring

T = TypeVar('T')
logger = logging.getLogger(__name__)


def handle_connector_errors(connector_name: str):
    """
    Decorator specifically for connector operations.
    
    Args:
        connector_name: Name of the connector for error context
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Convert to ConnectorException if not already a PromptFlowException
                if not isinstance(e, PromptFlowException):
                    connector_error = ConnectorException(
                        message=f"Connector '{connector_name}' failed: {str(e)}",
                        connector_name=connector_name,
                        original_exception=e,
                        retryable=True
                    )
                    await record_error_for_monitoring(connector_error)
                    raise connector_error
                else:
                    await record_error_for_monitoring(e)
                    raise e
        
        return wrapper
    return decorator


def handle_external_api_errors(api_name: str, retryable: bool = True):
    """
    Decorator for external API calls.
    
    Args:
        api_name: Name of the external API
        retryable: Whether the operation should be retryable
    """
    retry_config = RetryConfig(
        max_attempts=3 if retryable else 1,
        base_delay=1.0,
        max_delay=30.0
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @with_retry(retry_config)
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if not isinstance(e, PromptFlowException):
                    api_error = ExternalAPIException(
                        message=f"External API '{api_name}' failed: {str(e)}",
                        api_name=api_name,
                        original_exception=e,
                        retryable=retryable
                    )
                    await record_error_for_monitoring(api_error)
                    raise api_error
                else:
                    await record_error_for_monitoring(e)
                    raise e
        
        return wrapper
    return decorator


def handle_database_errors(operation: str):
    """
    Decorator for database operations.
    
    Args:
        operation: Description of the database operation
    """
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @with_retry(retry_config)
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if not isinstance(e, PromptFlowException):
                    db_error = DatabaseException(
                        message=f"Database operation '{operation}' failed: {str(e)}",
                        original_exception=e,
                        retryable=True,
                        details={"operation": operation}
                    )
                    await record_error_for_monitoring(db_error)
                    raise db_error
                else:
                    await record_error_for_monitoring(e)
                    raise e
        
        return wrapper
    return decorator


def safe_async_call(
    func: Callable[..., T],
    *args,
    default_return: Any = None,
    log_errors: bool = True,
    **kwargs
) -> T:
    """
    Safely call an async function with error handling.
    
    Args:
        func: The async function to call
        *args: Arguments to pass to the function
        default_return: Value to return if function fails
        log_errors: Whether to log errors
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Function result or default_return if function fails
    """
    async def _safe_call():
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if log_errors:
                logger.error(f"Safe async call failed for {func.__name__}: {e}")
            return default_return
    
    return asyncio.create_task(_safe_call())


def create_error_context(
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    operation: Optional[str] = None,
    **additional_context
) -> Dict[str, Any]:
    """
    Create error context dictionary for consistent error reporting.
    
    Args:
        user_id: ID of the user associated with the error
        request_id: ID of the request that caused the error
        operation: Name of the operation that failed
        **additional_context: Additional context fields
        
    Returns:
        Dictionary containing error context
    """
    context = {}
    
    if user_id:
        context["user_id"] = user_id
    if request_id:
        context["request_id"] = request_id
    if operation:
        context["operation"] = operation
    
    context.update(additional_context)
    return context


async def handle_and_log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    operation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle and log an error with full context.
    
    Args:
        error: The exception that occurred
        context: Additional error context
        user_id: ID of the user who encountered the error
        operation: Name of the operation that failed
        
    Returns:
        Error response dictionary
    """
    # Create context without duplicating keys
    base_context = context or {}
    
    # Build full context, avoiding duplicate keys
    full_context = {}
    full_context.update(base_context)
    
    # Only add user_id and operation if not already in context
    if user_id and 'user_id' not in full_context:
        full_context['user_id'] = user_id
    if operation and 'operation' not in full_context:
        full_context['operation'] = operation
    
    return await global_error_handler.handle_error(error, full_context, user_id)


def log_function_performance(operation_name: str):
    """
    Decorator to log function performance metrics.
    
    Args:
        operation_name: Name of the operation for logging
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            import time
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Operation '{operation_name}' completed successfully",
                    extra={
                        "operation": operation_name,
                        "duration": duration,
                        "success": True
                    }
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.warning(
                    f"Operation '{operation_name}' failed",
                    extra={
                        "operation": operation_name,
                        "duration": duration,
                        "success": False,
                        "error": str(e)
                    }
                )
                
                raise e
        
        return wrapper
    return decorator


class ErrorBoundary:
    """Context manager for error boundary operations."""
    
    def __init__(
        self,
        operation: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True
    ):
        self.operation = operation
        self.user_id = user_id
        self.context = context or {}
        self.reraise = reraise
        self.error_occurred = False
        self.error_response = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_occurred = True
            self.error_response = await handle_and_log_error(
                exc_val,
                context=self.context,
                user_id=self.user_id,
                operation=self.operation
            )
            
            if not self.reraise:
                return True  # Suppress the exception
        
        return False  # Let the exception propagate


# Convenience functions for common error scenarios
async def handle_validation_error(field: str, message: str, value: Any = None) -> Dict[str, Any]:
    """Handle validation errors with consistent formatting."""
    from app.core.exceptions import ValidationException
    
    error = ValidationException(
        message=message,
        field=field,
        details={"field": field, "value": str(value) if value is not None else None}
    )
    
    return await global_error_handler.handle_error(error)


async def handle_authentication_error(message: str = "Authentication failed") -> Dict[str, Any]:
    """Handle authentication errors with consistent formatting."""
    from app.core.exceptions import AuthenticationException
    
    error = AuthenticationException(message=message)
    return await global_error_handler.handle_error(error)


async def handle_rate_limit_error(retry_after: int = 60) -> Dict[str, Any]:
    """Handle rate limit errors with consistent formatting."""
    error = RateLimitException(
        message="Rate limit exceeded",
        retry_after=retry_after
    )
    
    return await global_error_handler.handle_error(error)


async def handle_timeout_error(operation: str, timeout_duration: float) -> Dict[str, Any]:
    """Handle timeout errors with consistent formatting."""
    error = TimeoutException(
        message=f"Operation '{operation}' timed out after {timeout_duration} seconds",
        timeout_duration=timeout_duration
    )
    
    return await global_error_handler.handle_error(error)