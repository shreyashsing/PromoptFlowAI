"""
Dynamic Tool Loader for ReAct Agent Integration.

Converts connector metadata into LangChain-compatible tools with rich descriptions
to improve ReAct agent tool selection and reduce hallucination.
"""
import json
import logging
from typing import Dict, Any, List, Callable, Optional
from pydantic import BaseModel, Field

from app.connectors.registry import get_connector_registry
from app.connectors.base import BaseConnector
from app.models.connector import ConnectorExecutionContext
from app.core.exceptions import ConnectorException

logger = logging.getLogger(__name__)


class ToolMetadata(BaseModel):
    """Enhanced tool metadata for LangChain integration."""
    name: str
    description: str
    parameters: Dict[str, Any]
    examples: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    category: str = "general"


class ConnectorTool:
    """
    Wrapper class that converts a connector into a LangChain-compatible tool.
    """
    
    def __init__(self, connector_name: str, connector: BaseConnector, auth_context: Optional[Dict[str, str]] = None):
        self.connector_name = connector_name
        self.connector = connector
        self.auth_context = auth_context or {}
        self.metadata = self._generate_tool_metadata()
    
    def _generate_tool_metadata(self) -> ToolMetadata:
        """Generate rich tool metadata from connector."""
        ai_metadata = self.connector.get_ai_metadata()
        
        # Create comprehensive description
        description_parts = [
            ai_metadata["description"],
            f"Category: {ai_metadata['category']}",
            f"Capabilities: {', '.join(ai_metadata['capabilities'])}"
        ]
        
        # Add use cases to description
        if ai_metadata.get("use_cases"):
            use_case_descriptions = [uc.get("description", uc.get("title", "")) for uc in ai_metadata["use_cases"][:3]]
            description_parts.append(f"Common use cases: {'; '.join(use_case_descriptions)}")
        
        # Add example prompts
        if ai_metadata.get("example_prompts"):
            description_parts.append(f"Example usage: {'; '.join(ai_metadata['example_prompts'][:2])}")
        
        # Add parameter hints
        if ai_metadata.get("parameter_hints"):
            key_params = list(ai_metadata["parameter_hints"].keys())[:3]
            param_hints = [f"{param}: {ai_metadata['parameter_hints'][param][:50]}..." 
                          for param in key_params]
            description_parts.append(f"Key parameters: {'; '.join(param_hints)}")
        
        full_description = "\n".join(description_parts)
        
        return ToolMetadata(
            name=self.connector_name,
            description=full_description,
            parameters=ai_metadata.get("schema", {}),
            examples=ai_metadata.get("example_prompts", []),
            use_cases=[uc.get("title", "") for uc in ai_metadata.get("use_cases", [])],
            capabilities=ai_metadata.get("capabilities", []),
            category=ai_metadata.get("category", "general")
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the connector with provided parameters."""
        try:
            # Create execution context
            context = ConnectorExecutionContext(
                auth_tokens=self.auth_context,
                previous_results={},
                workflow_context={}
            )
            
            # Execute connector
            result = await self.connector.execute_with_retry(kwargs, context)
            
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "metadata": {
                    "connector": self.connector_name,
                    "execution_time": getattr(result, 'execution_time', None)
                }
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed for {self.connector_name}: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {"connector": self.connector_name}
            }
    
    def to_langchain_tool(self):
        """Convert to LangChain Tool format."""
        try:
            from langchain.tools import Tool
            
            def tool_func(**kwargs):
                """Synchronous wrapper for async connector execution."""
                import asyncio
                try:
                    # Get or create event loop
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If loop is running, we need to use a different approach
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, self.execute(**kwargs))
                                return future.result()
                        else:
                            return loop.run_until_complete(self.execute(**kwargs))
                    except RuntimeError:
                        return asyncio.run(self.execute(**kwargs))
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "data": None
                    }
            
            return Tool(
                name=self.connector_name,
                description=self.metadata.description,
                func=tool_func
            )
            
        except ImportError:
            logger.warning("LangChain not available, returning custom tool format")
            return {
                "name": self.connector_name,
                "description": self.metadata.description,
                "func": self.execute,
                "metadata": self.metadata.dict()
            }


class DynamicToolLoader:
    """
    Dynamic tool loader that converts connectors to LangChain-compatible tools.
    """
    
    def __init__(self, auth_context: Optional[Dict[str, str]] = None):
        self.registry = get_connector_registry()
        self.auth_context = auth_context or {}
        self._tools_cache = {}
    
    def load_all_tools(self) -> List[ConnectorTool]:
        """Load all available connectors as tools."""
        tools = []
        
        for connector_name in self.registry.list_connectors():
            try:
                tool = self.load_tool(connector_name)
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.warning(f"Failed to load tool {connector_name}: {str(e)}")
        
        return tools
    
    def load_tool(self, connector_name: str) -> Optional[ConnectorTool]:
        """Load a specific connector as a tool."""
        if connector_name in self._tools_cache:
            return self._tools_cache[connector_name]
        
        try:
            connector = self.registry.create_connector(connector_name)
            tool = ConnectorTool(connector_name, connector, self.auth_context)
            self._tools_cache[connector_name] = tool
            return tool
            
        except Exception as e:
            logger.error(f"Failed to create tool for {connector_name}: {str(e)}")
            return None
    
    def load_tools_by_category(self, category: str) -> List[ConnectorTool]:
        """Load tools filtered by category."""
        tools = []
        connector_names = self.registry.list_connectors_by_category(category)
        
        for name in connector_names:
            tool = self.load_tool(name)
            if tool:
                tools.append(tool)
        
        return tools
    
    def load_tools_by_capability(self, capability: str) -> List[ConnectorTool]:
        """Load tools filtered by capability."""
        tools = []
        connector_names = self.registry.search_by_capability(capability)
        
        for name in connector_names:
            tool = self.load_tool(name)
            if tool:
                tools.append(tool)
        
        return tools
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get all tool descriptions for agent context."""
        descriptions = {}
        
        for connector_name in self.registry.list_connectors():
            try:
                tool = self.load_tool(connector_name)
                if tool:
                    descriptions[connector_name] = tool.metadata.description
            except Exception as e:
                logger.warning(f"Failed to get description for {connector_name}: {str(e)}")
        
        return descriptions
    
    def get_tools_for_prompt(self, user_prompt: str, max_tools: int = 10) -> List[ConnectorTool]:
        """Get most relevant tools for a user prompt."""
        relevant_connectors = self.registry.get_connectors_for_prompt(user_prompt)
        tools = []
        
        for connector_metadata in relevant_connectors[:max_tools]:
            connector_name = connector_metadata["name"]
            tool = self.load_tool(connector_name)
            if tool:
                # Add relevance score to tool metadata
                tool.relevance_score = connector_metadata.get("relevance_score", 0)
                tools.append(tool)
        
        return tools
    
    def to_langchain_tools(self, connector_names: Optional[List[str]] = None) -> List:
        """Convert connectors to LangChain Tool objects."""
        if connector_names is None:
            connector_names = self.registry.list_connectors()
        
        langchain_tools = []
        
        for name in connector_names:
            try:
                tool = self.load_tool(name)
                if tool:
                    lc_tool = tool.to_langchain_tool()
                    langchain_tools.append(lc_tool)
            except Exception as e:
                logger.warning(f"Failed to convert {name} to LangChain tool: {str(e)}")
        
        return langchain_tools
    
    def get_tool_registry_json(self) -> Dict[str, Any]:
        """Get tool registry in JSON format for agent consumption."""
        registry_data = {
            "tools": {},
            "categories": {},
            "capabilities": {},
            "metadata": {
                "total_tools": 0,
                "last_updated": None
            }
        }
        
        # Load all tools
        tools = self.load_all_tools()
        registry_data["metadata"]["total_tools"] = len(tools)
        
        # Organize tools
        for tool in tools:
            tool_data = {
                "name": tool.connector_name,
                "description": tool.metadata.description,
                "parameters": tool.metadata.parameters,
                "examples": tool.metadata.examples,
                "use_cases": tool.metadata.use_cases,
                "capabilities": tool.metadata.capabilities,
                "category": tool.metadata.category
            }
            
            registry_data["tools"][tool.connector_name] = tool_data
            
            # Group by category
            category = tool.metadata.category
            if category not in registry_data["categories"]:
                registry_data["categories"][category] = []
            registry_data["categories"][category].append(tool.connector_name)
            
            # Group by capabilities
            for capability in tool.metadata.capabilities:
                if capability not in registry_data["capabilities"]:
                    registry_data["capabilities"][capability] = []
                registry_data["capabilities"][capability].append(tool.connector_name)
        
        return registry_data
    
    def update_auth_context(self, auth_context: Dict[str, str]):
        """Update authentication context for all tools."""
        self.auth_context = auth_context
        # Clear cache to force recreation with new auth context
        self._tools_cache.clear()


# Global tool loader instance
_tool_loader = None

def get_tool_loader(auth_context: Optional[Dict[str, str]] = None) -> DynamicToolLoader:
    """Get global tool loader instance."""
    global _tool_loader
    
    if _tool_loader is None:
        _tool_loader = DynamicToolLoader(auth_context)
    elif auth_context:
        _tool_loader.update_auth_context(auth_context)
    
    return _tool_loader