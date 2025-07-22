"""
Comprehensive error handling system with retry logic and monitoring.
"""
import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, TypeVar, Union, List
from functools import wraps
import random
import json

from app.core.exceptions import (
    PromptFlowException, ErrorCategory, ErrorSeverity,
    ExternalAPIException, RateLimitException, TimeoutException,
    DatabaseException, ConnectorException
)

T = TypeVar('T')

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[type]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ExternalAPIException,
            RateLimitException,
            TimeoutException,
            DatabaseException,
            ConnectorException
        ]
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add jitter to prevent thundering herd
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if the exception should trigger a retry."""
        if attempt >= self.max_attempts:
            return False
        
        # Check if it's a PromptFlowException with retryable flag
        if isinstance(exception, PromptFlowException):
            return exception.retryable
        
        # Check if it's in the list of retryable exceptions
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)


class ErrorHandler:
    """Comprehensive error handling system."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging and user-friendly response.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            user_id: ID of the user who encountered the error
            
        Returns:
            Dictionary containing error response for API
        """
        context = context or {}
        
        # Convert to PromptFlowException if needed
        if not isinstance(error, PromptFlowException):
            error = self._convert_to_promptflow_exception(error)
        
        # Log the error
        await self._log_error(error, context, user_id)
        
        # Update error tracking
        self._update_error_tracking(error)
        
        # Check circuit breaker
        if self._should_circuit_break(error):
            return self._create_circuit_breaker_response()
        
        # Create response
        return self._create_error_response(error)
    
    def _convert_to_promptflow_exception(self, error: Exception) -> PromptFlowException:
        """Convert a generic exception to a PromptFlowException."""
        error_message = str(error)
        
        # Map common exceptions to appropriate categories
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ExternalAPIException(
                message=error_message,
                original_exception=error,
                retryable=True
            )
        elif isinstance(error, ValueError):
            return PromptFlowException(
                message=error_message,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                original_exception=error
            )
        elif isinstance(error, PermissionError):
            return PromptFlowException(
                message=error_message,
                category=ErrorCategory.AUTHORIZATION,
                severity=ErrorSeverity.HIGH,
                original_exception=error
            )
        else:
            return PromptFlowException(
                message=error_message,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                original_exception=error,
                retryable=True
            )
    
    async def _log_error(
        self,
        error: PromptFlowException,
        context: Dict[str, Any],
        user_id: Optional[str]
    ):
        """Log error with appropriate level and context."""
        log_data = {
            "error_code": error.error_code,
            "category": error.category.value,
            "severity": error.severity.value,
            "error_message": error.message,  # Changed from 'message' to 'error_message'
            "user_id": user_id,
            "context": context,
            "details": error.details,
            "error_timestamp": error.timestamp.isoformat(),  # Changed from 'timestamp'
            "traceback": traceback.format_exc() if error.original_exception else None
        }
        
        log_message = f"Error {error.error_code}: {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=log_data)
        else:
            logger.info(log_message, extra=log_data)
    
    def _update_error_tracking(self, error: PromptFlowException):
        """Update error tracking for monitoring and circuit breaking."""
        error_key = f"{error.category.value}_{error.__class__.__name__}"
        
        # Update error counts
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_errors[error_key] = datetime.utcnow()
        
        # Clean up old entries (older than 1 hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        keys_to_remove = [
            key for key, timestamp in self.last_errors.items()
            if timestamp < cutoff_time
        ]
        for key in keys_to_remove:
            self.error_counts.pop(key, None)
            self.last_errors.pop(key, None)
    
    def _should_circuit_break(self, error: PromptFlowException) -> bool:
        """Determine if circuit breaker should be triggered."""
        error_key = f"{error.category.value}_{error.__class__.__name__}"
        
        # Circuit break if too many errors in short time
        error_count = self.error_counts.get(error_key, 0)
        if error_count > 10:  # More than 10 errors of same type
            last_error_time = self.last_errors.get(error_key)
            if last_error_time and (datetime.utcnow() - last_error_time).seconds < 300:  # Within 5 minutes
                return True
        
        return False
    
    def _create_circuit_breaker_response(self) -> Dict[str, Any]:
        """Create response when circuit breaker is triggered."""
        return {
            "error": True,
            "error_code": "CIRCUIT_BREAKER_OPEN",
            "message": "Service temporarily unavailable due to high error rate",
            "user_message": "The service is temporarily unavailable. Please try again in a few minutes.",
            "retryable": True,
            "retry_after": 300  # 5 minutes
        }
    
    def _create_error_response(self, error: PromptFlowException) -> Dict[str, Any]:
        """Create API error response from PromptFlowException."""
        return {
            "error": True,
            "error_code": error.error_code,
            "message": error.message,
            "user_message": error.user_message,
            "category": error.category.value,
            "severity": error.severity.value,
            "details": error.details,
            "recovery_suggestions": error.recovery_suggestions,
            "retryable": error.retryable,
            "timestamp": error.timestamp.isoformat()
        }


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        config: Retry configuration. Uses default if None.
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not config.should_retry(e, attempt):
                        break
                    
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        await asyncio.sleep(delay)
            
            # All retries exhausted, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


def with_error_handling(error_handler: Optional[ErrorHandler] = None):
    """
    Decorator to add comprehensive error handling to async functions.
    
    Args:
        error_handler: Error handler instance. Creates default if None.
    """
    if error_handler is None:
        error_handler = ErrorHandler()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],  # Truncate for logging
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}  # Truncate values
                }
                
                # Handle the error
                error_response = await error_handler.handle_error(e, context)
                
                # Re-raise as PromptFlowException for consistent handling
                if isinstance(e, PromptFlowException):
                    raise e
                else:
                    raise PromptFlowException(
                        message=str(e),
                        original_exception=e
                    )
        
        return wrapper
    return decorator


# Global error handler instance
global_error_handler = ErrorHandler()


async def handle_api_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function for handling API errors.
    
    Args:
        error: The exception that occurred
        context: Additional context about the error
        
    Returns:
        Dictionary containing error response for API
    """
    return await global_error_handler.handle_error(error, context)


def get_error_stats() -> Dict[str, Any]:
    """Get current error statistics for monitoring."""
    return {
        "error_counts": global_error_handler.error_counts.copy(),
        "last_errors": {
            key: timestamp.isoformat()
            for key, timestamp in global_error_handler.last_errors.items()
        },
        "circuit_breakers": global_error_handler.circuit_breakers.copy()
    }