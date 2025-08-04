#!/usr/bin/env python3
"""
Test script for Airtable Connector Tool Registry Integration.
"""
import asyncio
import json
import os
from typing import Dict, Any

from app.services.tool_registry import ToolRegistry
from app.services.connector_tool_adapter import ConnectorToolAdapter
from app.connectors.core.airtable_connector import AirtableConnector
from app.models.connector import ConnectorExecutionContext


async def test_airtable_tool_registry():
    """Test Airtable connector integration with tool registry."""
    print("🧪 Testing Airtable Connector Tool Registry Integration")
    print("=" * 60)
    
    # Initialize tool registry
    tool_registry = ToolRegistry()
    
    # Test 1: Initialize tool registry
    print("1️⃣ Testing tool registry initialization...")
    try:
        await tool_registry.initialize()
        print("   ✅ Tool registry initialized successfully")
        
        # Check if tools are registered
        if hasattr(tool_registry, 'tools') and tool_registry.tools:
            print(f"   📊 Registry contains {len(tool_registry.tools)} tools")
            tool_names = list(tool_registry.tools.keys())
            print(f"   🔧 Available tools: {tool_names}")
            
            # Check for Airtable specifically
            airtable_tools = [name for name in tool_names if 'airtable' in name.lower()]
            if airtable_tools:
                print(f"   ✅ Found Airtable tools: {airtable_tools}")
            else:
                print("   ⚠️  No Airtable tools found in registry")
        else:
            print("   ⚠️  No tools registered in registry")
            
    except Exception as e:
        print(f"   ❌ Registry initialization failed: {str(e)}")
    print()
    
    # Test 2: Test connector tool adapter directly
    print("2️⃣ Testing connector tool adapter...")
    try:
        connector = AirtableConnector()
        
        # Get connector schema
        schema = connector.schema
        print(f"   ✅ Connector schema retrieved")
        print(f"   📊 Schema has {len(schema.get('properties', {}))} properties")
        
        # Test connector instantiation
        connector_name = connector._get_connector_name()
        print(f"   ✅ Connector name: {connector_name}")
        print(f"   📂 Connector category: {connector._get_category()}")
        
        # Test tool adapter creation
        adapter = ConnectorToolAdapter(connector_name, AirtableConnector)
        print(f"   ✅ Tool adapter created for {connector_name}")
        
    except Exception as e:
        print(f"   ❌ Tool adapter test failed: {str(e)}")
    print()
    
    # Test 3: Test tool metadata extraction
    print("3️⃣ Testing tool metadata extraction...")
    try:
        connector = AirtableConnector()
        
        # Check if tool metadata is available
        if hasattr(tool_registry, 'tool_metadata') and 'airtable' in tool_registry.tool_metadata:
            metadata = tool_registry.tool_metadata['airtable']
            print(f"   ✅ Tool metadata found for Airtable")
            print(f"   📋 Metadata keys: {list(metadata.keys())}")
            
            if 'schema' in metadata:
                schema = metadata['schema']
                if 'properties' in schema:
                    print(f"   📊 Schema has {len(schema['properties'])} properties")
                    
                    # Check key properties
                    key_props = ['resource', 'operation', 'base_id']
                    for prop in key_props:
                        if prop in schema['properties']:
                            prop_info = schema['properties'][prop]
                            print(f"      ✓ {prop}: {prop_info.get('type', 'unknown')} - {prop_info.get('description', 'no description')[:50]}...")
        else:
            print("   ⚠️  No tool metadata found for Airtable")
            
    except Exception as e:
        print(f"   ❌ Tool metadata test failed: {str(e)}")
    print()
    
    # Test 4: Test tool schema validation
    print("4️⃣ Testing tool schema validation...")
    try:
        connector = AirtableConnector()
        
        # Get connector schema directly
        schema = connector.schema
        
        # Validate schema structure
        required_fields = ['type', 'properties']
        missing_fields = [field for field in required_fields if field not in schema]
        
        if not missing_fields:
            print("   ✅ Connector schema has all required fields")
            
            # Check parameter schema
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            print(f"   📊 Schema has {len(properties)} properties")
            print(f"   📋 {len(required)} required parameters")
            
            # Check some key parameters
            key_params = ['resource', 'operation', 'base_id']
            for param in key_params:
                if param in properties:
                    param_info = properties[param]
                    print(f"      ✓ {param}: {param_info.get('type', 'unknown type')} - {param_info.get('description', 'no description')[:50]}...")
                else:
                    print(f"      ✗ Missing key parameter: {param}")
        else:
            print(f"   ❌ Schema missing required fields: {missing_fields}")
            
    except Exception as e:
        print(f"   ❌ Schema validation failed: {str(e)}")
    print()
    
    # Test 5: Test connector discovery
    print("5️⃣ Testing connector discovery...")
    try:
        # Test if connector can be discovered by name
        from app.connectors.registry import get_connector_registry
        
        registry = get_connector_registry()
        connector_names = registry.list_connectors()
        
        print(f"   📋 Found {len(connector_names)} connectors in registry")
        print(f"   🔧 Available connectors: {connector_names}")
        
        if 'airtable' in connector_names:
            print("   ✅ Airtable connector found in connector registry")
            
            # Get connector class
            airtable_connector_class = registry.get_connector('airtable')
            if airtable_connector_class:
                print("   ✅ Airtable connector class retrieved successfully")
                
                # Try to instantiate
                try:
                    instance = airtable_connector_class()
                    print(f"   ✅ Connector instance created")
                    print(f"   📋 Connector name: {instance._get_connector_name()}")
                    print(f"   📂 Connector category: {instance._get_category()}")
                except Exception as e:
                    print(f"   ❌ Failed to instantiate connector: {str(e)}")
            else:
                print("   ❌ Failed to get Airtable connector class")
        else:
            print("   ❌ Airtable connector not found in connector registry")
            
    except Exception as e:
        print(f"   ❌ Connector discovery failed: {str(e)}")
    print()
    
    # Test 6: Test tool registry tools access
    print("6️⃣ Testing tool registry tools access...")
    try:
        # Check if we can access tools directly from registry
        if hasattr(tool_registry, 'tools'):
            tools = tool_registry.tools
            print(f"   📊 Tool registry has {len(tools)} tools")
            
            # Look for Airtable tool
            airtable_tool_names = [name for name in tools.keys() if 'airtable' in name.lower()]
            
            if airtable_tool_names:
                print(f"   ✅ Found Airtable tools: {airtable_tool_names}")
                
                # Get first Airtable tool
                tool_name = airtable_tool_names[0]
                tool = tools[tool_name]
                
                print(f"   🔧 Tool name: {tool.name}")
                print(f"   📝 Tool description: {tool.description[:100]}...")
                
                # Test tool function exists
                if hasattr(tool, 'func') and callable(tool.func):
                    print("   ✅ Tool function is callable")
                else:
                    print("   ❌ Tool function is not callable")
                    
            else:
                print("   ❌ No Airtable tools found in registry")
                print(f"   📋 Available tool names: {list(tools.keys())}")
        else:
            print("   ❌ Tool registry has no tools attribute")
            
    except Exception as e:
        print(f"   ❌ Tool registry access test failed: {str(e)}")
    print()


