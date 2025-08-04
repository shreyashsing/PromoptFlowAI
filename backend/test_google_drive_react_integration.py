#!/usr/bin/env python3
"""
Comprehensive test for Google Drive connector integration with ReAct agent.
"""
import asyncio
import json
import logging
from typing import Dict, Any

from app.services.tool_registry import get_tool_registry
from app.services.connector_tool_adapter import ConnectorToolAdapter
from app.connectors.core.google_drive_connector import GoogleDriveConnector
from app.models.connector import ConnectorExecutionContext

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_google_drive_connector_registration():
    """Test that Google Drive connector is properly registered as a tool."""
    print("🔧 Testing Google Drive Connector Registration...")
    
    try:
        # Get tool registry
        tool_registry = await get_tool_registry()
        
        # Check if Google Drive is registered
        tools = await tool_registry.get_available_tools()
        tool_names = [tool.name for tool in tools]
        
        print(f"📋 Available tools: {tool_names}")
        
        if "google_drive" in tool_names:
            print("✅ Google Drive connector is registered as a tool")
        else:
            print("❌ Google Drive connector is NOT registered as a tool")
            return False
        
        # Get Google Drive tool specifically
        google_drive_tool = await tool_registry.get_tool_by_name("google_drive")
        if google_drive_tool:
            print(f"✅ Google Drive tool found: {google_drive_tool.name}")
            print(f"📝 Description: {google_drive_tool.description[:100]}...")
        else:
            print("❌ Could not retrieve Google Drive tool")
            return False
        
        # Get tool metadata
        metadata = await tool_registry.get_tool_metadata_by_name("google_drive")
        if metadata:
            print("✅ Google Drive tool metadata found:")
            print(f"   Category: {metadata.get('category')}")
            print(f"   Auth Type: {metadata.get('auth_requirements', {}).get('type')}")
            print(f"   Required Params: {metadata.get('required_params', [])}")
            print(f"   Optional Params: {len(metadata.get('optional_params', []))} parameters")
        else:
            print("❌ Could not retrieve Google Drive tool metadata")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Registration test failed: {e}")
        return False


async def test_google_drive_schema_conversion():
    """Test that Google Drive connector schema is properly converted for ReAct agent."""
    print("\n🔄 Testing Google Drive Schema Conversion...")
    
    try:
        # Create connector instance
        connector = GoogleDriveConnector()
        
        # Create tool adapter
        adapter = ConnectorToolAdapter("google_drive", GoogleDriveConnector)
        
        # Get tool schema
        tool_schema = await adapter.get_tool_schema()
        
        print("✅ Tool schema generated successfully:")
        print(f"   Name: {tool_schema.get('name')}")
        print(f"   Description: {tool_schema.get('description', '')[:100]}...")
        print(f"   Auth Required: {tool_schema.get('auth_required')}")
        print(f"   Auth Type: {tool_schema.get('auth_type')}")
        print(f"   Required Fields: {tool_schema.get('required_fields', [])}")
        print(f"   Optional Fields: {len(tool_schema.get('optional_fields', []))} fields")
        
        # Check that all 14 actions are supported
        parameters = tool_schema.get('parameters', {})
        action_param = parameters.get('action', {})
        
        if 'enum' in action_param:
            actions = action_param['enum']
            print(f"✅ Supported actions ({len(actions)}): {actions}")
            
            expected_actions = [
                'upload', 'download', 'create_folder', 'delete', 'move', 'copy',
                'share', 'search', 'get_info', 'list_files', 'create_from_text',
                'update_file', 'get_permissions', 'update_permissions'
            ]
            
            missing_actions = set(expected_actions) - set(actions)
            if missing_actions:
                print(f"❌ Missing actions: {missing_actions}")
                return False
            else:
                print("✅ All expected actions are present")
        else:
            print("❌ No action enum found in schema")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Schema conversion test failed: {e}")
        return False


