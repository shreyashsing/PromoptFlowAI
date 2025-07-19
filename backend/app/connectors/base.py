"""
Base connector interface and abstract classes.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.models.connector import ConnectorResult, AuthRequirements, ConnectorExecutionContext


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.
    
    This defines the standard interface that all connectors must implement
    to ensure consistency and type safety across the platform.
    """
    
    def __init__(self):
        self.name = self.__class__.__name__.lower().replace('connector', '')
        self.description = self.__doc__ or f"{self.name} connector"
        self.schema = self._define_schema()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for the connector."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the connector's functionality."""
        pass
    
    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """JSON schema defining the connector's input parameters."""
        pass
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute the connector with given parameters and context.
        
        Args:
            params: Input parameters for the connector
            context: Execution context including auth tokens and previous results
            
        Returns:
            ConnectorResult with success status, data, and any errors
        """
        pass
    
    @abstractmethod
    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate input parameters against the connector's schema.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get authentication requirements for this connector.
        
        Returns:
            AuthRequirements object describing needed authentication
        """
        pass
    
    def _define_schema(self) -> Dict[str, Any]:
        """
        Define the JSON schema for this connector's parameters.
        Override this method in subclasses to define specific schemas.
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test if the connector can successfully connect with provided authentication.
        
        Args:
            auth_tokens: Authentication tokens/credentials
            
        Returns:
            True if connection successful, False otherwise
        """
        return True