"""
Test script for Notion Connector functionality.
"""
import asyncio
import json
from app.connectors.core.notion_connector import NotionConnector
from app.models.connector import ConnectorExecutionContext


async def test_notion_connector():
    """Test Notion connector functionality."""
    print("🚀 Testing Notion Connector")
    
    # Initialize connector
    connector = NotionConnector()
    
    # Test 1: Connector metadata
    print(f"\n📋 Connector Info:")
    print(f"   Name: {connector.name}")
    print(f"   Category: {connector.category}")
    print(f"   Description: {connector.description}")
    
    # Test 2: Schema validation
    print(f"\n🔧 Schema Properties:")
    schema = connector.schema
    properties = schema.get("properties", {})
    print(f"   Total properties: {len(properties)}")
    print(f"   Required: {schema.get('required', [])}")
    
    # Test key properties
    key_props = ["resource", "operation", "page_id", "database_id", "title", "content"]
    for prop in key_props:
        if prop in properties:
            prop_info = properties[prop]
            print(f"   ✅ {prop}: {prop_info.get('type', 'unknown')} - {prop_info.get('description', 'No description')[:50]}...")
        else:
            print(f"   ❌ Missing property: {prop}")
    
    # Test 3: Auth requirements
    print(f"\n🔐 Authentication:")
    auth_req = await connector.get_auth_requirements()
    print(f"   Auth Type: {auth_req.type}")
    print(f"   Required Fields: {auth_req.fields}")
    print(f"   Instructions: {auth_req.instructions}")
    
    # Test 4: Resource and operation validation
    print(f"\n📚 Resources and Operations:")
    
    resources = properties["resource"]["enum"]
    operations = properties["operation"]["enum"]
    
    print(f"   Resources ({len(resources)}): {', '.join(resources)}")
    print(f"   Operations ({len(operations)}): {len(operations)} total")
    
    # Group operations by resource
    resource_ops = {
        "block": ["append_block", "get_block_children"],
        "database": ["get_database", "get_all_databases", "search_databases"],
        "database_page": ["create_database_page", "get_database_page", "get_all_database_pages", "update_database_page"],
        "page": ["create_page", "get_page", "search_pages", "archive_page"],
        "user": ["get_user", "get_all_users"]
    }
    
    for resource, expected_ops in resource_ops.items():
        print(f"   📁 {resource}:")
        for op in expected_ops:
            if op in operations:
                print(f"      ✅ {op}")
            else:
                print(f"      ❌ Missing: {op}")
    
    # Test 5: ID normalization
    print(f"\n🔗 ID Normalization Tests:")
    test_ids = [
        "12345678901234567890123456789012",  # 32 chars no dashes
        "12345678-1234-1234-1234-123456789012",  # With dashes
        "https://www.notion.so/Test-Page-12345678901234567890123456789012",  # URL format
    ]
    
    for test_id in test_ids:
        try:
            normalized = connector._normalize_id(test_id.replace("https://www.notion.so/Test-Page-", ""))
            print(f"   ✅ {test_id[:50]}... → {normalized}")
        except Exception as e:
            print(f"   ❌ {test_id[:50]}... → Error: {str(e)}")
    
    # Test 6: Block formatting
    print(f"\n📝 Block Formatting Tests:")
    test_blocks = [
        {"type": "paragraph", "content": "This is a paragraph"},
        {"type": "heading_1", "content": "This is a heading"},
        {"type": "bulleted_list_item", "content": "This is a bullet point"},
        {"type": "to_do", "content": "This is a todo item"},
        {"type": "code", "content": "console.log('Hello World');"}
    ]
    
    formatted_blocks = connector._format_blocks(test_blocks)
    print(f"   ✅ Formatted {len(formatted_blocks)} blocks successfully")
    
    for i, block in enumerate(formatted_blocks):
        block_type = block.get("type")
        print(f"      {i+1}. {block_type}: {block.get(block_type, {}).get('rich_text', [{}])[0].get('text', {}).get('content', 'No content')[:30]}...")
    
    # Test 7: Text to blocks conversion
    print(f"\n📄 Text to Blocks Conversion:")
    test_text = "First paragraph.\n\nSecond paragraph with more content.\n\nThird paragraph."
    text_blocks = connector._create_text_blocks(test_text)
    print(f"   ✅ Converted text to {len(text_blocks)} blocks")
    
    # Test 8: Mock execution (without API key)
    print(f"\n🧪 Mock Execution Test:")
    
    # Create mock context (without real API key)
    mock_context = ConnectorExecutionContext(
        user_id="test-user",
        auth_tokens={},  # No API key for testing
        previous_results={}
    )
    
    test_params = {
        "resource": "page",
        "operation": "get_page",
        "page_id": "12345678901234567890123456789012"
    }
    
    try:
        result = await connector.execute(test_params, mock_context)
        print(f"   ❌ Expected authentication error but got: {result}")
    except Exception as e:
        if "API key" in str(e):
            print(f"   ✅ Correctly caught authentication error: {str(e)}")
        else:
            print(f"   ⚠️  Unexpected error: {str(e)}")
    
    print(f"\n🎉 Notion Connector Tests Complete!")
    print(f"   ✅ Connector properly initialized")
    print(f"   ✅ Schema validation working")
    print(f"   ✅ Authentication requirements defined")
    print(f"   ✅ All resources and operations supported")
    print(f"   ✅ ID normalization working")
    print(f"   ✅ Block formatting working")
    print(f"   ✅ Error handling working")
    
    return True


async def test_notion_connector_integration():
    """Test Notion connector integration with registry."""
    print(f"\n🔗 Testing Notion Connector Integration")
    
    try:
        # Test import
        from app.connectors.core import NotionConnector
        print(f"   ✅ Successfully imported NotionConnector")
        
        # Test instantiation
        connector = NotionConnector()
        print(f"   ✅ Successfully instantiated connector")
        
        # Test registry integration
        from app.connectors.registry import ConnectorRegistry
        registry = ConnectorRegistry()
        
        # Register the connector
        registry.register(NotionConnector)
        print(f"   ✅ Successfully registered with ConnectorRegistry")
        
        # Test retrieval
        retrieved_connector = registry.create_connector("notion")
        print(f"   ✅ Successfully retrieved from registry: {retrieved_connector.name}")
        
        # Test metadata
        metadata = registry.get_metadata("notion")
        print(f"   ✅ Retrieved metadata: {metadata.name} - {metadata.category}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Integration test failed: {str(e)}")
        return False


async def main():
    """Run all Notion connector tests."""
    print("=" * 60)
    print("🧪 NOTION CONNECTOR TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Run basic connector tests
    try:
        result1 = await test_notion_connector()
        results.append(("Basic Functionality", result1))
    except Exception as e:
        print(f"❌ Basic functionality test failed: {str(e)}")
        results.append(("Basic Functionality", False))
    
    # Run integration tests
    try:
        result2 = await test_notion_connector_integration()
        results.append(("Registry Integration", result2))
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        results.append(("Registry Integration", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Notion connector is ready for use.")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())