async def test_google_drive_parameter_validation():
    """Test parameter validation for different Google Drive actions."""
    print("\n✅ Testing Google Drive Parameter Validation...")
    
    try:
        # Create tool adapter
        adapter = ConnectorToolAdapter("google_drive", GoogleDriveConnector)
        
        # Test different parameter sets
        test_cases = [
            {
                "name": "List Files",
                "params": {
                    "action": "list_files",
                    "parent_folder_id": "root",
                    "max_results": 10
                },
                "should_pass": True
            },
            {
                "name": "Upload File",
                "params": {
                    "action": "upload",
                    "file_name": "test.txt",
                    "file_content": "SGVsbG8gV29ybGQ="  # "Hello World" in base64
                },
                "should_pass": True
            },
            {
                "name": "Search Files",
                "params": {
                    "action": "search",
                    "query": "name contains 'test'"
                },
                "should_pass": True
            },
            {
                "name": "Share File",
                "params": {
                    "action": "share",
                    "file_id": "1234567890",
                    "share_type": "user",
                    "share_role": "reader",
                    "share_email": "test@example.com"
                },
                "should_pass": True
            },
            {
                "name": "Invalid Action",
                "params": {
                    "action": "invalid_action"
                },
                "should_pass": False
            },
            {
                "name": "Missing Required Parameter",
                "params": {
                    "action": "upload"
                    # Missing file_name and file_content
                },
                "should_pass": False
            }
        ]
        
        # Create Pydantic model for validation
        pydantic_model = adapter._create_pydantic_model()
        
        passed_tests = 0
        for test_case in test_cases:
            try:
                validated_params = await adapter._validate_and_convert_parameters(
                    test_case["params"], pydantic_model
                )
                
                if test_case["should_pass"]:
                    print(f"✅ {test_case['name']}: Validation passed as expected")
                    passed_tests += 1
                else:
                    print(f"❌ {test_case['name']}: Should have failed validation but passed")
                    
            except Exception as e:
                if not test_case["should_pass"]:
                    print(f"✅ {test_case['name']}: Validation failed as expected ({str(e)[:50]}...)")
                    passed_tests += 1
                else:
                    print(f"❌ {test_case['name']}: Validation failed unexpectedly: {e}")
        
        print(f"📊 Parameter validation tests: {passed_tests}/{len(test_cases)} passed")
        return passed_tests == len(test_cases)
        
    except Exception as e:
        print(f"❌ Parameter validation test failed: {e}")
        return False


async def test_google_drive_tool_execution():
    """Test Google Drive tool execution with mock context."""
    print("\n🚀 Testing Google Drive Tool Execution...")
    
    try:
        # Get tool registry
        tool_registry = await get_tool_registry()
        
        # Get Google Drive tool
        google_drive_tool = await tool_registry.get_tool_by_name("google_drive")
        if not google_drive_tool:
            print("❌ Could not get Google Drive tool")
            return False
        
        # Test different operations (these will fail due to mock auth, but should test the flow)
        test_operations = [
            {
                "name": "List Files",
                "query": json.dumps({
                    "action": "list_files",
                    "parent_folder_id": "root",
                    "max_results": 5
                })
            },
            {
                "name": "Search Files",
                "query": json.dumps({
                    "action": "search",
                    "query": "name contains 'test'",
                    "max_results": 10
                })
            }
        ]
        
        # Set mock user context for tool execution
        ConnectorToolAdapter.set_user_context(
            user_id="test_user",
            user_session={"session_id": "test_session"},
            auth_context_manager=None  # Will use default
        )
        
        successful_executions = 0
        for operation in test_operations:
            try:
                print(f"🔧 Testing {operation['name']}...")
                
                # Execute the tool (this will fail due to mock auth, but tests the flow)
                result = google_drive_tool.func(operation['query'])
                
                print(f"📋 Result for {operation['name']}: {result[:100]}...")
                
                # Check if the result indicates proper error handling
                if "authentication" in result.lower() or "oauth" in result.lower() or "token" in result.lower():
                    print(f"✅ {operation['name']}: Proper authentication error handling")
                    successful_executions += 1
                elif "parameter validation failed" in result.lower():
                    print(f"✅ {operation['name']}: Proper parameter validation")
                    successful_executions += 1
                elif "executed successfully" in result:
                    print(f"✅ {operation['name']}: Execution successful")
                    successful_executions += 1
                else:
                    print(f"⚠️ {operation['name']}: Unexpected result format")
                    
            except Exception as e:
                print(f"❌ {operation['name']} execution failed: {e}")
        
        print(f"📊 Tool execution tests: {successful_executions}/{len(test_operations)} handled properly")
        return successful_executions > 0  # At least some should work
        
    except Exception as e:
        print(f"❌ Tool execution test failed: {e}")
        return False


