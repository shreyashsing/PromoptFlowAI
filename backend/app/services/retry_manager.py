"""
Advanced retry manager with n8n-inspired error handling and exponential backoff.

This module provides sophisticated error handling capabilities including:
- Configurable retry policies with exponential backoff
- Error classification for retry decisions
- Circuit breaker pattern for failing services
- Retry attempt logging and metrics
- Jitter to prevent thundering herd problems
"""
import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Type, Dict, List, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """
    Classification of errors for retry decision making.
    
    Based on n8n's error handling patterns:
    - RETRYABLE: Temporary errors that should be retried
    - NON_RETRYABLE: Permanent errors that should not be retried
    - RATE_LIMITED: Rate limiting errors requiring longer delays
    - AUTHENTICATION: Authentication errors requiring token refresh
    - NETWORK: Network-related errors with specific retry patterns
    """
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION = "authentication"
    NETWORK = "network"


@dataclass
class RetryAttempt:
    """Records details of a retry attempt."""
    attempt_number: int
    timestamp: datetime
    error: str
    error_type: ErrorType
    delay_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """
    Configurable retry policy with n8n-inspired settings.
    
    This provides fine-grained control over retry behavior similar to n8n's
    retry configuration options.
    """
    # Basic retry settings
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    
    # Exponential backoff settings
    exponential_base: float = 2.0  # Multiplier for exponential backoff
    jitter: bool = True  # Add randomness to prevent thundering herd
    jitter_factor: float = 0.1  # Amount of jitter (0.0 to 1.0)
    
    # Error-specific settings
    rate_limit_delay_multiplier: float = 5.0  # Extra delay for rate limiting
    authentication_retry_delay: float = 2.0  # Delay for auth errors
    network_timeout_multiplier: float = 1.5  # Extra delay for network timeouts
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = False
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 30.0
    
    # Retry conditions
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_on_server_error: bool = True  # 5xx HTTP errors
    retry_on_rate_limit: bool = True
    
    def __post_init__(self):
        """Validate policy settings."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if not 0 <= self.jitter_factor <= 1:
            raise ValueError("jitter_factor must be between 0 and 1")


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker pattern."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half_open
    
    def is_open(self, policy: RetryPolicy) -> bool:
        """Check if circuit breaker is open (blocking requests)."""
        if self.state == "open":
            if self.last_failure_time:
                recovery_time = self.last_failure_time + timedelta(seconds=policy.circuit_breaker_recovery_timeout)
                if datetime.utcnow() >= recovery_time:
                    self.state = "half_open"
                    return False
            return True
        return False
    
    def record_success(self):
        """Record successful execution."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None
    
    def record_failure(self, policy: RetryPolicy):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= policy.circuit_breaker_failure_threshold:
            self.state = "open"


