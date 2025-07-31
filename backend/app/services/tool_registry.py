"""
Tool Registry for managing connector-to-tool conversion for ReAct agent.
"""
import logging
from typing import Dict, Any, List, Optional, Type
from langchain.tools import Tool

from app.connectors.registry import get_connector_registry
from app.connectors.core.register import register_core_connectors
from app.connectors.base import BaseConnector
from app.models.connector import ConnectorMetadata
from app.services.connector_tool_adapter import ConnectorToolAdapter
from app.core.exceptions import ToolRegistrationError

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Manages registration and discovery of connectors as LangGraph tools.
    Automatically converts existing connectors into tools that can be used by the ReAct agent.
    
    This class implements the connector discovery and registration system as specified
    in requirements 2.1 and 2.2.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.adapters: Dict[str, ConnectorToolAdapter] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the tool registry by discovering and registering connectors.
        
        This method implements the connector discovery system as specified in requirement 2.1:
        - Discovers available connectors from existing registry
        - Extracts tool metadata from connector schemas
        - Automatically registers connectors as tools
        """
        if self._initialized:
            return
            
        try:
            logger.info("Initializing tool registry...")
            
            # Get connector registry
            connector_registry = get_connector_registry()
            
            # Register core connectors if none are registered
            if connector_registry.get_connector_count() == 0:
                logger.info("No connectors found, registering core connectors...")
                register_core_connectors()
            
            # Discover and register each connector as a tool
            registered_count = 0
            failed_count = 0
            connector_names = connector_registry.list_connectors()
            
            logger.info(f"Discovered {len(connector_names)} connectors: {connector_names}")
            
            for connector_name in connector_names:
                try:
                    connector_class = connector_registry.get_connector(connector_name)
                    connector_metadata = connector_registry.get_metadata(connector_name)
                    
                    # Validate connector class before registration
                    if not await self._validate_connector_class(connector_name, connector_class):
                        failed_count += 1
                        logger.warning(f"Skipping connector '{connector_name}': validation failed")
                        continue
                    
                    # Extract and store tool metadata
                    tool_metadata = await self._extract_tool_metadata(connector_name, connector_class, connector_metadata)
                    self.tool_metadata[connector_name] = tool_metadata
                    
                    # Register connector as tool
                    await self._register_connector_as_tool(connector_name, connector_class)
                    registered_count += 1
                    logger.info(f"✅ Registered connector '{connector_name}' as tool with metadata")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Failed to register connector '{connector_name}' as tool: {e}")
                    # Log more details for debugging
                    import traceback
                    logger.debug(f"Full traceback for {connector_name}: {traceback.format_exc()}")
            
            self._initialized = True
            logger.info(f"🚀 Tool registry initialized with {registered_count} tools ({failed_count} failed)")
            
        except Exception as e:
            logger.error(f"Failed to initialize tool registry: {e}")
            raise ToolRegistrationError(f"Tool registry initialization failed: {str(e)}")
    
    async def _validate_connector_class(self, connector_name: str, connector_class: Type[BaseConnector]) -> bool:
        """
        Validate that a connector class is properly implemented and can be instantiated.
        
        This method implements requirement 2.2: Validate tool schemas and parameter formatting.
        
        Args:
            connector_name: Name of the connector
            connector_class: Connector class to validate
            
        Returns:
            True if connector is valid, False otherwise
        """
        try:
            # Check if class is abstract
            import inspect
            if inspect.isabstract(connector_class):
                logger.warning(f"Connector '{connector_name}' is abstract and cannot be instantiated")
                return False
            
            # Try to instantiate the connector
            connector_instance = connector_class()
            
            # Check if required methods are implemented
            required_methods = ['execute', 'get_auth_requirements']
            for method_name in required_methods:
                if not hasattr(connector_instance, method_name):
                    logger.warning(f"Connector '{connector_name}' missing required method: {method_name}")
                    return False
                
                method = getattr(connector_instance, method_name)
                if not callable(method):
                    logger.warning(f"Connector '{connector_name}' method '{method_name}' is not callable")
                    return False
            
            # Check if schema is defined
            if not hasattr(connector_instance, 'schema') or not connector_instance.schema:
                logger.warning(f"Connector '{connector_name}' has no schema defined")
                return False
            
            # Validate schema structure
            schema = connector_instance.schema
            if not isinstance(schema, dict):
                logger.warning(f"Connector '{connector_name}' schema is not a dictionary")
                return False
            
            # Check for required schema fields
            if 'properties' not in schema:
                logger.warning(f"Connector '{connector_name}' schema missing 'properties' field")
                return False
            
            logger.debug(f"✅ Connector '{connector_name}' validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connector '{connector_name}' validation failed: {e}")
            return False
    
    async def _extract_tool_metadata(
        self, 
        connector_name: str, 
        connector_class: Type[BaseConnector], 
        connector_metadata: ConnectorMetadata
    ) -> Dict[str, Any]:
        """
        Extract tool metadata from connector schemas.
        
        This method implements the tool metadata extraction requirement from 2.1.
        
        Args:
            connector_name: Name of the connector
            connector_class: Connector class
            connector_metadata: Connector metadata from registry
            
        Returns:
            Dictionary containing tool metadata
        """
        try:
            # Create temporary connector instance to get schema and auth requirements
            connector_instance = connector_class()
            
            # Get authentication requirements
            auth_requirements = await connector_instance.get_auth_requirements()
            
            # Extract parameter schema
            parameter_schema = connector_instance.schema
            
            # Build comprehensive tool metadata
            tool_metadata = {
                "name": connector_name,
                "display_name": connector_name.replace("_", " ").title(),
                "description": connector_metadata.description,
                "category": connector_metadata.category,
                "parameter_schema": parameter_schema,
                "auth_requirements": {
                    "type": auth_requirements.type.value if hasattr(auth_requirements.type, 'value') else str(auth_requirements.type),
                    "fields": auth_requirements.fields,
                    "instructions": auth_requirements.instructions,
                    "oauth_scopes": getattr(auth_requirements, 'oauth_scopes', [])
                },
                "example_params": connector_instance.get_example_params(),
                "parameter_hints": connector_instance.get_parameter_hints(),
                "required_params": parameter_schema.get("required", []),
                "optional_params": [
                    param for param in parameter_schema.get("properties", {}).keys()
                    if param not in parameter_schema.get("required", [])
                ],
                "supports_streaming": False,  # Default, can be overridden by specific connectors
                "max_retries": 3,  # Default retry count
                "timeout_seconds": 60  # Default timeout
            }
            
            logger.debug(f"Extracted metadata for tool '{connector_name}': {tool_metadata}")
            return tool_metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata for connector {connector_name}: {e}")
            # Return minimal metadata on error
            return {
                "name": connector_name,
                "display_name": connector_name.replace("_", " ").title(),
                "description": f"{connector_name} connector",
                "category": "general",
                "parameter_schema": {},
                "auth_requirements": {"type": "none", "fields": {}, "instructions": ""},
                "example_params": {},
                "parameter_hints": {},
                "required_params": [],
                "optional_params": [],
                "supports_streaming": False,
                "max_retries": 3,
                "timeout_seconds": 60
            }

    async def _register_connector_as_tool(self, connector_name: str, connector_class: Type[BaseConnector]) -> None:
        """
        Register a single connector as a LangGraph tool.
        
        This method implements the automatic connector registration requirement from 2.2.
        """
        try:
            logger.debug(f"🔧 Registering connector '{connector_name}' as tool...")
            
            # Create connector tool adapter
            adapter = ConnectorToolAdapter(connector_name, connector_class)
            logger.debug(f"📦 Created adapter for '{connector_name}'")
            
            # Convert to LangGraph tool
            tool = await adapter.to_langchain_tool()
            logger.debug(f"🔨 Converted '{connector_name}' to LangChain tool")
            
            # Validate the created tool
            if not self._validate_tool(tool, connector_name):
                raise ToolRegistrationError(f"Tool validation failed for {connector_name}")
            
            # Store both adapter and tool
            self.adapters[connector_name] = adapter
            self.tools[connector_name] = tool
            
            logger.info(f"✅ Successfully registered connector '{connector_name}' as tool")
            logger.debug(f"🔍 Tool details - Name: {tool.name}, Description: {tool.description[:100]}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to register connector {connector_name}: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _validate_tool(self, tool: Tool, connector_name: str) -> bool:
        """
        Validate that a created tool has all required properties.
        
        This method implements requirement 2.2: Validate tool schemas and parameter formatting.
        
        Args:
            tool: The LangChain tool to validate
            connector_name: Name of the connector for logging
            
        Returns:
            True if tool is valid, False otherwise
        """
        try:
            # Check required tool properties
            if not hasattr(tool, 'name') or not tool.name:
                logger.error(f"Tool for '{connector_name}' missing name")
                return False
            
            if not hasattr(tool, 'description') or not tool.description:
                logger.error(f"Tool for '{connector_name}' missing description")
                return False
            
            if not hasattr(tool, 'func') or not callable(tool.func):
                logger.error(f"Tool for '{connector_name}' missing or invalid func")
                return False
            
            # Check tool args schema if present
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    # Try to create an instance to validate schema
                    tool.args_schema()
                    logger.debug(f"✅ Tool '{connector_name}' has valid args schema")
                except Exception as schema_error:
                    logger.warning(f"Tool '{connector_name}' args schema validation failed: {schema_error}")
                    # Don't fail registration for schema issues, just log warning
            
            logger.debug(f"✅ Tool validation passed for '{connector_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tool validation failed for '{connector_name}': {e}")
            return False
    
    async def get_available_tools(self) -> List[Tool]:
        """Get list of all registered tools."""
        if not self._initialized:
            await self.initialize()
        
        return list(self.tools.values())
    
    async def get_tool_by_name(self, tool_name: str) -> Optional[Tool]:
        """Get a specific tool by name."""
        if not self._initialized:
            await self.initialize()
        
        return self.tools.get(tool_name)
    
    async def get_tool_registration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive tool registration status for debugging.
        
        This method implements requirement 2.2: Add comprehensive logging for tool registration process.
        
        Returns:
            Dictionary containing registration status and details
        """
        if not self._initialized:
            await self.initialize()
        
        # Get connector registry for comparison
        from app.connectors.registry import get_connector_registry
        connector_registry = get_connector_registry()
        
        all_connectors = connector_registry.list_connectors()
        registered_tools = list(self.tools.keys())
        failed_connectors = [name for name in all_connectors if name not in registered_tools]
        
        status = {
            "initialized": self._initialized,
            "total_connectors_discovered": len(all_connectors),
            "successfully_registered": len(registered_tools),
            "registration_failures": len(failed_connectors),
            "success_rate": len(registered_tools) / len(all_connectors) * 100 if all_connectors else 0,
            "registered_tools": [
                {
                    "name": tool_name,
                    "description": self.tools[tool_name].description[:100] + "..." if len(self.tools[tool_name].description) > 100 else self.tools[tool_name].description,
                    "has_args_schema": hasattr(self.tools[tool_name], 'args_schema') and self.tools[tool_name].args_schema is not None,
                    "metadata": self.tool_metadata.get(tool_name, {})
                }
                for tool_name in registered_tools
            ],
            "failed_connectors": failed_connectors,
            "all_connectors": all_connectors
        }
        
        return status
    
    async def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the schema for a specific tool."""
        if not self._initialized:
            await self.initialize()
        
        adapter = self.adapters.get(tool_name)
        if adapter:
            return await adapter.get_tool_schema()
        return None
    
    async def discover_available_connectors(self) -> List[Dict[str, Any]]:
        """
        Discover all available connectors from the connector registry.
        
        This method implements the connector discovery requirement from 2.1.
        
        Returns:
            List of connector information dictionaries
        """
        try:
            connector_registry = get_connector_registry()
            
            # Get all connector metadata
            all_metadata = connector_registry.get_all_metadata()
            
            discovered_connectors = []
            for metadata in all_metadata:
                connector_info = {
                    "name": metadata.name,
                    "description": metadata.description,
                    "category": metadata.category,
                    "auth_type": metadata.auth_type,
                    "parameter_schema": metadata.parameter_schema,
                    "is_registered_as_tool": metadata.name in self.tools
                }
                discovered_connectors.append(connector_info)
            
            logger.info(f"Discovered {len(discovered_connectors)} connectors")
            return discovered_connectors
            
        except Exception as e:
            logger.error(f"Failed to discover connectors: {e}")
            return []

    async def get_tool_metadata(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive metadata for all registered tools.
        
        This method returns the extracted tool metadata as specified in requirement 2.1.
        """
        if not self._initialized:
            await self.initialize()
        
        return list(self.tool_metadata.values())

    async def get_tool_metadata_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool metadata dictionary or None if not found
        """
        if not self._initialized:
            await self.initialize()
        
        return self.tool_metadata.get(tool_name)

    async def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Category name (e.g., 'communication', 'data_sources', 'ai_services')
            
        Returns:
            List of tool metadata for tools in the specified category
        """
        if not self._initialized:
            await self.initialize()
        
        category_tools = []
        for tool_metadata in self.tool_metadata.values():
            if tool_metadata.get("category") == category:
                category_tools.append(tool_metadata)
        
        return category_tools

    async def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for tools by name, description, or category.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching tool metadata
        """
        if not self._initialized:
            await self.initialize()
        
        query_lower = query.lower()
        matching_tools = []
        
        for tool_metadata in self.tool_metadata.values():
            if (query_lower in tool_metadata.get("name", "").lower() or
                query_lower in tool_metadata.get("description", "").lower() or
                query_lower in tool_metadata.get("category", "").lower()):
                matching_tools.append(tool_metadata)
        
        return matching_tools
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with the given parameters and authentication context.
        
        This method uses the enhanced authentication context from task 2.3.
        """
        if not self._initialized:
            await self.initialize()
        
        adapter = self.adapters.get(tool_name)
        if not adapter:
            raise ToolRegistrationError(f"Tool '{tool_name}' not found")
        
        try:
            # Execute tool with authentication context management
            result = await adapter.execute_with_context(
                parameters=parameters,
                user_id=user_id,
                auth_context=auth_context
            )
            
            # Log successful execution
            if result.get("success"):
                logger.info(f"Tool '{tool_name}' executed successfully for user {user_id}")
            else:
                logger.warning(f"Tool '{tool_name}' execution failed for user {user_id}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            raise
    
    def is_initialized(self) -> bool:
        """Check if the tool registry is initialized."""
        return self._initialized
    
    def get_tool_count(self) -> int:
        """Get the number of registered tools."""
        return len(self.tools)


# Global registry instance
tool_registry: Optional[ToolRegistry] = None


async def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry instance."""
    global tool_registry
    if not tool_registry:
        tool_registry = ToolRegistry()
        await tool_registry.initialize()
    return tool_registry