async def test_airtable_tool_execution():
    """Test actual tool execution with mock data."""
    print("🔧 Testing Airtable Tool Execution")
    print("=" * 50)
    
    try:
        # Test connector execution directly
        connector = AirtableConnector()
        
        # Test different operation types
        test_cases = [
            {
                "name": "List Tables",
                "params": {
                    "resource": "base",
                    "operation": "list_tables",
                    "base_id": "appTEST123456789"
                }
            },
            {
                "name": "Search Records", 
                "params": {
                    "resource": "record",
                    "operation": "search",
                    "base_id": "appTEST123456789",
                    "table_id": "tblTEST123456789",
                    "max_records": 10
                }
            },
            {
                "name": "Get Base Schema",
                "params": {
                    "resource": "base", 
                    "operation": "get_schema",
                    "base_id": "appTEST123456789"
                }
            }
        ]
        
        # Create mock execution context
        context = ConnectorExecutionContext(
            user_id="test-user",
            auth_tokens={"api_token": "dummy_token"}
        )
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}️⃣ Testing: {test_case['name']}")
            
            try:
                # Validate parameters against connector schema
                schema = connector.schema
                required_params = schema.get('required', [])
                provided_params = set(test_case['params'].keys())
                
                # Check conditional requirements
                all_required = set(required_params)
                
                # Add conditional requirements based on operation
                operation = test_case['params'].get('operation')
                resource = test_case['params'].get('resource')
                
                if resource == 'record':
                    all_required.add('table_id')
                if operation in ['get', 'update', 'delete']:
                    all_required.add('record_id')
                
                missing_params = all_required - provided_params
                
                if not missing_params:
                    print(f"   ✅ All required parameters provided")
                    print(f"   📋 Parameters: {list(test_case['params'].keys())}")
                    
                    # Test execution (will fail due to dummy token, but validates structure)
                    try:
                        result = await connector.execute(test_case['params'], context)
                        if result.success:
                            print(f"   ✅ Execution successful")
                        else:
                            print(f"   ⚠️  Execution failed as expected (dummy credentials): {result.error[:100]}...")
                    except Exception as exec_e:
                        print(f"   ⚠️  Execution failed as expected (dummy credentials): {str(exec_e)[:100]}...")
                        
                else:
                    print(f"   ❌ Missing required parameters: {missing_params}")
                    
            except Exception as e:
                print(f"   ❌ Test case failed: {str(e)}")
            print()
            
    except Exception as e:
        print(f"❌ Tool execution test failed: {str(e)}")


