"""
Custom exceptions for the PromptFlow AI platform.
"""


class PromptFlowException(Exception):
    """Base exception for PromptFlow AI platform."""
    pass


class ConnectorException(PromptFlowException):
    """Exception raised by connector operations."""
    pass


class AuthenticationException(PromptFlowException):
    """Exception raised for authentication failures."""
    pass


class ValidationException(PromptFlowException):
    """Exception raised for validation errors."""
    pass


class WorkflowException(PromptFlowException):
    """Exception raised during workflow execution."""
    pass


class RAGException(PromptFlowException):
    """Exception raised by RAG system operations."""
    pass


class RAGError(RAGException):
    """Exception raised for general RAG system errors."""
    pass


class EmbeddingError(RAGException):
    """Exception raised for embedding generation errors."""
    pass