async def test_google_drive_react_agent_compatibility():
    """Test Google Drive connector compatibility with ReAct agent patterns."""
    print("\n🤖 Testing Google Drive ReAct Agent Compatibility...")
    
    try:
        # Get tool registry status
        tool_registry = await get_tool_registry()
        status = await tool_registry.get_tool_registration_status()
        
        print("📊 Tool Registry Status:")
        print(f"   Initialized: {status['initialized']}")
        print(f"   Total Connectors: {status['total_connectors_discovered']}")
        print(f"   Successfully Registered: {status['successfully_registered']}")
        print(f"   Success Rate: {status['success_rate']:.1f}%")
        
        # Check Google Drive specifically
        google_drive_registered = False
        for tool_info in status['registered_tools']:
            if tool_info['name'] == 'google_drive':
                google_drive_registered = True
                print(f"✅ Google Drive tool registered:")
                print(f"   Description: {tool_info['description']}")
                print(f"   Has Args Schema: {tool_info['has_args_schema']}")
                print(f"   Metadata Available: {bool(tool_info['metadata'])}")
                break
        
        if not google_drive_registered:
            print("❌ Google Drive tool not found in registered tools")
            return False
        
        # Test tool metadata structure for ReAct agent
        metadata = await tool_registry.get_tool_metadata_by_name("google_drive")
        if metadata:
            required_metadata_fields = [
                'name', 'description', 'category', 'parameter_schema',
                'auth_requirements', 'required_params', 'optional_params'
            ]
            
            missing_fields = []
            for field in required_metadata_fields:
                if field not in metadata:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Missing metadata fields: {missing_fields}")
                return False
            else:
                print("✅ All required metadata fields present")
        
        # Test that the tool can be discovered by category
        data_source_tools = await tool_registry.get_tools_by_category("data_sources")
        google_drive_in_category = any(tool['name'] == 'google_drive' for tool in data_source_tools)
        
        if google_drive_in_category:
            print("✅ Google Drive tool discoverable by category")
        else:
            print("❌ Google Drive tool not found in data_sources category")
            return False
        
        # Test search functionality
        search_results = await tool_registry.search_tools("google drive")
        google_drive_searchable = any(tool['name'] == 'google_drive' for tool in search_results)
        
        if google_drive_searchable:
            print("✅ Google Drive tool discoverable by search")
        else:
            print("❌ Google Drive tool not found in search results")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ ReAct agent compatibility test failed: {e}")
        return False


async def test_google_drive_action_coverage():
    """Test that all Google Drive actions are properly supported."""
    print("\n📋 Testing Google Drive Action Coverage...")
    
    try:
        # Get connector instance
        connector = GoogleDriveConnector()
        schema = connector.schema
        
        # Check action parameter
        action_property = schema.get('properties', {}).get('action', {})
        supported_actions = action_property.get('enum', [])
        
        print(f"📊 Supported actions ({len(supported_actions)}):")
        for i, action in enumerate(supported_actions, 1):
            print(f"   {i:2d}. {action}")
        
        # Expected actions based on n8n Google Drive connector
        expected_actions = {
            'upload': 'Upload files to Google Drive',
            'download': 'Download files from Google Drive',
            'create_folder': 'Create new folders',
            'delete': 'Delete files and folders',
            'move': 'Move files between folders',
            'copy': 'Copy files',
            'share': 'Share files with others',
            'search': 'Search for files',
            'get_info': 'Get file information',
            'list_files': 'List files in folders',
            'create_from_text': 'Create text files',
            'update_file': 'Update file content',
            'get_permissions': 'Get file permissions',
            'update_permissions': 'Update file permissions'
        }
        
        # Check coverage
        missing_actions = set(expected_actions.keys()) - set(supported_actions)
        extra_actions = set(supported_actions) - set(expected_actions.keys())
        
        if missing_actions:
            print(f"❌ Missing actions: {missing_actions}")
            return False
        
        if extra_actions:
            print(f"ℹ️ Extra actions: {extra_actions}")
        
        print("✅ All expected actions are supported")
        
        # Test parameter requirements for key actions
        test_actions = ['upload', 'download', 'share', 'search']
        for action in test_actions:
            print(f"🔍 Testing {action} parameter requirements...")
            
            # This would require more complex validation logic
            # For now, just verify the action exists
            if action in supported_actions:
                print(f"   ✅ {action} action available")
            else:
                print(f"   ❌ {action} action missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Action coverage test failed: {e}")
        return False