class RetryManager:
    """
    Advanced retry manager with n8n-inspired error handling.
    
    This class provides sophisticated retry logic with:
    - Exponential backoff with jitter
    - Error classification and custom retry policies
    - Circuit breaker pattern for failing services
    - Comprehensive logging and metrics
    - Support for async and sync functions
    """
    
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()
        self.logger = logging.getLogger(__name__)
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.retry_metrics: Dict[str, List[RetryAttempt]] = {}
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        error_classifier: Optional[Callable[[Exception], ErrorType]] = None,
        circuit_breaker_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic and error handling.
        
        Args:
            func: The function to execute (can be async or sync)
            *args: Positional arguments for the function
            error_classifier: Optional function to classify errors
            circuit_breaker_key: Key for circuit breaker (if enabled)
            context: Additional context for logging and metrics
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function execution
            
        Raises:
            The last exception if all retries are exhausted
        """
        context = context or {}
        function_name = getattr(func, '__name__', str(func))
        
        # Check circuit breaker
        if self.policy.circuit_breaker_enabled and circuit_breaker_key:
            circuit_breaker = self._get_circuit_breaker(circuit_breaker_key)
            if circuit_breaker.is_open(self.policy):
                raise Exception(f"Circuit breaker is open for {circuit_breaker_key}")
        
        retry_attempts = []
        last_exception = None
        
        for attempt in range(self.policy.max_retries + 1):
            try:
                start_time = time.time()
                
                # Execute function (handle both async and sync)
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Record success in circuit breaker
                if self.policy.circuit_breaker_enabled and circuit_breaker_key:
                    circuit_breaker = self._get_circuit_breaker(circuit_breaker_key)
                    circuit_breaker.record_success()
                
                # Log successful execution after retries
                if attempt > 0:
                    self.logger.info(
                        f"Function {function_name} succeeded on attempt {attempt + 1} "
                        f"after {len(retry_attempts)} retries (execution time: {execution_time:.2f}ms)"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                error_type = self._classify_error(e, error_classifier)
                
                # Check if error should be retried
                if not self._should_retry_error(error_type, e):
                    self.logger.error(f"Non-retryable error in {function_name}: {str(e)}")
                    raise
                
                # Check if we've exhausted retries
                if attempt >= self.policy.max_retries:
                    self.logger.error(
                        f"Max retries ({self.policy.max_retries}) exceeded for {function_name}: {str(e)}"
                    )
                    
                    # Record failure in circuit breaker
                    if self.policy.circuit_breaker_enabled and circuit_breaker_key:
                        circuit_breaker = self._get_circuit_breaker(circuit_breaker_key)
                        circuit_breaker.record_failure(self.policy)
                    
                    raise
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, error_type)
                
                # Record retry attempt
                retry_attempt = RetryAttempt(
                    attempt_number=attempt + 1,
                    timestamp=datetime.utcnow(),
                    error=str(e),
                    error_type=error_type,
                    delay_ms=int(delay * 1000),
                    metadata={
                        "function_name": function_name,
                        "context": context,
                        "exception_type": type(e).__name__
                    }
                )
                retry_attempts.append(retry_attempt)
                
                # Store metrics
                if function_name not in self.retry_metrics:
                    self.retry_metrics[function_name] = []
                self.retry_metrics[function_name].append(retry_attempt)
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {function_name}: {str(e)}. "
                    f"Error type: {error_type.value}. Retrying in {delay:.2f}s"
                )
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        raise last_exception or Exception("Unknown error in retry logic")
    
    def _classify_error(
        self, 
        error: Exception, 
        classifier: Optional[Callable[[Exception], ErrorType]] = None
    ) -> ErrorType:
        """
        Classify an error to determine retry behavior.
        
        Args:
            error: The exception to classify
            classifier: Optional custom classifier function
            
        Returns:
            ErrorType indicating how the error should be handled
        """
        if classifier:
            try:
                return classifier(error)
            except Exception as e:
                self.logger.warning(f"Error classifier failed: {e}. Using default classification.")
        
        # Default classification logic
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Authentication errors
        if any(keyword in error_str for keyword in ['unauthorized', 'authentication', 'invalid token', '401']):
            return ErrorType.AUTHENTICATION
        
        # Rate limiting errors
        if any(keyword in error_str for keyword in ['rate limit', 'too many requests', '429', 'quota exceeded']):
            return ErrorType.RATE_LIMITED
        
        # Network errors
        if any(keyword in error_type_name for keyword in ['connection', 'timeout', 'network']):
            return ErrorType.NETWORK
        
        # Server errors (5xx)
        if any(keyword in error_str for keyword in ['500', '502', '503', '504', 'server error', 'internal error']):
            return ErrorType.RETRYABLE
        
        # Client errors (4xx) - usually non-retryable except for specific cases
        if any(keyword in error_str for keyword in ['400', '404', '422', 'bad request', 'not found']):
            return ErrorType.NON_RETRYABLE
        
        # Connection and timeout errors
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return ErrorType.NETWORK
        
        # Default to retryable for unknown errors
        return ErrorType.RETRYABLE
    
    def _should_retry_error(self, error_type: ErrorType, error: Exception) -> bool:
        """
        Determine if an error should be retried based on policy and error type.
        
        Args:
            error_type: The classified error type
            error: The original exception
            
        Returns:
            True if the error should be retried, False otherwise
        """
        if error_type == ErrorType.NON_RETRYABLE:
            return False
        
        if error_type == ErrorType.RATE_LIMITED and not self.policy.retry_on_rate_limit:
            return False
        
        if error_type == ErrorType.NETWORK:
            if isinstance(error, TimeoutError) and not self.policy.retry_on_timeout:
                return False
            if isinstance(error, ConnectionError) and not self.policy.retry_on_connection_error:
                return False
        
        # Check for server errors
        error_str = str(error).lower()
        if any(keyword in error_str for keyword in ['500', '502', '503', '504']):
            return self.policy.retry_on_server_error
        
        return True
    
    def _calculate_delay(self, attempt: int, error_type: ErrorType) -> float:
        """
        Calculate delay before next retry attempt using exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
            error_type: Type of error that occurred
            
        Returns:
            Delay in seconds before next retry
        """
        # Base delay calculation with exponential backoff
        base_delay = self.policy.base_delay
        
        # Apply error-type specific multipliers
        if error_type == ErrorType.RATE_LIMITED:
            base_delay *= self.policy.rate_limit_delay_multiplier
        elif error_type == ErrorType.AUTHENTICATION:
            base_delay = self.policy.authentication_retry_delay
        elif error_type == ErrorType.NETWORK:
            base_delay *= self.policy.network_timeout_multiplier
        
        # Calculate exponential backoff
        delay = min(
            base_delay * (self.policy.exponential_base ** attempt),
            self.policy.max_delay
        )
        
        # Add jitter to prevent thundering herd
        if self.policy.jitter:
            jitter_amount = delay * self.policy.jitter_factor
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)
        
        return delay
    
    def _get_circuit_breaker(self, key: str) -> CircuitBreakerState:
        """Get or create circuit breaker state for a key."""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreakerState()
        return self.circuit_breakers[key]
    
    def get_retry_statistics(self, function_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get retry statistics for monitoring and debugging.
        
        Args:
            function_name: Optional function name to get specific stats
            
        Returns:
            Dictionary containing retry statistics
        """
        if function_name:
            attempts = self.retry_metrics.get(function_name, [])
            if not attempts:
                return {"function_name": function_name, "total_attempts": 0}
            
            return {
                "function_name": function_name,
                "total_attempts": len(attempts),
                "error_types": {
                    error_type.value: sum(1 for a in attempts if a.error_type == error_type)
                    for error_type in ErrorType
                },
                "average_delay_ms": sum(a.delay_ms for a in attempts) / len(attempts),
                "last_attempt": attempts[-1].timestamp.isoformat(),
                "recent_attempts": [
                    {
                        "attempt": a.attempt_number,
                        "timestamp": a.timestamp.isoformat(),
                        "error_type": a.error_type.value,
                        "delay_ms": a.delay_ms,
                        "error": a.error
                    }
                    for a in attempts[-10:]  # Last 10 attempts
                ]
            }
        else:
            # Global statistics
            total_attempts = sum(len(attempts) for attempts in self.retry_metrics.values())
            
            return {
                "total_functions": len(self.retry_metrics),
                "total_attempts": total_attempts,
                "functions_with_retries": list(self.retry_metrics.keys()),
                "circuit_breakers": {
                    key: {
                        "state": cb.state,
                        "failure_count": cb.failure_count,
                        "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
                    }
                    for key, cb in self.circuit_breakers.items()
                }
            }
    
    def reset_circuit_breaker(self, key: str) -> bool:
        """
        Manually reset a circuit breaker.
        
        Args:
            key: Circuit breaker key to reset
            
        Returns:
            True if circuit breaker was reset, False if not found
        """
        if key in self.circuit_breakers:
            self.circuit_breakers[key].record_success()
            self.logger.info(f"Circuit breaker {key} manually reset")
            return True
        return False
    
    def clear_retry_metrics(self, function_name: Optional[str] = None) -> None:
        """
        Clear retry metrics for monitoring cleanup.
        
        Args:
            function_name: Optional function name to clear specific metrics
        """
        if function_name:
            if function_name in self.retry_metrics:
                del self.retry_metrics[function_name]
                self.logger.info(f"Cleared retry metrics for {function_name}")
        else:
            self.retry_metrics.clear()
            self.logger.info("Cleared all retry metrics")


