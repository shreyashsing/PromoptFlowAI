"""
Base connector interface and abstract classes.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
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
        Filter out authentication-related and AI metadata parameters that shouldn't be in connector schemas.
        
        These parameters are handled separately:
        - Auth parameters: through ConnectorExecutionContext.auth_tokens
        - AI metadata: internal system metadata for debugging/transparency
        
        Args:
            params: Original parameters dictionary
            
        Returns:
            Filtered parameters dictionary without auth-related or AI metadata fields
        """
        # List of parameter names that should be filtered out
        auth_param_names = {
            'auth', 'api_key', 'token', 'access_token', 'refresh_token',
            'client_id', 'client_secret', 'oauth_token', 'bearer_token',
            'authorization', 'credentials', 'key', 'secret'
        }
        
        # AI metadata fields that should be filtered out
        ai_metadata_names = {
            '_ai_confidence', '_ai_explanation', '_ai_generated', '_ai_intent',
            '_code_complexity', '_decision_reasoning', '_risk_assessment', '_validation',
            '_ai_reasoning', '_ai_context', '_ai_metadata', '_ai_debug'
        }
        
        # Combine all fields to filter
        filtered_param_names = auth_param_names | ai_metadata_names
        
        # Filter out auth and AI metadata parameters
        filtered = {k: v for k, v in params.items() if k.lower() not in filtered_param_names}
        
        # Log if any parameters were filtered
        filtered_keys = set(params.keys()) - set(filtered.keys())
        if filtered_keys:
            auth_filtered = [k for k in filtered_keys if k.lower() in auth_param_names]
            ai_filtered = [k for k in filtered_keys if k.lower() in ai_metadata_names]
            
            if auth_filtered:
                logger.info(f"Filtered auth parameters from {self.name}: {auth_filtered}")
            if ai_filtered:
                logger.debug(f"Filtered AI metadata from {self.name}: {ai_filtered}")
        
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
    
    # Enhanced AI-friendly metadata methods
    def get_capabilities(self) -> List[str]:
        """
        Get connector capabilities based on schema and operations.
        Override in subclasses for more specific capabilities.
        
        Returns:
            List of capability strings
        """
        capabilities = []
        schema_props = self.schema.get("properties", {})
        
        # Infer capabilities from schema
        if "action" in schema_props or "operation" in schema_props:
            action_enum = schema_props.get("action", {}).get("enum", [])
            operation_enum = schema_props.get("operation", {}).get("enum", [])
            operations = action_enum + operation_enum
            
            # Map operations to capabilities
            if any(op in operations for op in ["send", "create", "post", "upload", "write"]):
                capabilities.append("write")
            if any(op in operations for op in ["get", "read", "list", "fetch", "download"]):
                capabilities.append("read")
            if any(op in operations for op in ["update", "modify", "edit", "patch"]):
                capabilities.append("update")
            if any(op in operations for op in ["delete", "remove", "trash"]):
                capabilities.append("delete")
            if any(op in operations for op in ["search", "find", "query"]):
                capabilities.append("search")
        
        # Add authentication if auth is required
        if hasattr(self, 'get_auth_requirements'):
            try:
                # Skip async check for now to avoid warnings
                # This will be properly handled when the connector is actually used
                pass
            except:
                pass
        
        return capabilities or ["general"]
    
    def get_use_cases(self) -> List[Dict[str, Any]]:
        """
        Generate use cases based on connector operations and schema.
        Override in subclasses for more specific use cases.
        
        Returns:
            List of use case dictionaries
        """
        use_cases = []
        schema_props = self.schema.get("properties", {})
        
        # Get operations from schema
        operations = []
        if "action" in schema_props:
            operations = schema_props["action"].get("enum", [])
        elif "operation" in schema_props:
            operations = schema_props["operation"].get("enum", [])
        
        # Generate use cases based on operations
        operation_templates = {
            "send": {
                "title": "Send Data",
                "description": f"Send data using {self.name}",
                "category": "communication",
                "complexity": "simple"
            },
            "create": {
                "title": "Create Resource",
                "description": f"Create new resources in {self.name}",
                "category": "data_processing",
                "complexity": "simple"
            },
            "read": {
                "title": "Read Data",
                "description": f"Retrieve data from {self.name}",
                "category": "data_processing",
                "complexity": "simple"
            },
            "search": {
                "title": "Search Content",
                "description": f"Search for specific content in {self.name}",
                "category": "data_processing",
                "complexity": "intermediate"
            },
            "list": {
                "title": "List Items",
                "description": f"Get a list of items from {self.name}",
                "category": "data_processing",
                "complexity": "simple"
            },
            "update": {
                "title": "Update Data",
                "description": f"Modify existing data in {self.name}",
                "category": "data_processing",
                "complexity": "intermediate"
            },
            "delete": {
                "title": "Delete Data",
                "description": f"Remove data from {self.name}",
                "category": "data_processing",
                "complexity": "simple"
            }
        }
        
        # Generate use cases for available operations
        for operation in operations[:5]:  # Limit to first 5 operations
            template = operation_templates.get(operation.lower())
            if template:
                use_case = template.copy()
                use_case["example_prompts"] = [
                    f"{operation.title()} data using {self.name}",
                    f"Use {self.name} to {operation} information"
                ]
                use_cases.append(use_case)
        
        return use_cases
    
    def get_example_prompts(self) -> List[str]:
        """
        Generate example user prompts based on connector functionality.
        Override in subclasses for more specific prompts.
        
        Returns:
            List of example prompt strings
        """
        prompts = []
        schema_props = self.schema.get("properties", {})
        connector_name = self.name.replace("_", " ").title()
        
        # Get operations
        operations = []
        if "action" in schema_props:
            operations = schema_props["action"].get("enum", [])
        elif "operation" in schema_props:
            operations = schema_props["operation"].get("enum", [])
        
        # Generate prompts based on operations
        prompt_templates = {
            "send": f"Send a message using {connector_name}",
            "create": f"Create a new item in {connector_name}",
            "read": f"Get information from {connector_name}",
            "search": f"Search for content in {connector_name}",
            "list": f"Show me items from {connector_name}",
            "update": f"Update data in {connector_name}",
            "delete": f"Remove item from {connector_name}",
            "get": f"Retrieve data from {connector_name}",
            "fetch": f"Fetch information using {connector_name}"
        }
        
        for operation in operations[:3]:  # Limit to first 3 operations
            template = prompt_templates.get(operation.lower())
            if template:
                prompts.append(template)
        
        # Add generic prompts if no specific operations
        if not prompts:
            prompts = [
                f"Use {connector_name} to process data",
                f"Connect to {connector_name} and get information",
                f"Perform operations with {connector_name}"
            ]
        
        return prompts
    
    def get_parameter_hints(self) -> Dict[str, str]:
        """
        Get AI-friendly parameter hints from schema descriptions.
        Enhanced version that provides better hints for AI parameter generation.
        
        Returns:
            Dictionary mapping parameter names to AI-friendly hints
        """
        hints = {}
        schema_props = self.schema.get("properties", {})
        
        for param_name, param_schema in schema_props.items():
            description = param_schema.get("description", "")
            param_type = param_schema.get("type", "string")
            
            # Enhanced hints based on parameter patterns
            if param_name.lower() in ["action", "operation"]:
                enum_values = param_schema.get("enum", [])
                hints[param_name] = f"Choose operation: {', '.join(enum_values[:5])}{'...' if len(enum_values) > 5 else ''}"
            
            elif param_name.lower() in ["query", "search"]:
                hints[param_name] = "Convert natural language search to appropriate query format"
            
            elif param_name.lower() in ["to", "recipient", "email"]:
                hints[param_name] = "Extract email addresses from user request, validate format"
            
            elif param_name.lower() in ["subject", "title"]:
                hints[param_name] = "Generate descriptive title based on content or user intent"
            
            elif param_name.lower() in ["body", "content", "message"]:
                hints[param_name] = "Generate appropriate content based on user's message and context"
            
            elif param_name.lower() in ["id", "identifier"]:
                hints[param_name] = "Use ID from previous operations or user-provided identifier"
            
            elif param_type == "boolean":
                hints[param_name] = f"Boolean parameter: {description}"
            
            elif param_type == "integer":
                hints[param_name] = f"Numeric parameter: {description}"
            
            else:
                hints[param_name] = description or f"Parameter for {param_name}"
        
        return hints
    
    def get_ai_metadata(self) -> Dict[str, Any]:
        """
        Get comprehensive AI-friendly metadata for this connector.
        This is the main method AI agents should use to understand the connector.
        
        Returns:
            Dictionary with all AI-relevant metadata
        """
        return {
            "name": self.name,
            "display_name": self.name.replace("_", " ").title(),
            "description": self.description,
            "category": self.category,
            "capabilities": self.get_capabilities(),
            "use_cases": self.get_use_cases(),
            "example_prompts": self.get_example_prompts(),
            "parameter_hints": self.get_parameter_hints(),
            "schema": self.schema,
            "example_params": self.get_example_params(),
            "auth_required": self._requires_auth(),
            "supported_operations": self._get_supported_operations()
        }
    
    def _requires_auth(self) -> bool:
        """Check if connector requires authentication."""
        try:
            # Create a new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we can't use asyncio.run
                    return False  # Default to False for now
            except RuntimeError:
                pass
            
            auth_req = asyncio.run(self.get_auth_requirements())
            return auth_req.type != "none"
        except:
            return False
    
    def _get_supported_operations(self) -> List[str]:
        """Get list of supported operations from schema."""
        schema_props = self.schema.get("properties", {})
        
        if "action" in schema_props:
            return schema_props["action"].get("enum", [])
        elif "operation" in schema_props:
            return schema_props["operation"].get("enum", [])
        
        return []
    
    def generate_parameter_suggestions(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate parameter suggestions based on user prompt and context.
        Override in subclasses for connector-specific logic.
        
        Args:
            user_prompt: Natural language user request
            context: Additional context information
            
        Returns:
            Dictionary of suggested parameter values
        """
        suggestions = {}
        schema_props = self.schema.get("properties", {})
        prompt_lower = user_prompt.lower()
        
        # Basic parameter inference
        for param_name, param_schema in schema_props.items():
            param_type = param_schema.get("type", "string")
            
            # Action/operation inference
            if param_name.lower() in ["action", "operation"]:
                enum_values = param_schema.get("enum", [])
                for operation in enum_values:
                    if operation.lower() in prompt_lower:
                        suggestions[param_name] = operation
                        break
                else:
                    # Default to first operation if none found
                    if enum_values:
                        suggestions[param_name] = enum_values[0]
            
            # Boolean parameter inference
            elif param_type == "boolean":
                if any(word in prompt_lower for word in ["yes", "true", "enable", "on"]):
                    suggestions[param_name] = True
                elif any(word in prompt_lower for word in ["no", "false", "disable", "off"]):
                    suggestions[param_name] = False
            
            # Set defaults for required parameters
            elif param_name in self.schema.get("required", []):
                default_value = param_schema.get("default")
                if default_value is not None:
                    suggestions[param_name] = default_value
        
        return suggestions
    
    async def cleanup(self, context: ConnectorExecutionContext) -> None:
        """
        Cleanup resources after connector execution.
        Override in subclasses if cleanup is needed.
        
        Args:
            context: Execution context
        """
        pass