"""
Connector-to-Tool Adapter for converting existing connectors to LangGraph tools.
"""
import logging
from typing import Dict, Any, Optional, Callable, Union, List, Type
import json
from datetime import datetime
import asyncio
import concurrent.futures
from contextvars import ContextVar

from langchain.tools import Tool
from pydantic import BaseModel, Field, create_model, ValidationError

from app.connectors.base import BaseConnector, ConnectorExecutionContext
from app.models.connector import ConnectorResult
from app.services.auth_context_manager import get_auth_context_manager
from app.core.exceptions import (
    ToolExecutionError, AuthenticationException, ValidationException,
    ConnectorException, ExternalAPIException, RateLimitException
)

logger = logging.getLogger(__name__)

# Context variables for passing user context to tools
_user_context: ContextVar[Dict[str, Any]] = ContextVar('user_context', default={})


class ConnectorToolAdapter:
    """
    Adapts existing connectors to work as LangGraph tools.
    
    This class implements the Connector-to-Tool Adapter requirements from 2.2:
    - Schema conversion from connector format to LangGraph tool format
    - Parameter validation and type conversion logic
    - Wrapping connectors as LangGraph tools
    """
    
    def __init__(self, connector_name: str, connector_class: Type[BaseConnector]):
        self.connector_name = connector_name
        self.connector_class = connector_class
        self.connector_instance: Optional[BaseConnector] = None
        self._tool_schema: Optional[Dict[str, Any]] = None
        self._pydantic_model: Optional[Type[BaseModel]] = None
    
    @classmethod
    def set_user_context(cls, user_id: str, user_session: Dict[str, Any], auth_context_manager: Any) -> None:
        """Set the user context for the current execution."""
        context = {
            "user_id": user_id,
            "user_session": user_session,
            "auth_context_manager": auth_context_manager
        }
        _user_context.set(context)
    
    @classmethod
    def get_user_context(cls) -> Dict[str, Any]:
        """Get the current user context."""
        return _user_context.get({})
    
    async def to_langchain_tool(self) -> Tool:
        """
        Convert the connector to a LangChain Tool.
        
        This method implements the schema conversion requirement from 2.2:
        - Converts connector schema to LangGraph tool format
        - Creates proper tool function with parameter validation
        - Handles type conversion and error handling
        """
        try:
            # Get connector instance
            if not self.connector_instance:
                self.connector_instance = self.connector_class()
            
            # Convert connector schema to tool schema
            tool_schema = await self._convert_schema_to_tool_format()
            
            # Create Pydantic model for parameter validation
            pydantic_model = self._create_pydantic_model()
            
            # Create async tool function with comprehensive error handling and recovery
            async def async_tool_func(query: str, **kwargs) -> str:
                """
                Async tool function that will be called by the agent with validated parameters.
                
                This function implements comprehensive error handling as specified in requirement 1.5
                and authentication token injection mechanism from 2.3.
                """
                execution_start_time = datetime.utcnow()
                retry_count = 0
                max_retries = 3
                
                # Extract user context from context variable (set by ReAct agent) - do this once
                user_context = self.__class__.get_user_context()
                user_id = user_context.get("user_id", "system")
                user_session = user_context.get("user_session", {})
                auth_context_manager = user_context.get("auth_context_manager")
                
                while retry_count <= max_retries:
                    try:
                        
                        # Log the context for debugging
                        logger.debug(f"Tool {self.connector_name} executing with user_id: {user_id}")
                        
                        # Parse and validate parameters with enhanced error handling
                        try:
                            validated_params = await self._parse_and_validate_parameters(query, pydantic_model)
                        except ValidationError as e:
                            # Handle parameter validation errors with detailed feedback
                            error_details = self._extract_validation_error_details(e)
                            error_msg = f"Parameter validation failed for {self.connector_name}: {error_details['message']}"
                            logger.error(error_msg, extra={
                                "tool_name": self.connector_name,
                                "user_id": user_id,
                                "validation_errors": error_details['errors'],
                                "input_query": query[:200]  # Truncate for logging
                            })
                            return await self._format_validation_error_response(error_details)
                        
                        # Create secure execution context with enhanced error handling
                        try:
                            auth_manager = auth_context_manager or await get_auth_context_manager()
                            context = await auth_manager.create_secure_execution_context(
                                user_id=user_id,
                                connector_name=self.connector_name
                            )
                        except AuthenticationException as e:
                            # Handle authentication failures with recovery suggestions
                            return await self._handle_authentication_error(e, user_id, auth_context_manager)
                        
                        # Execute connector with comprehensive error handling and timeout
                        try:
                            # Set execution timeout based on tool metadata
                            timeout_seconds = self._get_tool_timeout()
                            result = await asyncio.wait_for(
                                self.connector_instance.execute(validated_params, context),
                                timeout=timeout_seconds
                            )
                            
                            # Log successful execution
                            execution_time = (datetime.utcnow() - execution_start_time).total_seconds()
                            logger.info(f"Tool '{self.connector_name}' executed successfully", extra={
                                "tool_name": self.connector_name,
                                "user_id": user_id,
                                "execution_time": execution_time,
                                "retry_count": retry_count,
                                "success": True
                            })
                            
                            # Format result for the agent
                            return await self._format_result_for_agent(result)
                            
                        except asyncio.TimeoutError:
                            # Handle execution timeout with retry logic
                            if retry_count < max_retries:
                                retry_count += 1
                                backoff_delay = min(2 ** retry_count, 10)  # Exponential backoff, max 10 seconds
                                logger.warning(f"Tool '{self.connector_name}' timed out after {timeout_seconds}s, retrying ({retry_count}/{max_retries}) in {backoff_delay}s", extra={
                                    "tool_name": self.connector_name,
                                    "user_id": user_id,
                                    "timeout_seconds": timeout_seconds,
                                    "retry_count": retry_count,
                                    "backoff_delay": backoff_delay
                                })
                                await asyncio.sleep(backoff_delay)
                                continue  # Retry the operation
                            else:
                                # Max retries exceeded, return timeout error
                                return await self._handle_timeout_error(timeout_seconds, retry_count, max_retries, user_id)
                        
                        except (ConnectorException, ExternalAPIException, RateLimitException) as e:
                            # Handle expected connector errors with retry logic
                            return await self._handle_connector_error(e, retry_count, max_retries, user_id)
                        
                        except Exception as e:
                            # Handle unexpected errors with graceful degradation
                            return await self._handle_unexpected_error(e, retry_count, max_retries, user_id)
                    
                    except Exception as critical_error:
                        # Handle critical errors that prevent retry logic
                        logger.critical(f"Critical error in tool '{self.connector_name}': {critical_error}", extra={
                            "tool_name": self.connector_name,
                            "user_id": user_context.get("user_id", "unknown"),
                            "error_type": type(critical_error).__name__,
                            "retry_count": retry_count
                        })
                        return await self._format_critical_error_response(critical_error)
                
                # If we've exhausted all retries
                return await self._format_max_retries_exceeded_response(max_retries)
            
            # Create synchronous wrapper function for LangChain Tool compatibility
            def sync_tool_func(query: str, **kwargs) -> str:
                """
                Synchronous wrapper function that handles the async execution.
                
                This fixes the coroutine issue by properly executing the async function
                in the current event loop or creating a new one if needed.
                """
                try:
                    # Try to get the current event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're already in an event loop, we need to run in a thread
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                lambda: asyncio.run(async_tool_func(query, **kwargs))
                            )
                            return future.result(timeout=300)  # 5 minute timeout
                    else:
                        # If no event loop is running, we can run directly
                        return loop.run_until_complete(async_tool_func(query, **kwargs))
                except RuntimeError:
                    # No event loop exists, create a new one
                    return asyncio.run(async_tool_func(query, **kwargs))
                except Exception as e:
                    logger.error(f"Error in sync wrapper for tool '{self.connector_name}': {e}")
                    return f"Error executing {self.connector_name}: {str(e)}"
            
            # Create LangChain Tool with synchronous function
            tool = Tool(
                name=self.connector_name,
                description=tool_schema.get("description", f"Execute {self.connector_name} connector"),
                func=sync_tool_func  # Now using synchronous wrapper
            )
            
            logger.debug(f"Successfully converted connector '{self.connector_name}' to LangChain tool")
            return tool
            
        except Exception as e:
            logger.error(f"Failed to convert connector {self.connector_name} to tool: {e}")
            raise ToolExecutionError(f"Tool conversion failed: {str(e)}")
    
    async def _convert_schema_to_tool_format(self) -> Dict[str, Any]:
        """
        Convert connector schema to LangGraph tool format.
        
        This method implements the schema conversion requirement from 2.2.
        """
        try:
            if not self.connector_instance:
                self.connector_instance = self.connector_class()
            
            # Get connector schema
            connector_schema = self.connector_instance.schema
            
            # Get authentication requirements
            auth_requirements = await self.connector_instance.get_auth_requirements()
            
            # Convert to tool format
            tool_schema = {
                "name": self.connector_name,
                "description": self.connector_instance.description,
                "parameters": self._convert_json_schema_to_tool_params(connector_schema),
                "auth_required": auth_requirements.type.value != "none" if hasattr(auth_requirements.type, 'value') else str(auth_requirements.type) != "none",
                "auth_type": auth_requirements.type.value if hasattr(auth_requirements.type, 'value') else str(auth_requirements.type),
                "required_fields": connector_schema.get("required", []),
                "optional_fields": [
                    field for field in connector_schema.get("properties", {}).keys()
                    if field not in connector_schema.get("required", [])
                ]
            }
            
            self._tool_schema = tool_schema
            logger.debug(f"Converted schema for tool '{self.connector_name}': {tool_schema}")
            return tool_schema
            
        except Exception as e:
            logger.error(f"Failed to convert schema for connector {self.connector_name}: {e}")
            # Return minimal schema on error
            return {
                "name": self.connector_name,
                "description": f"{self.connector_name} connector",
                "parameters": {},
                "auth_required": False,
                "auth_type": "none",
                "required_fields": [],
                "optional_fields": []
            }

    def _convert_json_schema_to_tool_params(self, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert JSON schema properties to tool parameter format.
        
        This method handles the detailed schema conversion logic.
        """
        properties = json_schema.get("properties", {})
        converted_params = {}
        
        for param_name, param_schema in properties.items():
            converted_param = {
                "type": param_schema.get("type", "string"),
                "description": param_schema.get("description", f"Parameter {param_name}"),
            }
            
            # Handle additional schema properties
            if "enum" in param_schema:
                converted_param["enum"] = param_schema["enum"]
            if "default" in param_schema:
                converted_param["default"] = param_schema["default"]
            if "minimum" in param_schema:
                converted_param["minimum"] = param_schema["minimum"]
            if "maximum" in param_schema:
                converted_param["maximum"] = param_schema["maximum"]
            if "items" in param_schema:
                converted_param["items"] = param_schema["items"]
            if "format" in param_schema:
                converted_param["format"] = param_schema["format"]
            
            converted_params[param_name] = converted_param
        
        return converted_params

    def _create_pydantic_model(self) -> Type[BaseModel]:
        """
        Create a Pydantic model for parameter validation.
        
        This method implements the parameter validation requirement from 2.2.
        """
        try:
            if not self.connector_instance:
                self.connector_instance = self.connector_class()
            
            connector_schema = self.connector_instance.schema
            properties = connector_schema.get("properties", {})
            required_fields = connector_schema.get("required", [])
            
            # Build Pydantic field definitions
            field_definitions = {}
            
            for param_name, param_schema in properties.items():
                field_type = self._json_type_to_python_type(param_schema)
                field_kwargs = {
                    "description": param_schema.get("description", f"Parameter {param_name}")
                }
                
                # Handle default values
                if "default" in param_schema:
                    field_kwargs["default"] = param_schema["default"]
                elif param_name not in required_fields:
                    field_kwargs["default"] = None
                
                # Create Field with validation
                if param_name in required_fields and "default" not in param_schema:
                    field_definitions[param_name] = (field_type, Field(**field_kwargs))
                else:
                    field_definitions[param_name] = (Optional[field_type], Field(**field_kwargs))
            
            # Create dynamic Pydantic model with proper base class
            model_name = f"{self.connector_name.title().replace('_', '')}Parameters"
            
            # Create the model with explicit BaseModel inheritance
            pydantic_model = create_model(
                model_name,
                __base__=BaseModel,
                **field_definitions
            )
            
            self._pydantic_model = pydantic_model
            logger.debug(f"Created Pydantic model for tool '{self.connector_name}': {model_name}")
            return pydantic_model
            
        except Exception as e:
            logger.error(f"Failed to create Pydantic model for connector {self.connector_name}: {e}")
            # Return basic model on error with explicit BaseModel inheritance
            return create_model(
                f"{self.connector_name.title().replace('_', '')}Parameters",
                __base__=BaseModel
            )

    def _json_type_to_python_type(self, param_schema: Dict[str, Any]) -> Type:
        """
        Convert JSON schema types to Python types for Pydantic.
        
        This method implements the type conversion logic requirement from 2.2.
        """
        json_type = param_schema.get("type", "string")
        
        if json_type == "string":
            return str
        elif json_type == "integer":
            return int
        elif json_type == "number":
            return float
        elif json_type == "boolean":
            return bool
        elif json_type == "array":
            # Handle array types
            items_schema = param_schema.get("items", {})
            if items_schema:
                item_type = self._json_type_to_python_type(items_schema)
                return List[item_type]
            return List[Any]
        elif json_type == "object":
            return Dict[str, Any]
        elif isinstance(json_type, list):
            # Handle union types like ["string", "array"]
            if "string" in json_type:
                return str  # Default to string for union types
            return str
        else:
            return str  # Default fallback

    async def _validate_and_convert_parameters(
        self, 
        raw_params: Dict[str, Any], 
        pydantic_model: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Validate and convert parameters using Pydantic model.
        
        This method implements the parameter validation and type conversion requirement from 2.2.
        """
        try:
            # Validate parameters using Pydantic model
            validated_model = pydantic_model(**raw_params)
            
            # Convert back to dictionary, excluding None values for optional parameters
            validated_params = {}
            for field_name, field_value in validated_model.dict().items():
                if field_value is not None:
                    validated_params[field_name] = field_value
            
            logger.debug(f"Validated parameters for tool '{self.connector_name}': {validated_params}")
            return validated_params
            
        except ValidationError as e:
            logger.error(f"Parameter validation failed for tool '{self.connector_name}': {e}")
            raise ValidationException(f"Parameter validation failed: {str(e)}")

    async def _format_result_for_agent(self, result: ConnectorResult) -> str:
        """
        Format connector result for the ReAct agent.
        
        This method formats the result in a way that's useful for the agent's reasoning.
        """
        try:
            if result.success:
                # Format successful result
                if isinstance(result.data, dict):
                    # For dictionary results, create a structured response
                    formatted_data = json.dumps(result.data, indent=2, default=str)
                    return f"✅ {self.connector_name} executed successfully:\n{formatted_data}"
                elif isinstance(result.data, (list, tuple)):
                    # For list results, format as numbered items
                    items = "\n".join([f"{i+1}. {item}" for i, item in enumerate(result.data)])
                    return f"✅ {self.connector_name} executed successfully:\n{items}"
                else:
                    # For other types, convert to string
                    return f"✅ {self.connector_name} executed successfully: {str(result.data)}"
            else:
                # Format error result
                error_msg = result.error or "Unknown error occurred"
                return f"❌ {self.connector_name} execution failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"Failed to format result for tool '{self.connector_name}': {e}")
            return f"❌ Error formatting result from {self.connector_name}: {str(e)}"
    
    async def get_tool_schema(self) -> Dict[str, Any]:
        """Get the tool schema for metadata purposes."""
        if self._tool_schema is None:
            await self._convert_schema_to_tool_format()
        return self._tool_schema or {}
    
    async def execute_with_context(
        self,
        parameters: Dict[str, Any],
        user_id: str,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the connector with proper authentication context.
        
        This method implements the authentication token injection mechanism from 2.3.
        """
        try:
            if not self.connector_instance:
                self.connector_instance = self.connector_class()
            
            # Validate parameters using Pydantic model
            if self._pydantic_model is None:
                self._create_pydantic_model()
            
            validated_params = await self._validate_and_convert_parameters(parameters, self._pydantic_model)
            
            # Create execution context with authentication tokens
            auth_manager = await get_auth_context_manager()
            context = await auth_manager.create_execution_context(
                user_id=user_id,
                connector_name=self.connector_name
            )
            
            # If auth_context is provided, merge it with the retrieved tokens
            if auth_context:
                context.auth_tokens.update(auth_context)
            
            # Execute connector
            result = await self.connector_instance.execute(validated_params, context)
            
            return {
                "success": result.success,
                "result": result.data,
                "error": result.error,
                "tool_name": self.connector_name,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": result.metadata,
                "auth_used": bool(context.auth_tokens)
            }
            
        except AuthenticationException as e:
            # Handle authentication failures with detailed error information
            auth_manager = await get_auth_context_manager()
            error_info = await auth_manager.handle_authentication_failure(
                user_id, self.connector_name, e
            )
            
            logger.error(f"Authentication failed for tool {self.connector_name}: {error_info}")
            return {
                "success": False,
                "error": error_info["message"],
                "error_type": error_info["error_type"],
                "suggested_action": error_info["suggested_action"],
                "requires_reauth": error_info["requires_reauth"],
                "tool_name": self.connector_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except ValidationError as e:
            error_msg = f"Parameter validation failed: {str(e)}"
            logger.error(f"Tool execution failed for {self.connector_name}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "validation_error",
                "tool_name": self.connector_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Tool execution failed for {self.connector_name}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "execution_error",
                "tool_name": self.connector_name,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_connector_name(self) -> str:
        """Get the connector name."""
        return self.connector_name
    
    def get_connector_class(self):
        """Get the connector class."""
        return self.connector_class
    
    # Enhanced error handling methods for task 6.1
    
    async def _parse_and_validate_parameters(self, query: str, pydantic_model: Type[BaseModel]) -> Dict[str, Any]:
        """
        Parse and validate parameters with enhanced error handling.
        
        This method implements comprehensive parameter validation as specified in requirement 2.3.
        """
        try:
            # For now, use a simple parameter parsing approach
            # This will be enhanced when we integrate with the ReAct agent properly
            import json
            try:
                # Try to parse query as JSON parameters
                parsed_params = json.loads(query)
                if isinstance(parsed_params, dict):
                    raw_params = parsed_params
                else:
                    # Fallback to simple text parameter
                    raw_params = {"text": query} if "text" in self.connector_instance.schema.get("properties", {}) else {"query": query}
            except json.JSONDecodeError:
                # Fallback to simple text parameter
                raw_params = {"text": query} if "text" in self.connector_instance.schema.get("properties", {}) else {"query": query}
            
            # Validate parameters using Pydantic model
            return await self._validate_and_convert_parameters(raw_params, pydantic_model)
            
        except Exception as e:
            logger.error(f"Parameter parsing failed for {self.connector_name}: {e}")
            raise ValidationException(f"Failed to parse parameters: {str(e)}")
    
    def _extract_validation_error_details(self, validation_error: ValidationError) -> Dict[str, Any]:
        """
        Extract detailed information from validation errors.
        
        This method provides structured error information for better user feedback.
        """
        try:
            errors = []
            if hasattr(validation_error, 'errors'):
                for error in validation_error.errors():
                    errors.append({
                        "field": ".".join(str(loc) for loc in error.get("loc", [])),
                        "message": error.get("msg", "Validation failed"),
                        "type": error.get("type", "unknown"),
                        "input": str(error.get("input", ""))[:100]  # Truncate for safety
                    })
            
            return {
                "message": f"Parameter validation failed: {str(validation_error)[:200]}",
                "errors": errors,
                "error_count": len(errors)
            }
        except Exception as e:
            logger.error(f"Failed to extract validation error details: {e}")
            return {
                "message": f"Parameter validation failed: {str(validation_error)[:200]}",
                "errors": [],
                "error_count": 0
            }
    
    async def _format_validation_error_response(self, error_details: Dict[str, Any]) -> str:
        """
        Format validation error response for the agent.
        
        This method provides user-friendly error messages with suggestions.
        """
        error_msg = f"❌ Parameter validation failed for {self.connector_name}"
        
        if error_details["errors"]:
            field_errors = []
            for error in error_details["errors"][:3]:  # Show max 3 errors
                field_errors.append(f"• {error['field']}: {error['message']}")
            
            if field_errors:
                error_msg += f"\n\nIssues found:\n" + "\n".join(field_errors)
            
            if error_details["error_count"] > 3:
                error_msg += f"\n... and {error_details['error_count'] - 3} more errors"
        
        # Add suggestions based on connector schema
        suggestions = await self._get_parameter_suggestions()
        if suggestions:
            error_msg += f"\n\n💡 Suggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions[:3])
        
        return error_msg
    
    async def _get_parameter_suggestions(self) -> List[str]:
        """
        Get parameter suggestions based on connector schema.
        
        This method provides helpful suggestions for parameter validation errors.
        """
        try:
            if not self.connector_instance:
                return []
            
            schema = self.connector_instance.schema
            suggestions = []
            
            # Add required parameters suggestion
            required_params = schema.get("required", [])
            if required_params:
                suggestions.append(f"Required parameters: {', '.join(required_params)}")
            
            # Add example parameters if available
            example_params = self.connector_instance.get_example_params()
            if example_params:
                suggestions.append(f"Example usage: {json.dumps(example_params, indent=2)}")
            
            # Add parameter hints if available
            hints = self.connector_instance.get_parameter_hints()
            if hints:
                for param, hint in list(hints.items())[:2]:  # Max 2 hints
                    suggestions.append(f"{param}: {hint}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get parameter suggestions for {self.connector_name}: {e}")
            return ["Check the parameter format and try again"]
    
    async def _handle_authentication_error(
        self, 
        auth_error: AuthenticationException, 
        user_id: str, 
        auth_context_manager
    ) -> str:
        """
        Handle authentication errors with recovery suggestions.
        
        This method implements authentication error handling as specified in requirement 2.4.
        """
        try:
            auth_manager = auth_context_manager or await get_auth_context_manager()
            error_info = await auth_manager.handle_authentication_failure(
                user_id, self.connector_name, auth_error
            )
            
            error_msg = f"🔒 Authentication failed for {self.connector_name}: {error_info['message']}"
            
            # Add recovery suggestions
            if error_info.get('suggested_action'):
                error_msg += f"\n\n💡 {error_info['suggested_action']}"
            
            if error_info.get('requires_reauth'):
                error_msg += "\n\n🔄 Please re-authenticate to continue using this tool."
            
            logger.error(f"Authentication error for tool {self.connector_name}", extra={
                "tool_name": self.connector_name,
                "user_id": user_id,
                "error_type": error_info.get('error_type', 'unknown'),
                "requires_reauth": error_info.get('requires_reauth', False)
            })
            
            return error_msg
            
        except Exception as e:
            logger.error(f"Failed to handle authentication error for {self.connector_name}: {e}")
            return f"🔒 Authentication failed for {self.connector_name}. Please check your credentials and try again."
    
    def _get_tool_timeout(self) -> int:
        """
        Get timeout for tool execution based on tool metadata.
        
        This method provides configurable timeouts for different tools.
        """
        try:
            # Default timeout
            default_timeout = 60
            
            # Get timeout from tool metadata if available
            if hasattr(self, '_tool_schema') and self._tool_schema:
                return self._tool_schema.get('timeout_seconds', default_timeout)
            
            # Tool-specific timeouts based on connector type
            timeout_map = {
                'gmail_connector': 30,
                'google_sheets_connector': 45,
                'perplexity_connector': 60,
                'text_summarizer_connector': 30
            }
            
            return timeout_map.get(self.connector_name, default_timeout)
            
        except Exception as e:
            logger.error(f"Failed to get timeout for {self.connector_name}: {e}")
            return 60  # Default fallback
    
    async def _format_timeout_error_response(self, timeout_seconds: int) -> str:
        """
        Format timeout error response for the agent.
        
        This method provides informative timeout error messages.
        """
        error_msg = f"⏱️ {self.connector_name} timed out after {timeout_seconds} seconds"
        
        # Add tool-specific timeout suggestions
        suggestions = []
        if self.connector_name == 'google_sheets_connector':
            suggestions.append("Try reducing the data range or splitting into smaller requests")
        elif self.connector_name == 'perplexity_connector':
            suggestions.append("Try simplifying your search query")
        elif self.connector_name == 'gmail_connector':
            suggestions.append("Try reducing the number of emails to process")
        else:
            suggestions.append("Try breaking down your request into smaller parts")
        
        if suggestions:
            error_msg += f"\n\n💡 Suggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions)
        
        return error_msg
    
    async def _handle_connector_error(
        self, 
        connector_error: ConnectorException, 
        retry_count: int, 
        max_retries: int, 
        user_id: str
    ) -> str:
        """
        Handle connector-specific errors with categorization and retry logic.
        
        This method implements graceful degradation when tools fail as specified in requirement 1.5.
        """
        try:
            # Log the connector error
            logger.error(f"Connector error for {self.connector_name}", extra={
                "tool_name": self.connector_name,
                "user_id": user_id,
                "error_message": str(connector_error),
                "retry_count": retry_count,
                "retryable": connector_error.retryable
            })
            
            # Check if error is retryable and we haven't exceeded max retries
            if connector_error.retryable and retry_count < max_retries:
                # This will be handled by the retry loop in the calling function
                raise connector_error
            
            # Format error response based on error category
            error_msg = f"❌ {self.connector_name} encountered an error"
            
            if connector_error.details:
                # Add specific error details if available
                if 'error_type' in connector_error.details:
                    error_msg += f" ({connector_error.details['error_type']})"
            
            error_msg += f": {connector_error.user_message or connector_error.message}"
            
            # Add recovery suggestions
            if connector_error.recovery_suggestions:
                error_msg += f"\n\n💡 Suggestions:\n"
                error_msg += "\n".join(f"• {suggestion}" for suggestion in connector_error.recovery_suggestions[:3])
            
            return error_msg
            
        except Exception as e:
            logger.error(f"Failed to handle connector error for {self.connector_name}: {e}")
            return f"❌ {self.connector_name} encountered an unexpected error. Please try again later."
    
    async def _format_external_api_error_response(self, api_error: ExternalAPIException) -> str:
        """
        Format external API error response for the agent.
        
        This method provides informative error messages for external API failures.
        """
        error_msg = f"🌐 External service error for {self.connector_name}"
        
        if api_error.details:
            if 'api_name' in api_error.details:
                error_msg += f" ({api_error.details['api_name']})"
            if 'status_code' in api_error.details:
                error_msg += f" [HTTP {api_error.details['status_code']}]"
        
        error_msg += f": {api_error.user_message or api_error.message}"
        
        # Add recovery suggestions
        suggestions = [
            "Check your internet connection",
            "Verify your API credentials are valid",
            "Try again in a few moments"
        ]
        
        if api_error.recovery_suggestions:
            suggestions = api_error.recovery_suggestions[:3]
        
        error_msg += f"\n\n💡 Suggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions)
        
        return error_msg
    
    async def _handle_timeout_error(
        self, 
        timeout_seconds: int, 
        retry_count: int, 
        max_retries: int, 
        user_id: str
    ) -> str:
        """
        Handle execution timeout with user feedback.
        
        This method formats timeout errors with helpful user guidance.
        Note: Retry logic is handled at the main execution level.
        """
        error_msg = f"⏱️ {self.connector_name} operation timed out after {timeout_seconds} seconds"
        
        # Add tool-specific timeout guidance
        if self.connector_name == 'gmail_connector':
            error_msg += "\n\n💡 Large email operations can take time. Consider reducing the scope or checking your Gmail quota."
        elif self.connector_name == 'google_sheets_connector':
            error_msg += "\n\n💡 Large spreadsheet operations can be slow. Try working with smaller ranges or fewer rows."
        elif self.connector_name == 'http_request':
            error_msg += "\n\n💡 The external service may be slow or unresponsive. Check the target URL and try again."
        elif self.connector_name == 'perplexity_connector':
            error_msg += "\n\n💡 Complex searches can take time. Try simplifying your query."
        else:
            error_msg += f"\n\n💡 The {self.connector_name} operation took longer than expected. Please try again."
        
        logger.error(f"Tool '{self.connector_name}' timed out after {timeout_seconds}s", extra={
            "tool_name": self.connector_name,
            "user_id": user_id,
            "timeout_seconds": timeout_seconds,
            "retry_count": retry_count
        })
        
        return error_msg
    
    async def _handle_rate_limit_error(
        self, 
        rate_limit_error: RateLimitException, 
        retry_count: int, 
        max_retries: int
    ) -> str:
        """
        Handle rate limiting with appropriate delays and user feedback.
        
        This method implements rate limit handling with user-friendly messages.
        """
        retry_after = rate_limit_error.details.get('retry_after', 60)
        
        error_msg = f"🚦 Rate limit exceeded for {self.connector_name}"
        
        if retry_after:
            if retry_after < 60:
                error_msg += f". Please wait {retry_after} seconds before trying again."
            else:
                minutes = retry_after // 60
                error_msg += f". Please wait {minutes} minute(s) before trying again."
        else:
            error_msg += ". Please wait a moment before trying again."
        
        # Add tool-specific rate limit guidance
        if self.connector_name == 'gmail_connector':
            error_msg += "\n\n💡 Gmail has strict rate limits. Consider reducing the frequency of requests."
        elif self.connector_name == 'google_sheets_connector':
            error_msg += "\n\n💡 Google Sheets API has usage quotas. Try processing smaller data ranges."
        elif self.connector_name == 'perplexity_connector':
            error_msg += "\n\n💡 Perplexity has query limits. Consider spacing out your searches."
        
        logger.warning(f"Rate limit exceeded for {self.connector_name}", extra={
            "tool_name": self.connector_name,
            "retry_after": retry_after,
            "retry_count": retry_count
        })
        
        return error_msg
    
    async def _handle_unexpected_error(
        self, 
        error: Exception, 
        retry_count: int, 
        max_retries: int, 
        user_id: str
    ) -> str:
        """
        Handle unexpected errors with graceful degradation.
        
        This method implements graceful degradation when tools fail as specified in requirement 1.5.
        """
        # Log the unexpected error
        logger.error(f"Unexpected error in tool {self.connector_name}", extra={
            "tool_name": self.connector_name,
            "user_id": user_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retry_count": retry_count
        })
        
        # Check if we should retry for certain error types
        retryable_error_types = [
            'ConnectionError',
            'TimeoutError',
            'HTTPError',
            'RequestException'
        ]
        
        if type(error).__name__ in retryable_error_types and retry_count < max_retries:
            # This will be handled by the retry loop in the calling function
            raise error
        
        # Format graceful degradation response
        error_msg = f"❌ {self.connector_name} encountered an unexpected issue"
        
        # Provide graceful degradation suggestions
        suggestions = [
            "Try rephrasing your request",
            "Check if the service is currently available",
            "Contact support if the issue persists"
        ]
        
        # Add tool-specific suggestions
        if self.connector_name == 'gmail_connector':
            suggestions.insert(0, "Verify your Gmail account is accessible")
        elif self.connector_name == 'google_sheets_connector':
            suggestions.insert(0, "Check if the spreadsheet exists and is accessible")
        elif self.connector_name == 'perplexity_connector':
            suggestions.insert(0, "Try a simpler search query")
        
        error_msg += f"\n\n💡 Suggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions[:3])
        
        return error_msg
    
    async def _format_critical_error_response(self, critical_error: Exception) -> str:
        """
        Format critical error response that prevents retry logic.
        
        This method handles critical system errors with appropriate user messaging.
        """
        error_msg = f"🚨 Critical error in {self.connector_name}: The tool is temporarily unavailable"
        
        # Add basic recovery suggestions
        suggestions = [
            "Please try again later",
            "Contact support if the issue persists",
            "Consider using alternative tools if available"
        ]
        
        error_msg += f"\n\n💡 Suggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions)
        
        return error_msg
    
    async def _format_max_retries_exceeded_response(self, max_retries: int) -> str:
        """
        Format response when maximum retries have been exceeded.
        
        This method provides informative messages when all retry attempts fail.
        """
        error_msg = f"❌ {self.connector_name} failed after {max_retries} attempts"
        
        suggestions = [
            "The service may be temporarily unavailable",
            "Check your network connection and credentials",
            "Try again in a few minutes",
            "Contact support if the issue persists"
        ]
        
        error_msg += f"\n\n💡 Suggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions)
        
        return error_msg