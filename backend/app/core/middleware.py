"""
Middleware for comprehensive error handling and monitoring.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.error_handler import handle_api_error
from app.core.monitoring import record_request_time, record_error_for_monitoring
from app.core.exceptions import PromptFlowException
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive error handling and monitoring.
    
    This middleware:
    - Records request timing for monitoring
    - Handles all unhandled exceptions with proper error responses
    - Records errors for monitoring and alerting
    - Provides consistent error response format
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive error handling."""
        start_time = time.time()
        request_id = f"req_{int(start_time * 1000)}"
        
        # Add request ID to context
        request.state.request_id = request_id
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Record successful request timing
            duration = time.time() - start_time
            record_request_time(duration)
            
            # Add timing and request ID headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as exc:
            # Record request timing even for errors
            duration = time.time() - start_time
            record_request_time(duration)
            
            # Create error context
            error_context = {
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "duration": duration,
                "query_params": dict(request.query_params),
                "path_params": dict(request.path_params)
            }
            
            # Handle the error using our comprehensive error handling system
            try:
                error_response = await handle_api_error(exc, context=error_context)
                
                # Record error for monitoring if it's a PromptFlowException
                if isinstance(exc, PromptFlowException):
                    await record_error_for_monitoring(exc)
                
                # Determine HTTP status code
                status_code = self._determine_status_code(exc, error_response)
                
                # Create JSON response
                response = JSONResponse(
                    status_code=status_code,
                    content=error_response
                )
                
                # Add headers
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{duration:.3f}"
                
                return response
                
            except Exception as handler_error:
                # Fallback if our error handler fails
                logger.critical(
                    f"Error handler failed for request {request_id}: {handler_error}",
                    extra={
                        "request_id": request_id,
                        "original_error": str(exc),
                        "handler_error": str(handler_error),
                        "context": error_context
                    }
                )
                
                # Return basic error response
                fallback_response = {
                    "error": True,
                    "error_code": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                    "user_message": "Something went wrong. Please try again or contact support.",
                    "request_id": request_id
                }
                
                response = JSONResponse(
                    status_code=500,
                    content=fallback_response
                )
                
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{duration:.3f}"
                
                return response
    
    def _determine_status_code(self, exception: Exception, error_response: dict) -> int:
        """
        Determine appropriate HTTP status code for the error.
        
        Args:
            exception: The original exception
            error_response: The error response dictionary
            
        Returns:
            HTTP status code
        """
        # Check if it's a PromptFlowException with specific category
        if isinstance(exception, PromptFlowException):
            category = exception.category.value
            
            if category in ["authentication"]:
                return 401
            elif category in ["authorization"]:
                return 403
            elif category in ["validation", "user_input"]:
                return 400
            elif category in ["rate_limit"]:
                return 429
            elif category in ["timeout"]:
                return 408
            elif category in ["external_api", "connector"]:
                return 502  # Bad Gateway
            elif category in ["database"]:
                return 503  # Service Unavailable
            else:
                return 500
        
        # Check error response for specific codes
        error_code = error_response.get("error_code", "")
        
        if "VALIDATION" in error_code or "INPUT" in error_code:
            return 400
        elif "AUTH" in error_code:
            return 401
        elif "PERMISSION" in error_code or "FORBIDDEN" in error_code:
            return 403
        elif "NOT_FOUND" in error_code:
            return 404
        elif "RATE_LIMIT" in error_code:
            return 429
        elif "TIMEOUT" in error_code:
            return 408
        else:
            return 500


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.
    
    This middleware logs all incoming requests and their responses
    for debugging and monitoring purposes.
    """
    
    def __init__(self, app, log_level: str = "INFO"):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', f"req_{int(start_time * 1000)}")
        
        # Log incoming request
        logger.log(
            self.log_level,
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", "")[:100]  # Truncate
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        
        logger.log(
            self.log_level,
            f"Response: {response.status_code} for {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration": duration,
                "method": request.method,
                "path": request.url.path
            }
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response