"""
Custom exceptions for the PromptFlow AI platform.
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class ErrorCategory(Enum):
    """Categories of errors for better classification and handling."""
    USER_INPUT = "user_input"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    CONNECTOR = "connector"
    WORKFLOW = "workflow"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"


class ErrorSeverity(Enum):
    """Severity levels for error classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromptFlowException(Exception):
    """Base exception for PromptFlow AI platform with enhanced error handling."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        recovery_suggestions: Optional[List[str]] = None,
        retryable: bool = False,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or self._generate_error_code()
        self.details = details or {}
        self.user_message = user_message or self._generate_user_message()
        self.recovery_suggestions = recovery_suggestions or []
        self.retryable = retryable
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()
    
    def _generate_error_code(self) -> str:
        """Generate a unique error code based on exception type and category."""
        class_name = self.__class__.__name__
        return f"{self.category.value.upper()}_{class_name.upper()}"
    
    def _generate_user_message(self) -> str:
        """Generate a user-friendly error message."""
        return "An error occurred while processing your request. Please try again."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "recovery_suggestions": self.recovery_suggestions,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat(),
            "original_exception": str(self.original_exception) if self.original_exception else None
        }


class ConnectorException(PromptFlowException):
    """Exception raised by connector operations."""
    
    def __init__(self, message: str, connector_name: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.CONNECTOR)
        kwargs.setdefault('retryable', True)
        self.connector_name = connector_name  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if connector_name:
            self.details['connector_name'] = connector_name
    
    def _generate_user_message(self) -> str:
        if self.connector_name:
            return f"There was an issue with the {self.connector_name} integration. Please check your configuration."
        return "There was an issue with one of your integrations. Please check your configuration."


class AuthenticationException(PromptFlowException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.AUTHENTICATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('recovery_suggestions', [
            "Please check your login credentials",
            "Verify your API keys are correct",
            "Try logging out and logging back in"
        ])
        super().__init__(message, **kwargs)
    
    def _generate_user_message(self) -> str:
        return "Authentication failed. Please check your credentials and try again."


class ValidationException(PromptFlowException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.VALIDATION)
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        self.field = field  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if field:
            self.details['field'] = field
    
    def _generate_user_message(self) -> str:
        if self.field:
            return f"Invalid value for {self.field}. Please check your input and try again."
        return "Invalid input provided. Please check your data and try again."


class WorkflowException(PromptFlowException):
    """Exception raised during workflow execution."""
    
    def __init__(self, message: str, workflow_id: str = None, node_id: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.WORKFLOW)
        kwargs.setdefault('retryable', True)
        self.workflow_id = workflow_id  # Set before calling super().__init__
        self.node_id = node_id  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if workflow_id:
            self.details['workflow_id'] = workflow_id
        if node_id:
            self.details['node_id'] = node_id
    
    def _generate_user_message(self) -> str:
        return "Your workflow encountered an error during execution. Please review the workflow and try again."


class RAGException(PromptFlowException):
    """Exception raised by RAG system operations."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.SYSTEM)
        kwargs.setdefault('retryable', True)
        super().__init__(message, **kwargs)


class RAGError(RAGException):
    """Exception raised for general RAG system errors."""
    
    def _generate_user_message(self) -> str:
        return "Unable to find relevant connectors for your request. Please try rephrasing your prompt."


class EmbeddingError(RAGException):
    """Exception raised for embedding generation errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.EXTERNAL_API)
        kwargs.setdefault('recovery_suggestions', [
            "Check your OpenAI API key configuration",
            "Verify your internet connection",
            "Try again in a few moments"
        ])
        super().__init__(message, **kwargs)
    
    def _generate_user_message(self) -> str:
        return "Unable to process your request due to an AI service issue. Please try again."


class AgentError(PromptFlowException):
    """Exception raised by conversational agent operations."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.SYSTEM)
        kwargs.setdefault('retryable', True)
        super().__init__(message, **kwargs)
    
    def _generate_user_message(self) -> str:
        return "The AI assistant encountered an error. Please try rephrasing your request."


class PlanningError(PromptFlowException):
    """Exception raised during workflow planning operations."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.SYSTEM)
        kwargs.setdefault('recovery_suggestions', [
            "Try rephrasing your request with more specific details",
            "Break down complex requests into simpler steps",
            "Check if all required integrations are available"
        ])
        super().__init__(message, **kwargs)
    
    def _generate_user_message(self) -> str:
        return "Unable to create a workflow plan for your request. Please try rephrasing with more details."


class TriggerException(PromptFlowException):
    """Exception raised by trigger system operations."""
    
    def __init__(self, message: str, trigger_id: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.SYSTEM)
        kwargs.setdefault('retryable', True)
        self.trigger_id = trigger_id  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if trigger_id:
            self.details['trigger_id'] = trigger_id
    
    def _generate_user_message(self) -> str:
        return "There was an issue with your workflow trigger. Please check the trigger configuration."


class ExternalAPIException(PromptFlowException):
    """Exception raised for external API errors."""
    
    def __init__(self, message: str, api_name: str = None, status_code: int = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.EXTERNAL_API)
        kwargs.setdefault('retryable', True)
        self.api_name = api_name  # Set before calling super().__init__
        self.status_code = status_code  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if api_name:
            self.details['api_name'] = api_name
        if status_code:
            self.details['status_code'] = status_code
    
    def _generate_user_message(self) -> str:
        if self.api_name:
            return f"Unable to connect to {self.api_name}. Please check your configuration and try again."
        return "Unable to connect to external service. Please try again later."


class RateLimitException(PromptFlowException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.RATE_LIMIT)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retryable', True)
        self.retry_after = retry_after  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if retry_after:
            self.details['retry_after'] = retry_after
    
    def _generate_user_message(self) -> str:
        if self.retry_after:
            return f"Rate limit exceeded. Please wait {self.retry_after} seconds before trying again."
        return "Rate limit exceeded. Please wait a moment before trying again."


class TimeoutException(PromptFlowException):
    """Exception raised for timeout errors."""
    
    def __init__(self, message: str, timeout_duration: float = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.TIMEOUT)
        kwargs.setdefault('retryable', True)
        self.timeout_duration = timeout_duration  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if timeout_duration:
            self.details['timeout_duration'] = timeout_duration
    
    def _generate_user_message(self) -> str:
        return "The operation timed out. Please try again or contact support if the issue persists."


class DatabaseException(PromptFlowException):
    """Exception raised for database errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.DATABASE)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('retryable', True)
        super().__init__(message, **kwargs)
    
    def _generate_user_message(self) -> str:
        return "A database error occurred. Please try again or contact support if the issue persists."


class ConfigurationException(PromptFlowException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.CONFIGURATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        self.config_key = config_key  # Set before calling super().__init__
        super().__init__(message, **kwargs)
        if config_key:
            self.details['config_key'] = config_key
    
    def _generate_user_message(self) -> str:
        return "Configuration error detected. Please contact support for assistance."