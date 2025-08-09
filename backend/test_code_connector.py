#!/usr/bin/env python3
"""
Test script for Code Connector functionality.
"""
import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.connectors.core.code_connector import CodeConnector
from app.models.connector import ConnectorExecutionContext


async def test_code_connector():
    """Test Code connector functionality."""
    print("🚀 Testing Code Connector...")
    
    connector = CodeConnector()
    
    # Test 1: Basic JavaScript execution (all items)
    print("\n📝 Test 1: JavaScript - Run Once for All Items")
    try:
        params = {
            "language": "javascript",
            "mode": "runOnceForAllItems",
            "code": """
// Transform all items by adding a processed flag
return items.map(item => ({
    json: {
        ...item.json,
        processed: true,
        timestamp: new Date().toISOString()
    }
}));
""",
            "timeout": 30,
            "safe_mode": True
        }
        
        context = ConnectorExecutionContext(
            user_id="test-user",
            workflow_id="test-workflow",
            previous_results={
                "items": [
                    {"json": {"name": "John", "age": 30}},
                    {"json": {"name": "Jane", "age": 25}}
                ]
            }
        )
        
        result = await connector.execute(params, context)
        
        if result.success:
            print("   ✅ JavaScript all items execution successful")
            print(f"   📊 Items processed: {result.metadata.get('items_processed', 0)}")
            print(f"   ⏱️ Execution time: {result.metadata.get('execution_time', 0):.3f}s")
            if result.data.get("items"):
                print(f"   📄 Result items: {len(result.data['items'])}")
        else:
            print(f"   ❌ JavaScript all items execution failed: {result.error}")
            
    except Exception as e:
        print(f"   ❌ JavaScript all items test failed: {str(e)}")
    
    # Test 2: JavaScript execution (each item)
    print("\n📝 Test 2: JavaScript - Run Once for Each Item")
    try:
        params = {
            "language": "javascript",
            "mode": "runOnceForEachItem", 
            "code": """
// Process individual item
const result = {
    json: {
        ...item.json,
        processed_individually: true,
        double_age: item.json.age * 2
    }
};
return result;
""",
            "timeout": 30,
            "safe_mode": True
        }
        
        result = await connector.execute(params, context)
        
        if result.success:
            print("   ✅ JavaScript each item execution successful")
            print(f"   📊 Items processed: {result.metadata.get('items_processed', 0)}")
            if result.data.get("items"):
                print(f"   📄 Result items: {len(result.data['items'])}")
        else:
            print(f"   ❌ JavaScript each item execution failed: {result.error}")
            
    except Exception as e:
        print(f"   ❌ JavaScript each item test failed: {str(e)}")
    
    # Test 3: Python execution (all items)
    print("\n📝 Test 3: Python - Run Once for All Items")
    try:
        params = {
            "language": "python",
            "mode": "runOnceForAllItems",
            "code": """
# Transform all items using Python
result = []
for item in items:
    new_item = {
        "json": {
            **item["json"],
            "processed_with_python": True,
            "name_length": len(item["json"].get("name", ""))
        }
    }
    result.append(new_item)

print(f"Processed {len(result)} items with Python")
""",
            "timeout": 30,
            "safe_mode": True
        }
        
        result = await connector.execute(params, context)
        
        if result.success:
            print("   ✅ Python all items execution successful")
            print(f"   📊 Items processed: {result.metadata.get('items_processed', 0)}")
            if result.data.get("console_output"):
                print(f"   📝 Console output: {result.data['console_output']}")
        else:
            print(f"   ❌ Python all items execution failed: {result.error}")
            
    except Exception as e:
        print(f"   ❌ Python all items test failed: {str(e)}")
    
    # Test 4: Python execution (each item)
    print("\n📝 Test 4: Python - Run Once for Each Item")
    try:
        params = {
            "language": "python",
            "mode": "runOnceForEachItem",
            "code": """
# Process individual item with Python
result = {
    "json": {
        **item["json"],
        "processed_individually_python": True,
        "age_category": "adult" if item["json"]["age"] >= 18 else "minor"
    }
}

print(f"Processed item: {item['json']['name']}")
""",
            "timeout": 30,
            "safe_mode": True
        }
        
        result = await connector.execute(params, context)
        
        if result.success:
            print("   ✅ Python each item execution successful")
            print(f"   📊 Items processed: {result.metadata.get('items_processed', 0)}")
            if result.data.get("console_output"):
                print(f"   📝 Console output: {result.data['console_output']}")
        else:
            print(f"   ❌ Python each item execution failed: {result.error}")
            
    except Exception as e:
        print(f"   ❌ Python each item test failed: {str(e)}")
    
    # Test 5: Code validation (should fail)
    print("\n📝 Test 5: Code Validation - Dangerous Code")
    try:
        params = {
            "language": "javascript",
            "mode": "runOnceForAllItems",
            "code": """
const fs = require('fs');
fs.readFileSync('/etc/passwd');
""",
            "timeout": 30,
            "safe_mode": True
        }
        
        result = await connector.execute(params, context)
        
        if result.success:
            print("   ❌ Dangerous code validation failed - should have been blocked")
        else:
            print("   ✅ Dangerous code properly blocked")
            print(f"   🛡️ Error: {result.error}")
            
    except Exception as e:
        print(f"   ✅ Dangerous code properly blocked with exception: {str(e)}")
    
    # Test 6: Syntax error handling
    print("\n📝 Test 6: Syntax Error Handling")
    try:
        params = {
            "language": "python",
            "mode": "runOnceForAllItems",
            "code": """
# Invalid Python syntax
if True
    print("Missing colon")
""",
            "timeout": 30,
            "safe_mode": True
        }
        
        result = await connector.execute(params, context)
        
        if result.success:
            print("   ❌ Syntax error validation failed - should have been caught")
        else:
            print("   ✅ Syntax error properly caught")
            print(f"   🐛 Error: {result.error}")
            
    except Exception as e:
        print(f"   ✅ Syntax error properly caught with exception: {str(e)}")
    
    # Test 7: Connector metadata
    print("\n📝 Test 7: Connector Metadata")
    try:
        print(f"   📛 Name: {connector.name}")
        print(f"   📝 Description: {connector.description}")
        print(f"   🏷️ Category: {connector.category}")
        print(f"   🔧 Capabilities: {connector.get_capabilities()}")
        print(f"   💡 Example prompts: {len(connector.get_example_prompts())} prompts")
        print(f"   📋 Use cases: {len(connector.get_use_cases())} use cases")
        
        # Test auth requirements
        auth_req = await connector.get_auth_requirements()
        print(f"   🔐 Auth required: {auth_req.type}")
        
        # Test parameter validation
        valid_params = {
            "language": "javascript",
            "code": "return items;",
            "mode": "runOnceForAllItems"
        }
        is_valid = await connector.validate_params(valid_params)
        print(f"   ✅ Parameter validation: {is_valid}")
        
    except Exception as e:
        print(f"   ❌ Metadata test failed: {str(e)}")
    
    print("\n🎉 Code Connector testing completed!")


async def test_parameter_suggestions():
    """Test parameter suggestion functionality."""
    print("\n🧠 Testing Parameter Suggestions...")
    
    connector = CodeConnector()
    
    test_prompts = [
        "Execute JavaScript code to transform data",
        "Run Python script to process each item individually", 
        "Transform JSON data using custom JavaScript logic",
        "Execute Python code with network access to fetch data",
        "Run code to read files from the system"
    ]
    
    for prompt in test_prompts:
        print(f"\n📝 Prompt: '{prompt}'")
        suggestions = connector.generate_parameter_suggestions(prompt)
        print(f"   💡 Suggestions: {json.dumps(suggestions, indent=2)}")


async def main():
    """Main test function."""
    await test_code_connector()
    await test_parameter_suggestions()


if __name__ == "__main__":
    asyncio.run(main())