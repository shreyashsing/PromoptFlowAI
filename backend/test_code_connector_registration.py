#!/usr/bin/env python3
"""
Test Code Connector registration and integration.
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.registry import connector_registry
from app.connectors.core.register import register_core_connectors


def test_code_connector_registration():
    """Test that Code connector is properly registered."""
    print("🔧 Testing Code Connector Registration...")
    
    # Register all core connectors
    result = register_core_connectors()
    print(f"   📊 Registration result: {result}")
    
    # Check if Code connector is registered
    if connector_registry.is_registered("code"):
        print("   ✅ Code connector is registered")
        
        # Try to create an instance
        try:
            connector = connector_registry.create_connector("code")
            print(f"   ✅ Code connector instance created: {connector.name}")
            print(f"   📝 Description: {connector.description}")
            print(f"   🏷️ Category: {connector.category}")
            print(f"   🔧 Capabilities: {connector.get_capabilities()}")
            
            # Test schema
            schema = connector.schema
            print(f"   📋 Schema properties: {len(schema.get('properties', {}))}")
            
            # Test AI metadata
            ai_metadata = connector.get_ai_metadata()
            print(f"   🤖 AI metadata keys: {list(ai_metadata.keys())}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to create Code connector instance: {str(e)}")
            return False
    else:
        print("   ❌ Code connector is not registered")
        return False


def test_connector_list():
    """Test that Code connector appears in connector list."""
    print("\n📋 Testing Connector List...")
    
    try:
        connectors = connector_registry.list_connectors()
        code_connector = None
        
        for connector in connectors:
            if connector.name == "code":
                code_connector = connector
                break
        
        if code_connector:
            print("   ✅ Code connector found in connector list")
            print(f"   📛 Name: {code_connector.name}")
            print(f"   📝 Description: {code_connector.description}")
            print(f"   🏷️ Category: {code_connector.category}")
            return True
        else:
            print("   ❌ Code connector not found in connector list")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to list connectors: {str(e)}")
        return False


def test_connector_search():
    """Test that Code connector can be found via search."""
    print("\n🔍 Testing Connector Search...")
    
    try:
        # Search for code-related connectors
        search_terms = ["code", "javascript", "python", "development"]
        
        for term in search_terms:
            results = connector_registry.search_connectors(term)
            code_found = any(r.name == "code" for r in results)
            
            if code_found:
                print(f"   ✅ Code connector found when searching for '{term}'")
            else:
                print(f"   ⚠️ Code connector not found when searching for '{term}'")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to search connectors: {str(e)}")
        return False


def main():
    """Run all registration tests."""
    print("🚀 Starting Code Connector Registration Tests\n")
    
    tests = [
        test_code_connector_registration,
        test_connector_list,
        test_connector_search
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Test failed with exception: {str(e)}")
            results.append(False)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 Registration Test Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All Code connector registration tests passed!")
    else:
        print("❌ Some Code connector registration tests failed")
    
    return success_count == total_count


if __name__ == "__main__":
    main()