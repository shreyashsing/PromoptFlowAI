"""
Comprehensive error response formatting for ReAct agent.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.react_agent import ReactError, ReasoningStep, ToolCall
from app.core.exceptions import (
    PromptFlowException, AgentExecutionError, ToolExecutionError,
    AuthenticationException, ValidationException, ConnectorException,
    ExternalAPIException, RateLimitException, TimeoutException
)

logger = logging.getLogger(__name__)


class ReactErrorFormatter:
    """
    Comprehensive error response formatter for ReAct agent.
    
    This class implements comprehensive error response formatting as specified in requirement 1.5
    and requirement 3.4 for creating user-friendly error messages with suggestions.
    """
    
    def __init__(self):
        self.error_code_counter = 0
    
    async def format_error_response(
        self,
        error: Exception,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        reasoning_trace: Optional[List[ReasoningStep]] = None,
        failed_tool_calls: Optional[List[ToolCall]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format a comprehensive error response for the ReAct agent.
        
        Args:
            error: The exception that occurred
            session_id: Session ID where error occurred
            request_id: Request ID for tracking
            reasoning_trace: Reasoning steps before error
            failed_tool_calls: Tool calls that failed
            context: Additional context about the error
            
        Returns:
            Comprehensive error response dictionary
        """
        try:
            # Create ReactError model
            react_error = await self._create_react_error(
                error, session_id, request_id, reasoning_trace, failed_tool_calls, context
            )
            
            # Format the response
            response = await self._format_response(react_error)
            
            # Log the error
            await self._log_error(react_error, context)
            
            return response
            
        except Exception as formatting_error:
            logger.error(f"Error formatting failed: {formatting_error}")
            return await self._create_fallback_error_response(error, session_id, request_id)
    
    async def _create_react_error(
        self,
        error: Exception,
        session_id: Optional[str],
        request_id: Optional[str],
        reasoning_trace: Optional[List[ReasoningStep]],
        failed_tool_calls: Optional[List[ToolCall]],
        context: Optional[Dict[str, Any]]
    ) -> ReactError:
        """
        Create a ReactError model from an exception.
        
        This method implements detailed error information as specified in requirement 1.5.
        """
        # Generate unique error code
        error_code = self._generate_error_code(error)
        
        # Determine error type and category
        error_type, category = self._categorize_error(error)
        
        # Extract error details
        details = self._extract_error_details(error)
        
        # Generate user-friendly message
        user_message = self._generate_user_message(error, error_type)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(error, error_type)
        
        # Generate recovery actions
        recovery_actions = self._generate_recovery_actions(error, error_type)
        
        # Determine retry information
        retryable, retry_after = self._determine_retry_info(error)
        
        # Determine severity
        severity = self._determine_severity(error)
        
        return ReactError(
            error_type=error_type,
            error_code=error_code,
            message=str(error),
            user_message=user_message,
            details=details,
            reasoning_trace=reasoning_trace or [],
            failed_tool_calls=failed_tool_calls or [],
            suggestions=suggestions,
            recovery_actions=recovery_actions,
            session_id=session_id,
            request_id=request_id or str(uuid.uuid4()),
            retryable=retryable,
            retry_after=retry_after,
            severity=severity,
            category=category,
            context=context or {},
            timestamp=datetime.utcnow()
        )
    
    def _generate_error_code(self, error: Exception) -> str:
        """Generate a unique error code for tracking."""
        self.error_code_counter += 1
        error_type = type(error).__name__
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"REACT_{error_type.upper()}_{timestamp}_{self.error_code_counter:03d}"
    
    def _categorize_error(self, error: Exception) -> tuple[str, str]:
        """
        Categorize the error type and category.
        
        Returns:
            Tuple of (error_type, category)
        """
        if isinstance(error, AgentExecutionError):
            if "timeout" in str(error).lower():
                return "agent_timeout", "timeout"
            elif "infinite loop" in str(error).lower():
                return "infinite_loop", "agent_reasoning"
            elif "cancelled" in str(error).lower():
                return "execution_cancelled", "agent_reasoning"
            else:
                return "agent_execution_error", "agent_reasoning"
        
        elif isinstance(error, ToolExecutionError):
            return "tool_execution_error", "tool"
        
        elif isinstance(error, AuthenticationException):
            return "authentication_error", "authentication"
        
        elif isinstance(error, ValidationException):
            return "validation_error", "validation"
        
        elif isinstance(error, ConnectorException):
            return "connector_error", "connector"
        
        elif isinstance(error, ExternalAPIException):
            return "external_api_error", "external_api"
        
        elif isinstance(error, RateLimitException):
            return "rate_limit_error", "rate_limit"
        
        elif isinstance(error, TimeoutException):
            return "timeout_error", "timeout"
        
        elif isinstance(error, (ConnectionError, OSError)):
            return "connection_error", "network"
        
        elif isinstance(error, ValueError):
            return "value_error", "validation"
        
        elif isinstance(error, PermissionError):
            return "permission_error", "authorization"
        
        else:
            return "unexpected_error", "system"
    
    def _extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """Extract detailed information from the error."""
        details = {
            "error_class": type(error).__name__,
            "error_module": getattr(type(error), '__module__', 'unknown')
        }
        
        # Extract details from PromptFlowException
        if isinstance(error, PromptFlowException):
            details.update({
                "category": error.category.value if hasattr(error.category, 'value') else str(error.category),
                "severity": error.severity.value if hasattr(error.severity, 'value') else str(error.severity),
                "retryable": error.retryable,
                "original_exception": str(error.original_exception) if error.original_exception else None
            })
            details.update(error.details)
        
        # Extract tool-specific details
        if isinstance(error, ToolExecutionError):
            if hasattr(error, 'tool_name'):
                details['tool_name'] = error.tool_name
        
        # Extract connector-specific details
        if isinstance(error, ConnectorException):
            if hasattr(error, 'connector_name'):
                details['connector_name'] = error.connector_name
        
        # Extract API-specific details
        if isinstance(error, ExternalAPIException):
            if hasattr(error, 'api_name'):
                details['api_name'] = error.api_name
            if hasattr(error, 'status_code'):
                details['status_code'] = error.status_code
        
        # Extract rate limit details
        if isinstance(error, RateLimitException):
            if hasattr(error, 'retry_after'):
                details['retry_after'] = error.retry_after
        
        return details
    
    def _generate_user_message(self, error: Exception, error_type: str) -> str:
        """
        Generate a user-friendly error message.
        
        This method implements user-friendly error messages as specified in requirement 1.5.
        """
        # Use existing user message if available
        if isinstance(error, PromptFlowException) and error.user_message:
            return error.user_message
        
        # Generate user-friendly messages based on error type
        user_messages = {
            "agent_timeout": "The AI agent took too long to process your request. Please try a simpler query or try again later.",
            "infinite_loop": "The AI agent got stuck in a loop while processing your request. Please rephrase your query and try again.",
            "execution_cancelled": "Your request was cancelled due to system constraints. Please try again with a simpler request.",
            "agent_execution_error": "The AI agent encountered an error while processing your request. Please try rephrasing your query.",
            "tool_execution_error": "One of the tools encountered an error. Please check your integrations and try again.",
            "authentication_error": "Authentication failed. Please check your credentials and try logging in again.",
            "validation_error": "The input provided is invalid. Please check your data and try again.",
            "connector_error": "There was an issue with one of your integrations. Please check your configuration.",
            "external_api_error": "An external service is currently unavailable. Please try again later.",
            "rate_limit_error": "You've exceeded the rate limit. Please wait a moment before trying again.",
            "timeout_error": "The operation timed out. Please try again or contact support if the issue persists.",
            "connection_error": "Unable to connect to the service. Please check your internet connection.",
            "permission_error": "You don't have permission to perform this action. Please check your account settings.",
            "unexpected_error": "An unexpected error occurred. Please try again or contact support if the issue persists."
        }
        
        return user_messages.get(error_type, "An error occurred while processing your request. Please try again.")
    
    def _generate_suggestions(self, error: Exception, error_type: str) -> List[str]:
        """
        Generate helpful suggestions based on the error type.
        
        This method implements suggested actions as specified in requirement 1.5.
        """
        # Use existing suggestions if available
        if isinstance(error, PromptFlowException) and error.recovery_suggestions:
            return error.recovery_suggestions
        
        # Generate suggestions based on error type
        suggestions_map = {
            "agent_timeout": [
                "Try breaking down your request into smaller, simpler tasks",
                "Reduce the complexity of your query",
                "Try again when system load is lower"
            ],
            "infinite_loop": [
                "Rephrase your request more specifically",
                "Break down complex tasks into simpler steps",
                "Avoid circular or contradictory instructions"
            ],
            "execution_cancelled": [
                "Try again with a simpler request",
                "Reduce the scope of your task",
                "Contact support if you need assistance"
            ],
            "agent_execution_error": [
                "Try rephrasing your request",
                "Check if all required information is provided",
                "Try again in a few moments"
            ],
            "tool_execution_error": [
                "Check your integration settings",
                "Verify your account permissions",
                "Try reconnecting your accounts"
            ],
            "authentication_error": [
                "Check your login credentials",
                "Verify your API keys are correct",
                "Try logging out and logging back in"
            ],
            "validation_error": [
                "Check your input format",
                "Ensure all required fields are provided",
                "Verify data types are correct"
            ],
            "connector_error": [
                "Check your integration configuration",
                "Verify your account is connected",
                "Try reconnecting the integration"
            ],
            "external_api_error": [
                "Check your internet connection",
                "Verify the external service is available",
                "Try again in a few moments"
            ],
            "rate_limit_error": [
                "Wait before making another request",
                "Reduce the frequency of your requests",
                "Consider upgrading your plan if available"
            ],
            "timeout_error": [
                "Try a simpler request",
                "Check your internet connection",
                "Try again later"
            ],
            "connection_error": [
                "Check your internet connection",
                "Verify firewall settings",
                "Try again in a few moments"
            ],
            "permission_error": [
                "Check your account permissions",
                "Contact your administrator",
                "Verify you have access to the required resources"
            ],
            "unexpected_error": [
                "Try again in a few moments",
                "Contact support if the issue persists",
                "Check system status page"
            ]
        }
        
        return suggestions_map.get(error_type, ["Try again later", "Contact support if the issue persists"])
    
    def _generate_recovery_actions(self, error: Exception, error_type: str) -> List[Dict[str, Any]]:
        """
        Generate specific recovery actions with instructions.
        
        This method provides actionable recovery steps for users.
        """
        recovery_actions = []
        
        if error_type == "authentication_error":
            recovery_actions.append({
                "action": "reauth",
                "title": "Re-authenticate",
                "description": "Log out and log back in to refresh your authentication",
                "url": "/auth/login"
            })
        
        elif error_type == "tool_execution_error" or error_type == "connector_error":
            # Extract tool/connector name if available
            tool_name = None
            if hasattr(error, 'tool_name'):
                tool_name = error.tool_name
            elif hasattr(error, 'connector_name'):
                tool_name = error.connector_name
            
            if tool_name:
                recovery_actions.append({
                    "action": "reconnect",
                    "title": f"Reconnect {tool_name.replace('_', ' ').title()}",
                    "description": f"Reconnect your {tool_name.replace('_', ' ')} integration",
                    "url": f"/integrations/{tool_name}"
                })
        
        elif error_type == "rate_limit_error":
            retry_after = 60  # Default
            if hasattr(error, 'retry_after'):
                retry_after = error.retry_after
            
            recovery_actions.append({
                "action": "wait",
                "title": "Wait and Retry",
                "description": f"Wait {retry_after} seconds before trying again",
                "wait_seconds": retry_after
            })
        
        elif error_type in ["agent_timeout", "infinite_loop"]:
            recovery_actions.append({
                "action": "simplify",
                "title": "Simplify Request",
                "description": "Try breaking down your request into smaller parts",
                "example": "Instead of 'analyze all data and create reports', try 'show me the sales data first'"
            })
        
        return recovery_actions
    
    def _determine_retry_info(self, error: Exception) -> tuple[bool, Optional[int]]:
        """
        Determine if the error is retryable and when to retry.
        
        Returns:
            Tuple of (retryable, retry_after_seconds)
        """
        # Check if it's a PromptFlowException with retry info
        if isinstance(error, PromptFlowException):
            retryable = error.retryable
            retry_after = None
            
            if isinstance(error, RateLimitException) and hasattr(error, 'retry_after'):
                retry_after = error.retry_after
            
            return retryable, retry_after
        
        # Default retry logic for other exceptions
        retryable_types = [
            ConnectionError, TimeoutError, OSError
        ]
        
        retryable = any(isinstance(error, exc_type) for exc_type in retryable_types)
        return retryable, None
    
    def _determine_severity(self, error: Exception) -> str:
        """Determine the severity level of the error."""
        if isinstance(error, PromptFlowException):
            return error.severity.value if hasattr(error.severity, 'value') else str(error.severity)
        
        # Default severity mapping
        severity_map = {
            AuthenticationException: "high",
            PermissionError: "high",
            AgentExecutionError: "medium",
            ToolExecutionError: "medium",
            ValidationException: "low",
            RateLimitException: "medium",
            TimeoutException: "medium"
        }
        
        for exc_type, severity in severity_map.items():
            if isinstance(error, exc_type):
                return severity
        
        return "medium"  # Default
    
    async def _format_response(self, react_error: ReactError) -> Dict[str, Any]:
        """
        Format the ReactError into a comprehensive response.
        
        This method implements comprehensive error response formatting as specified in requirement 3.4.
        """
        response = {
            "error": True,
            "error_type": react_error.error_type,
            "error_code": react_error.error_code,
            "message": react_error.message,
            "user_message": react_error.user_message,
            "details": react_error.details,
            "suggestions": react_error.suggestions,
            "recovery_actions": react_error.recovery_actions,
            "retryable": react_error.retryable,
            "severity": react_error.severity,
            "category": react_error.category,
            "timestamp": react_error.timestamp.isoformat()
        }
        
        # Add optional fields if present
        if react_error.session_id:
            response["session_id"] = react_error.session_id
        
        if react_error.request_id:
            response["request_id"] = react_error.request_id
        
        if react_error.retry_after:
            response["retry_after"] = react_error.retry_after
        
        # Add reasoning trace if available
        if react_error.reasoning_trace:
            response["reasoning_trace"] = [
                {
                    "step_number": step.step_number,
                    "step_type": step.step_type.value if hasattr(step.step_type, 'value') else str(step.step_type),
                    "content": step.thought or step.observation or "",
                    "timestamp": step.timestamp.isoformat() if hasattr(step.timestamp, 'isoformat') else str(step.timestamp)
                }
                for step in react_error.reasoning_trace
            ]
        
        # Add failed tool calls if available
        if react_error.failed_tool_calls:
            response["failed_tool_calls"] = [
                {
                    "id": call.id,
                    "tool_name": call.tool_name,
                    "parameters": call.parameters,
                    "error": call.error,
                    "status": call.status.value if hasattr(call.status, 'value') else str(call.status),
                    "timestamp": call.started_at.isoformat() if hasattr(call.started_at, 'isoformat') else str(call.started_at)
                }
                for call in react_error.failed_tool_calls
            ]
        
        # Add context if available
        if react_error.context:
            response["context"] = react_error.context
        
        return response
    
    async def _log_error(self, react_error: ReactError, context: Optional[Dict[str, Any]]):
        """Log the error with appropriate level and context."""
        log_data = {
            "error_code": react_error.error_code,
            "error_type": react_error.error_type,
            "category": react_error.category,
            "severity": react_error.severity,
            "session_id": react_error.session_id,
            "request_id": react_error.request_id,
            "retryable": react_error.retryable,
            "context": context or {}
        }
        
        log_message = f"ReactError {react_error.error_code}: {react_error.message}"
        
        if react_error.severity == "critical":
            logger.critical(log_message, extra=log_data)
        elif react_error.severity == "high":
            logger.error(log_message, extra=log_data)
        elif react_error.severity == "medium":
            logger.warning(log_message, extra=log_data)
        else:
            logger.info(log_message, extra=log_data)
    
    async def _create_fallback_error_response(
        self,
        error: Exception,
        session_id: Optional[str],
        request_id: Optional[str]
    ) -> Dict[str, Any]:
        """Create a fallback error response when formatting fails."""
        return {
            "error": True,
            "error_type": "formatting_error",
            "error_code": f"REACT_FORMAT_ERROR_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "message": "Error formatting failed",
            "user_message": "An error occurred while processing your request. Please try again.",
            "details": {
                "original_error": str(error),
                "error_class": type(error).__name__
            },
            "suggestions": [
                "Try again in a few moments",
                "Contact support if the issue persists"
            ],
            "recovery_actions": [],
            "retryable": True,
            "severity": "high",
            "category": "system",
            "session_id": session_id,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global error formatter instance
react_error_formatter = ReactErrorFormatter()


async def format_react_error(
    error: Exception,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    reasoning_trace: Optional[List[ReasoningStep]] = None,
    failed_tool_calls: Optional[List[ToolCall]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for formatting ReAct agent errors.
    
    Args:
        error: The exception that occurred
        session_id: Session ID where error occurred
        request_id: Request ID for tracking
        reasoning_trace: Reasoning steps before error
        failed_tool_calls: Tool calls that failed
        context: Additional context about the error
        
    Returns:
        Comprehensive error response dictionary
    """
    return await react_error_formatter.format_error_response(
        error, session_id, request_id, reasoning_trace, failed_tool_calls, context
    )