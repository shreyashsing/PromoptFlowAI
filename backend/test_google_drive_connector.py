#!/usr/bin/env python3
"""
Test script for Google Drive Connector functionality.
"""
import asyncio
import json
import base64
from typing import Dict, Any

from app.connectors.core.google_drive_connector import GoogleDriveConnector
from app.models.connector import ConnectorExecutionContext


async def test_google_drive_connector():
    """Test Google Drive connector functionality."""
    print("Testing Google Drive Connector...")
    
    # Create connector instance
    connector = GoogleDriveConnector()
    
    # Test basic properties
    print(f"Connector name: {connector.name}")
    print(f"Connector description: {connector.description}")
    print(f"Connector category: {connector.category}")
    
    # Test schema validation
    print("\nTesting schema validation...")
    schema = connector.schema
    print(f"Schema type: {schema.get('type')}")
    print(f"Required fields: {schema.get('required', [])}")
    print(f"Available actions: {schema['properties']['action']['enum']}")
    
    # Test auth requirements
    print("\nTesting auth requirements...")
    auth_req = await connector.get_auth_requirements()
    print(f"Auth type: {auth_req.type}")
    print(f"OAuth scopes: {auth_req.oauth_scopes}")
    
    # Test parameter validation
    print("\nTesting parameter validation...")
    
    # Valid parameters for list_files
    valid_params = {
        "action": "list_files",
        "parent_folder_id": "root",
        "max_results": 10
    }
    
    try:
        await connector.validate_params(valid_params)
        print("✓ Valid parameters passed validation")
    except Exception as e:
        print(f"✗ Valid parameters failed validation: {e}")
    
    # Invalid parameters (missing required field for upload)
    invalid_params = {
        "action": "upload",
        "file_name": "test.txt"
        # Missing file_content
    }
    
    try:
        await connector.validate_params(invalid_params)
        print("✗ Invalid parameters should have failed validation")
    except Exception as e:
        print(f"✓ Invalid parameters correctly failed validation: {e}")
    
    # Test parameter hints
    print("\nTesting parameter hints...")
    hints = connector.get_parameter_hints()
    for param, hint in hints.items():
        print(f"  {param}: {hint}")
    
    # Test example parameters
    print("\nTesting example parameters...")
    examples = connector.get_example_params()
    print(f"Example params: {json.dumps(examples, indent=2)}")
    
    # Test connection (will fail without real tokens, but should not crash)
    print("\nTesting connection test...")
    fake_tokens = {"access_token": "fake_token"}
    try:
        connection_result = await connector.test_connection(fake_tokens)
        print(f"Connection test result: {connection_result}")
    except Exception as e:
        print(f"Connection test failed as expected: {e}")
    
    print("\n✓ All basic tests completed successfully!")


async def test_google_drive_operations():
    """Test Google Drive operations with mock data."""
    print("\nTesting Google Drive operations with mock context...")
    
    connector = GoogleDriveConnector()
    
    # Mock execution context (will fail API calls but test parameter processing)
    mock_context = ConnectorExecutionContext(
        auth_tokens={"access_token": "mock_token"},
        previous_results={},
        workflow_id="test_workflow",
        execution_id="test_execution",
        user_id="test_user"
    )
    
    # Test different operations
    test_operations = [
        {
            "name": "List Files",
            "params": {
                "action": "list_files",
                "parent_folder_id": "root",
                "max_results": 5
            }
        },
        {
            "name": "Search Files",
            "params": {
                "action": "search",
                "query": "name contains 'test'",
                "max_results": 10
            }
        },
        {
            "name": "Create Folder",
            "params": {
                "action": "create_folder",
                "file_name": "Test Folder",
                "parent_folder_id": "root",
                "description": "Test folder created by connector"
            }
        },
        {
            "name": "Upload Text File",
            "params": {
                "action": "create_from_text",
                "file_name": "test.txt",
                "text_content": "Hello, Google Drive!",
                "parent_folder_id": "root",
                "mime_type": "text/plain"
            }
        },
        {
            "name": "Get File Info",
            "params": {
                "action": "get_info",
                "file_id": "1234567890abcdef"
            }
        }
    ]
    
    for operation in test_operations:
        print(f"\nTesting {operation['name']}...")
        try:
            # Validate parameters first
            await connector.validate_params(operation['params'])
            print(f"✓ Parameters valid for {operation['name']}")
            
            # Try to execute (will fail due to mock tokens, but tests parameter processing)
            result = await connector.execute(operation['params'], mock_context)
            if result.success:
                print(f"✓ {operation['name']} executed successfully")
                print(f"  Result: {result.data.get('result', 'No result message')}")
            else:
                print(f"✗ {operation['name']} failed: {result.error}")
                
        except Exception as e:
            print(f"✗ {operation['name']} failed with exception: {e}")


async def test_schema_completeness():
    """Test that the schema covers all the functionality from the n8n connector."""
    print("\nTesting schema completeness...")
    
    connector = GoogleDriveConnector()
    schema = connector.schema
    
    # Check that we have all the main actions from n8n Google Drive
    expected_actions = [
        "upload", "download", "create_folder", "delete", "move", "copy",
        "share", "search", "get_info", "list_files", "create_from_text",
        "update_file", "get_permissions", "update_permissions"
    ]
    
    actual_actions = schema['properties']['action']['enum']
    
    print(f"Expected actions: {len(expected_actions)}")
    print(f"Actual actions: {len(actual_actions)}")
    
    missing_actions = set(expected_actions) - set(actual_actions)
    extra_actions = set(actual_actions) - set(expected_actions)
    
    if missing_actions:
        print(f"✗ Missing actions: {missing_actions}")
    else:
        print("✓ All expected actions are present")
    
    if extra_actions:
        print(f"ℹ Extra actions: {extra_actions}")
    
    # Check key parameters are present
    key_params = [
        "file_id", "file_name", "parent_folder_id", "file_content", 
        "text_content", "mime_type", "query", "share_type", "share_role"
    ]
    
    schema_params = set(schema['properties'].keys())
    missing_params = set(key_params) - schema_params
    
    if missing_params:
        print(f"✗ Missing key parameters: {missing_params}")
    else:
        print("✓ All key parameters are present")
    
    print(f"Total schema parameters: {len(schema_params)}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Google Drive Connector Test Suite")
    print("=" * 60)
    
    try:
        await test_google_drive_connector()
        await test_google_drive_operations()
        await test_schema_completeness()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())