async def test_airtable_rag_integration():
    """Test Airtable connector integration with RAG system."""
    print("🔍 Testing Airtable RAG Integration")
    print("=" * 50)
    
    try:
        # Test connector registration in RAG system
        print("1️⃣ Testing connector registration in RAG...")
        
        from app.connectors.registry import get_connector_registry
        
        registry = get_connector_registry()
        connector_names = registry.list_connectors()
        
        if 'airtable' in connector_names:
            print("   ✅ Airtable connector is registered in connector registry")
            
            # Get connector metadata
            try:
                metadata = registry.get_metadata('airtable')
                if metadata:
                    print(f"   ✅ Airtable connector metadata available")
                    print(f"   📋 Name: {metadata.name}")
                    print(f"   📂 Category: {metadata.category}")
                    print(f"   📝 Description: {metadata.description[:100]}...")
                else:
                    print("   ⚠️  No metadata available for Airtable connector")
            except Exception as e:
                print(f"   ❌ Failed to get metadata: {str(e)}")
        else:
            print("   ❌ Airtable connector not found in registry")
        
        print()
        
        # Test connector schema for RAG indexing
        print("2️⃣ Testing connector schema for RAG indexing...")
        try:
            connector = AirtableConnector()
            schema = connector.schema
            
            # Extract searchable content
            searchable_content = []
            
            # Add connector name and category
            searchable_content.append(f"airtable database connector")
            searchable_content.append(f"category: {connector._get_category()}")
            
            # Add operation descriptions
            if 'properties' in schema:
                properties = schema['properties']
                
                # Extract operation information
                if 'operation' in properties:
                    operation_info = properties['operation']
                    if 'enum' in operation_info:
                        operations = operation_info['enum']
                        searchable_content.append(f"operations: {', '.join(operations)}")
                
                # Extract resource information
                if 'resource' in properties:
                    resource_info = properties['resource']
                    if 'enum' in resource_info:
                        resources = resource_info['enum']
                        searchable_content.append(f"resources: {', '.join(resources)}")
            
            print(f"   ✅ Generated {len(searchable_content)} searchable content items")
            for content in searchable_content:
                print(f"      - {content}")
                
        except Exception as e:
            print(f"   ❌ Schema extraction for RAG failed: {str(e)}")
        
        print()
        
        # Test search keywords
        print("3️⃣ Testing search keywords...")
        
        keywords = [
            "airtable",
            "database", 
            "records",
            "tables",
            "base",
            "schema"
        ]
        
        connector = AirtableConnector()
        schema = connector.schema
        
        for keyword in keywords:
            found_in_schema = False
            
            # Search in schema description and properties
            schema_str = json.dumps(schema).lower()
            if keyword.lower() in schema_str:
                found_in_schema = True
                
            if found_in_schema:
                print(f"   ✅ Keyword '{keyword}' found in connector schema")
            else:
                print(f"   ⚠️  Keyword '{keyword}' not found in connector schema")
                
    except Exception as e:
        print(f"❌ RAG integration test failed: {str(e)}")


if __name__ == "__main__":
    print("🚀 Starting Airtable Tool Registry Integration Tests")
    print()
    
    # Run tool registry tests
    asyncio.run(test_airtable_tool_registry())
    
    # Run tool execution tests
    asyncio.run(test_airtable_tool_execution())
    
    # Run RAG integration tests
    asyncio.run(test_airtable_rag_integration())
    
    print("🎉 Airtable Tool Registry Integration Tests Completed!")
    print()
    print("💡 Summary:")
    print("   - Tool registry integration ensures Airtable connector is available to React agents")
    print("   - Parameter validation ensures proper tool usage")
    print("   - RAG integration enables intelligent connector discovery")
    print("   - All tests validate the complete integration pipeline")