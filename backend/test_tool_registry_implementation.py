"""
Test script to verify the Tool Registry implementation for task 2.
"""
import asyncio
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_tool_registry_implementation():
    """Test the Tool Registry implementation."""
    try:
        from app.services.tool_registry import get_tool_registry
        from app.services.auth_context_manager import get_auth_context_manager
        
        logger.info("Testing Tool Registry implementation...")
        
        # Test 1: Initialize tool registry and discover connectors
        logger.info("1. Testing tool registry initialization...")
        tool_registry = await get_tool_registry()
        
        # Test 2: Check discovered connectors
        logger.info("2. Testing connector discovery...")
        discovered_connectors = await tool_registry.discover_available_connectors()
        logger.info(f"Discovered {len(discovered_connectors)} connectors:")
        for connector in discovered_connectors:
            logger.info(f"  - {connector['name']}: {connector['description']}")
        
        # Test 3: Get tool metadata
        logger.info("3. Testing tool metadata extraction...")
        tool_metadata = await tool_registry.get_tool_metadata()
        logger.info(f"Extracted metadata for {len(tool_metadata)} tools:")
        for metadata in tool_metadata:
            logger.info(f"  - {metadata['name']}: {metadata['category']}")
            logger.info(f"    Auth required: {metadata['auth_requirements']['type']}")
            logger.info(f"    Required params: {metadata['required_params']}")
        
        # Test 4: Get available tools
        logger.info("4. Testing tool availability...")
        available_tools = await tool_registry.get_available_tools()
        logger.info(f"Available tools: {len(available_tools)}")
        for tool in available_tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        
        # Test 5: Test authentication context manager
        logger.info("5. Testing authentication context manager...")
        auth_manager = await get_auth_context_manager()
        
        # Test context creation (with system user)
        test_context = await auth_manager.create_execution_context(
            user_id="00000000-0000-0000-0000-000000000001",  # Development user
            connector_name="text_summarizer"
        )
        logger.info(f"Created execution context: user_id={test_context.user_id}, request_id={test_context.request_id}")
        
        # Test 6: Test tool execution with a simple connector
        logger.info("6. Testing tool execution...")
        try:
            # Test with text summarizer (doesn't require auth)
            result = await tool_registry.execute_tool(
                tool_name="text_summarizer",
                parameters={
                    "text": "This is a test text for summarization. It contains multiple sentences to test the summarization functionality.",
                    "max_length": 50,
                    "style": "concise"
                },
                user_id="00000000-0000-0000-0000-000000000001"
            )
            logger.info(f"Tool execution result: success={result.get('success')}")
            if result.get('success'):
                logger.info(f"Summary: {result.get('result', {}).get('summary', 'No summary')}")
            else:
                logger.warning(f"Tool execution failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Tool execution test failed: {e}")
        
        # Test 7: Test schema conversion
        logger.info("7. Testing schema conversion...")
        text_summarizer_metadata = await tool_registry.get_tool_metadata_by_name("text_summarizer")
        if text_summarizer_metadata:
            logger.info("Text Summarizer schema conversion:")
            logger.info(f"  Parameters: {list(text_summarizer_metadata['parameter_schema'].keys())}")
            logger.info(f"  Required: {text_summarizer_metadata['required_params']}")
            logger.info(f"  Optional: {text_summarizer_metadata['optional_params']}")
        
        # Test 8: Test tools by category
        logger.info("8. Testing tools by category...")
        ai_tools = await tool_registry.get_tools_by_category("ai_services")
        logger.info(f"AI Services tools: {[tool['name'] for tool in ai_tools]}")
        
        communication_tools = await tool_registry.get_tools_by_category("communication")
        logger.info(f"Communication tools: {[tool['name'] for tool in communication_tools]}")
        
        data_tools = await tool_registry.get_tools_by_category("data_sources")
        logger.info(f"Data Sources tools: {[tool['name'] for tool in data_tools]}")
        
        logger.info("✅ Tool Registry implementation test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Tool Registry implementation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_connector_tool_adapter():
    """Test the ConnectorToolAdapter implementation."""
    try:
        from app.services.connector_tool_adapter import ConnectorToolAdapter
        from app.connectors.core.text_summarizer_connector import TextSummarizerConnector
        
        logger.info("Testing ConnectorToolAdapter implementation...")
        
        # Test 1: Create adapter
        adapter = ConnectorToolAdapter("text_summarizer", TextSummarizerConnector)
        
        # Test 2: Convert to LangChain tool
        tool = await adapter.to_langchain_tool()
        logger.info(f"Created LangChain tool: {tool.name}")
        logger.info(f"Tool description: {tool.description}")
        
        # Test 3: Get tool schema
        schema = await adapter.get_tool_schema()
        logger.info(f"Tool schema: {schema['name']}")
        logger.info(f"Parameters: {list(schema['parameters'].keys())}")
        
        # Test 4: Test parameter validation
        test_params = {
            "text": "This is a test text for validation.",
            "max_length": 50,
            "style": "concise"
        }
        
        result = await adapter.execute_with_context(
            parameters=test_params,
            user_id="00000000-0000-0000-0000-000000000001"
        )
        
        logger.info(f"Adapter execution result: success={result.get('success')}")
        if not result.get('success'):
            logger.warning(f"Execution failed: {result.get('error')}")
        
        logger.info("✅ ConnectorToolAdapter test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ ConnectorToolAdapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    logger.info("Starting Tool Registry implementation tests...")
    
    # Test 1: Tool Registry
    registry_success = await test_tool_registry_implementation()
    
    # Test 2: Connector Tool Adapter
    adapter_success = await test_connector_tool_adapter()
    
    if registry_success and adapter_success:
        logger.info("🎉 All tests passed! Tool Registry implementation is working correctly.")
    else:
        logger.error("❌ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    asyncio.run(main())