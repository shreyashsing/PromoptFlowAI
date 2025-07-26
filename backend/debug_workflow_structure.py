#!/usr/bin/env python3
"""
Debug workflow database structure to understand how data is stored.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase_client
import json


async def debug_workflow_structure():
    """Debug the actual workflow database structure."""
    print("🔍 Debugging Workflow Database Structure")
    print("=" * 50)
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # 1. Check the most recent workflow
        print("1. Fetching the most recent workflow...")
        result = supabase.table("workflows").select("*").order("created_at", desc=True).limit(1).execute()
        
        if not result.data:
            print("   ❌ No workflows found!")
            return
            
        workflow = result.data[0]
        print(f"   ✅ Found workflow: {workflow.get('name', 'UNNAMED')}")
        print(f"   📅 Created: {workflow.get('created_at', 'N/A')}")
        
        # 2. Print all available fields
        print(f"\n2. Available workflow fields:")
        for key, value in workflow.items():
            if isinstance(value, (dict, list)):
                print(f"   📋 {key}: {type(value)} with {len(value) if hasattr(value, '__len__') else 'N/A'} items")
            else:
                print(f"   📋 {key}: {type(value)} = {str(value)[:100]}...")
        
        # 3. Examine workflow_data structure
        workflow_data = workflow.get('workflow_data', {})
        print(f"\n3. Workflow Data Structure:")
        print(f"   📊 Type: {type(workflow_data)}")
        
        if isinstance(workflow_data, dict):
            print(f"   📋 Keys: {list(workflow_data.keys())}")
            for key, value in workflow_data.items():
                if isinstance(value, list):
                    print(f"      - {key}: List with {len(value)} items")
                    if value and len(value) > 0:
                        print(f"        First item type: {type(value[0])}")
                        if isinstance(value[0], dict):
                            print(f"        First item keys: {list(value[0].keys())}")
                elif isinstance(value, dict):
                    print(f"      - {key}: Dict with {len(value)} keys: {list(value.keys())}")
                else:
                    print(f"      - {key}: {type(value)} = {str(value)[:100]}...")
        
        # 4. Check if there's a separate nodes table
        print(f"\n4. Checking for workflow nodes table...")
        try:
            nodes_result = supabase.table("workflow_nodes").select("*").eq("workflow_id", workflow['id']).execute()
            print(f"   📦 Found {len(nodes_result.data)} nodes in workflow_nodes table")
            
            for i, node in enumerate(nodes_result.data[:3], 1):  # Show first 3 nodes
                print(f"\n   🔧 Node {i}:")
                print(f"      Connector: {node.get('connector_name', 'N/A')}")
                print(f"      Node ID: {node.get('id', 'N/A')}")
                
                # Check parameters
                parameters = node.get('parameters', {})
                if isinstance(parameters, dict):
                    print(f"      Parameters ({len(parameters)} items):")
                    for param_name, param_value in parameters.items():
                        if isinstance(param_value, str) and '{' in param_value:
                            print(f"         📋 {param_name}: {param_value}")
                            
                            # Check brace matching
                            open_braces = param_value.count('{')
                            close_braces = param_value.count('}')
                            
                            if open_braces != close_braces:
                                print(f"         ❌ MALFORMED: {open_braces} open, {close_braces} close braces")
                            else:
                                print(f"         ✅ Well-formed")
                        elif param_value is not None:
                            print(f"         📝 {param_name}: {str(param_value)[:50]}...")
                            
        except Exception as e:
            print(f"   ❌ No workflow_nodes table or error: {e}")
        
        # 5. Full JSON dump of the latest workflow
        print(f"\n5. Full workflow JSON structure:")
        print("=" * 30)
        print(json.dumps(workflow, indent=2, default=str)[:2000] + "..." if len(str(workflow)) > 2000 else json.dumps(workflow, indent=2, default=str))
        
        print("\n✅ Structure debugging complete!")
        
    except Exception as e:
        print(f"❌ Error debugging structure: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_workflow_structure()) 