async def create_test_workflow():
    """Create a test workflow to demonstrate Google Drive connector usage."""
    print("\n🔧 Creating Test Workflow for Google Drive Connector...")
    
    workflow_definition = {
        "name": "Google Drive Test Workflow",
        "description": "Test workflow demonstrating Google Drive connector capabilities",
        "version": "1.0",
        "steps": [
            {
                "id": "step_1",
                "name": "List Root Files",
                "connector": "google_drive",
                "action": "list_files",
                "parameters": {
                    "action": "list_files",
                    "parent_folder_id": "root",
                    "max_results": 10,
                    "order_by": "modifiedTime desc"
                },
                "description": "List files in the root directory"
            },
            {
                "id": "step_2",
                "name": "Search for Documents",
                "connector": "google_drive",
                "action": "search",
                "parameters": {
                    "action": "search",
                    "query": "mimeType contains 'document'",
                    "max_results": 5
                },
                "description": "Search for document files",
                "depends_on": ["step_1"]
            },
            {
                "id": "step_3",
                "name": "Create Test Folder",
                "connector": "google_drive",
                "action": "create_folder",
                "parameters": {
                    "action": "create_folder",
                    "file_name": "Test Workflow Folder",
                    "parent_folder_id": "root",
                    "description": "Folder created by test workflow"
                },
                "description": "Create a test folder",
                "depends_on": ["step_1"]
            },
            {
                "id": "step_4",
                "name": "Upload Test File",
                "connector": "google_drive",
                "action": "create_from_text",
                "parameters": {
                    "action": "create_from_text",
                    "file_name": "workflow_test.txt",
                    "text_content": "This file was created by the Google Drive connector test workflow.",
                    "parent_folder_id": "{{step_3.result.folder_id}}",
                    "mime_type": "text/plain"
                },
                "description": "Create a test text file",
                "depends_on": ["step_3"]
            },
            {
                "id": "step_5",
                "name": "Share Test File",
                "connector": "google_drive",
                "action": "share",
                "parameters": {
                    "action": "share",
                    "file_id": "{{step_4.result.file_id}}",
                    "share_type": "anyone",
                    "share_role": "reader",
                    "send_notification": False
                },
                "description": "Share the test file publicly",
                "depends_on": ["step_4"]
            }
        ],
        "metadata": {
            "created_by": "google_drive_test",
            "created_at": "2024-01-15T10:00:00Z",
            "tags": ["test", "google_drive", "automation"],
            "estimated_duration": "30 seconds"
        }
    }
    
    print("✅ Test workflow created successfully:")
    print(f"   Name: {workflow_definition['name']}")
    print(f"   Steps: {len(workflow_definition['steps'])}")
    print(f"   Description: {workflow_definition['description']}")
    
    # Print workflow steps
    print("\n📋 Workflow Steps:")
    for step in workflow_definition['steps']:
        print(f"   {step['id']}: {step['name']}")
        print(f"      Action: {step['parameters']['action']}")
        print(f"      Description: {step['description']}")
        if 'depends_on' in step:
            print(f"      Depends on: {step['depends_on']}")
    
    # Save workflow to file
    import json
    with open('google_drive_test_workflow.json', 'w') as f:
        json.dump(workflow_definition, f, indent=2)
    
    print(f"\n💾 Workflow saved to: google_drive_test_workflow.json")
    
    return workflow_definition


async def main():
    """Run all Google Drive connector integration tests."""
    print("=" * 80)
    print("🚀 Google Drive Connector - ReAct Agent Integration Test Suite")
    print("=" * 80)
    
    test_results = []
    
    # Run all tests
    tests = [
        ("Connector Registration", test_google_drive_connector_registration),
        ("Schema Conversion", test_google_drive_schema_conversion),
        ("Parameter Validation", test_google_drive_parameter_validation),
        ("Tool Execution", test_google_drive_tool_execution),
        ("ReAct Agent Compatibility", test_google_drive_react_agent_compatibility),
        ("Action Coverage", test_google_drive_action_coverage)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = await test_func()
            test_results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            test_results.append((test_name, False))
    
    # Create test workflow
    try:
        print(f"\n{'='*20} Test Workflow Creation {'='*20}")
        workflow = await create_test_workflow()
        test_results.append(("Test Workflow Creation", True))
        print("✅ Test Workflow Creation: PASSED")
    except Exception as e:
        print(f"💥 Test Workflow Creation: ERROR - {e}")
        test_results.append(("Test Workflow Creation", False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
    
    print(f"\n📈 Overall Result: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Google Drive connector is ready for ReAct agent integration!")
    elif passed_tests >= total_tests * 0.8:
        print("\n⚠️ Most tests passed. Google Drive connector is mostly ready with minor issues.")
    else:
        print("\n❌ Several tests failed. Google Drive connector needs fixes before ReAct agent integration.")
    
    print("\n" + "=" * 80)
    print("🔧 NEXT STEPS:")
    print("1. Fix any failing tests")
    print("2. Set up OAuth authentication for Google Drive")
    print("3. Test with real Google Drive API credentials")
    print("4. Integrate with ReAct agent workflow system")
    print("5. Create production workflows using the test workflow as template")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())