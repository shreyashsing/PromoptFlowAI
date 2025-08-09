"""
Test Google Translate Connector registration with the tool registry.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.connectors.core.register import register_core_connectors
from app.connectors.registry import connector_registry
from app.services.tool_registry import ToolRegistry


async def test_google_translate_registration():
    """Test Google Translate connector registration."""
    print("\n🔄 Testing Google Translate Connector Registration...")
    
    try:
        # Register core connectors
        result = register_core_connectors()
        print(f"   📊 Registration result: {result}")
        
        # Check if Google Translate connector is registered
        if connector_registry.is_registered("google_translate"):
            print("   ✅ Google Translate connector registered successfully")
        else:
            print("   ❌ Google Translate connector not found in registry")
            return False
        
        # Test creating connector instance
        connector = connector_registry.create_connector("google_translate")
        print(f"   ✅ Connector instance created: {connector.name}")
        
        # Test connector properties
        assert connector.name == "google_translate"
        assert connector.category == "utility"
        print("   ✅ Connector properties validated")
        
        # Test schema
        schema = connector.schema
        assert "text" in schema["properties"]
        assert "target_language" in schema["properties"]
        print("   ✅ Connector schema validated")
        
        # Test auth requirements
        auth_req = await connector.get_auth_requirements()
        assert auth_req.type.value == "oauth2"
        print("   ✅ Auth requirements validated")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Registration test failed: {str(e)}")
        return False


async def test_tool_registry_integration():
    """Test Google Translate connector integration with tool registry."""
    print("\n🔄 Testing Tool Registry Integration...")
    
    try:
        # Initialize tool registry
        tool_registry = ToolRegistry()
        
        # Register connectors
        register_core_connectors()
        
        # Initialize tool registry
        await tool_registry.initialize()
        
        # Check if Google Translate tools are available
        all_tools = await tool_registry.get_available_tools()
        google_translate_tools = [tool for tool in all_tools if "google_translate" in tool.name.lower()]
        
        if google_translate_tools:
            print(f"   ✅ Found {len(google_translate_tools)} Google Translate tools")
            for tool in google_translate_tools:
                print(f"      - {tool.name}: {tool.description}")
        else:
            print("   ❌ No Google Translate tools found in tool registry")
            return False
        
        # Test tool search
        search_results = await tool_registry.search_tools("translate text")
        translate_tools = [tool for tool in search_results if "google_translate" in tool.get("name", "").lower()]
        
        if translate_tools:
            print(f"   ✅ Found {len(translate_tools)} tools via search")
        else:
            print("   ⚠️  No Google Translate tools found via search")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Tool registry integration test failed: {str(e)}")
        return False


async def main():
    """Run all Google Translate registration tests."""
    print("🚀 Starting Google Translate Registration Tests")
    
    results = []
    results.append(await test_google_translate_registration())
    results.append(await test_tool_registry_integration())
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 Test Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All Google Translate registration tests passed!")
    else:
        print("❌ Some Google Translate registration tests failed")
    
    return success_count == total_count


if __name__ == "__main__":
    asyncio.run(main())