def retry_with_policy(
    policy: Optional[RetryPolicy] = None,
    error_classifier: Optional[Callable[[Exception], ErrorType]] = None,
    circuit_breaker_key: Optional[str] = None
):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        policy: Retry policy to use
        error_classifier: Function to classify errors
        circuit_breaker_key: Key for circuit breaker
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        retry_manager = RetryManager(policy)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_manager.execute_with_retry(
                func, *args,
                error_classifier=error_classifier,
                circuit_breaker_key=circuit_breaker_key,
                **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in an event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(
                retry_manager.execute_with_retry(
                    func, *args,
                    error_classifier=error_classifier,
                    circuit_breaker_key=circuit_breaker_key,
                    **kwargs
                )
            )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Predefined retry policies for common scenarios
class RetryPolicies:
    """Collection of predefined retry policies for common use cases."""
    
    # Conservative policy for critical operations
    CONSERVATIVE = RetryPolicy(
        max_retries=2,
        base_delay=2.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True
    )
    
    # Aggressive policy for resilient operations
    AGGRESSIVE = RetryPolicy(
        max_retries=5,
        base_delay=0.5,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
        circuit_breaker_enabled=True
    )
    
    # Network-optimized policy
    NETWORK = RetryPolicy(
        max_retries=4,
        base_delay=1.0,
        max_delay=45.0,
        network_timeout_multiplier=2.0,
        retry_on_timeout=True,
        retry_on_connection_error=True
    )
    
    # API-optimized policy with rate limiting handling
    API = RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=120.0,
        rate_limit_delay_multiplier=10.0,
        retry_on_rate_limit=True,
        retry_on_server_error=True
    )