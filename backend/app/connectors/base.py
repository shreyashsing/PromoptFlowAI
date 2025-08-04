"""
Base connector interface and abstract classes.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
try:
    import jsonschema
    from jsonschema import ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    ValidationError = ValueError

from app.models.connector import ConnectorResult, AuthRequirements, ConnectorExecutionContext
from app.core.exceptions import ConnectorException, ValidationException, AuthenticationException


logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.
    
    This defines the standard interface that all connectors must implement
    to ensure consistency and type safety across the platform.
    """
    
    def __init__(self):
        self._name = self._get_connector_name()
        self._description = self._get_connector_description()
        self._schema = self._define_schema()
        self._category = self._get_category()
    
    @property
    def name(self) -> str:
        """Unique name for the connector."""
        return self._name
    
    @property
    def description(self) -> str:
        """Human-readable description of the connector's functionality."""
        return self._description
    
    @property
    def schema(self) -> Dict[str, Any]:
        """JSON schema defining the connector's input parameters."""
        return self._schema
    
    @property
    def category(self) -> str:
        """Category of the connector for organization."""
        return self._category
    
    def _get_connector_name(self) -> str:
        """Get the connector name from class name."""
        class_name = self.__class__.__name__
        if class_name.endswith('Connector'):
            return class_name[:-9].lower()  # Remove 'Connector' suffix
        return class_name.lower()
    
    def _get_connector_description(self) -> str:
        """Get connector description from docstring or generate default."""
        return self.__doc__.strip() if self.__doc__ else f"{self.name} connector"
    
    def _get_category(self) -> str:
        """Get connector category. Override in subclasses."""
        return "general"
    
    @abstractmethod
    def _define_schema(self) -> Dict[str, Any]:
        """
        Define the JSON schema for this connector's parameters.
        Must be implemented by subclasses.
        """
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
    async def get_auth_requirements(self) -> AuthRequirements:
        """
        Get authentication requirements for this connector.
        
        Returns:
            AuthRequirements object describing needed authentication
        """
        pass
    
    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate input parameters against the connector's schema.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if parameters are valid
            
        Raises:
            ValidationException: If parameters are invalid
        """
        if not HAS_JSONSCHEMA:
            # Basic validation without jsonschema
            schema_props = self.schema.get("properties", {})
            required_fields = self.schema.get("required", [])
            
            # Check required fields
            for field in required_fields:
                if field not in params:
                    raise ValidationException(f"Missing required parameter: {field}")
            
            # Basic type checking
            for field, value in params.items():
                if field in schema_props:
                    expected_type = schema_props[field].get("type")
                    if expected_type == "string" and not isinstance(value, str):
                        raise ValidationException(f"Parameter {field} must be a string")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        raise ValidationException(f"Parameter {field} must be a number")
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        raise ValidationException(f"Parameter {field} must be a boolean")
            
            return True
        
        try:
            jsonschema.validate(params, self.schema)
            return True
        except ValidationError as e:
            raise ValidationException(f"Parameter validation failed for {self.name}: {e.message}")
    
    async def validate_auth(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Validate authentication tokens for this connector.
        
        Args:
            auth_tokens: Authentication tokens/credentials
            
        Returns:
            True if authentication is valid
            
        Raises:
            AuthenticationException: If authentication is invalid
        """
        auth_req = await self.get_auth_requirements()
        
        if auth_req.type == "none":
            return True
        
        # Check required auth fields
        for field in auth_req.fields.keys():
            if field not in auth_tokens:
                raise AuthenticationException(f"Missing required auth field: {field}")
        
        return await self.test_connection(auth_tokens)
    
    async def test_connection(self, auth_tokens: Dict[str, str]) -> bool:
        """
        Test if the connector can successfully connect with provided authentication.
        Default implementation returns True. Override in subclasses for actual testing.
        
        Args:
            auth_tokens: Authentication tokens/credentials
            
        Returns:
            True if connection successful, False otherwise
        """
        return True
    
    async def execute_with_retry(
        self, 
        params: Dict[str, Any], 
        context: ConnectorExecutionContext,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> ConnectorResult:
        """
        Execute connector with automatic retry logic.
        
        Args:
            params: Input parameters for the connector
            context: Execution context
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            ConnectorResult from successful execution
            
        Raises:
            ConnectorException: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Filter out auth-related parameters that shouldn't be in connector schemas
                filtered_params = self._filter_auth_parameters(params)
                
                # Validate parameters before execution
                await self.validate_params(filtered_params)
                
                # Validate authentication if required
                auth_req = await self.get_auth_requirements()
                if auth_req.type != "none":
                    await self.validate_auth(context.auth_tokens)
                
                # Execute the connector with filtered parameters
                result = await self.execute(filtered_params, context)
                
                if result.success:
                    return result
                else:
                    # If execution failed but didn't raise exception, treat as error
                    last_error = ConnectorException(f"Connector execution failed: {result.error}")
                    
            except (ConnectorException, ValidationException, AuthenticationException) as e:
                last_error = e
                logger.warning(f"Connector {self.name} attempt {attempt + 1} failed: {str(e)}")
                
                # Don't retry validation or auth errors
                if isinstance(e, (ValidationException, AuthenticationException)):
                    raise e
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    
            except Exception as e:
                last_error = ConnectorException(f"Unexpected error in {self.name}: {str(e)}")
                logger.error(f"Unexpected error in connector {self.name}: {str(e)}")
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
        
        # All retries failed
        raise last_error or ConnectorException(f"Connector {self.name} failed after {max_retries} retries")
    
    def _filter_auth_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out authentication-related parameters that shouldn't be in connector schemas.
        
        These parameters are handled separately through the ConnectorExecutionContext.auth_tokens
        and should not be passed as regular connector parameters.
        
        Args:
            params: Original parameters dictionary
            
        Returns:
            Filtered parameters dictionary without auth-related fields
        """
        # List of parameter names that should be filtered out
        auth_param_names = {
            'auth', 'api_key', 'token', 'access_token', 'refresh_token',
            'client_id', 'client_secret', 'oauth_token', 'bearer_token',
            'authorization', 'credentials', 'key', 'secret'
        }
        
        # Filter out auth parameters
        filtered = {k: v for k, v in params.items() if k.lower() not in auth_param_names}
        
        # Log if any parameters were filtered
        filtered_keys = set(params.keys()) - set(filtered.keys())
        if filtered_keys:
            logger.info(f"Filtered auth parameters from {self.name}: {filtered_keys}")
        
        return filtered

    def get_parameter_hints(self) -> Dict[str, str]:
        """
        Get human-readable hints for connector parameters.
        Override in subclasses to provide helpful parameter descriptions.
        
        Returns:
            Dictionary mapping parameter names to description hints
        """
        hints = {}
        if "properties" in self.schema:
            for param_name, param_schema in self.schema["properties"].items():
                if "description" in param_schema:
                    hints[param_name] = param_schema["description"]
        return hints
    
    def get_example_params(self) -> Dict[str, Any]:
        """
        Get example parameters for this connector.
        Override in subclasses to provide helpful examples.
        
        Returns:
            Dictionary with example parameter values
        """
        return {}
    
    async def cleanup(self, context: ConnectorExecutionContext) -> None:
        """
        Cleanup resources after connector execution.
        Override in subclasses if cleanup is needed.
        
        Args:
            context: Execution context
        """
        pass