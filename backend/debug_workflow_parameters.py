#!/usr/bin/env python3
"""
Debug workflow parameters to check for malformed parameter references.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase_client
import json


async def debug_workflow_parameters():
    """Debug workflow parameters to find malformed references."""
    print("🔍 Debugging Workflow Parameters")
    print("=" * 40)
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # 1. Get recent workflows
        print("1. Fetching recent workflows...")
        result = supabase.table("workflows").select("*").order("created_at", desc=True).limit(5).execute()
        workflows = result.data
        
        print(f"   Found {len(workflows)} recent workflows")
        
        # 2. Analyze each workflow's parameters
        for i, workflow in enumerate(workflows, 1):
            print(f"\n📦 Workflow {i}: {workflow.get('name', 'UNNAMED')}")
            print(f"   ID: {workflow.get('id', 'N/A')}")
            print(f"   Created: {workflow.get('created_at', 'N/A')}")
            
            # Parse workflow data
            workflow_data = workflow.get('workflow_data', {})
            nodes = workflow_data.get('nodes', [])
            
            print(f"   Nodes: {len(nodes)}")
            
            # Check each node's parameters
            for j, node in enumerate(nodes, 1):
                connector_name = node.get('connector_name', 'unknown')
                parameters = node.get('parameters', {})
                
                print(f"\n   🔧 Node {j}: {connector_name}")
                print(f"      Node ID: {node.get('id', 'N/A')}")
                
                # Look for parameter references
                malformed_refs = []
                correct_refs = []
                
                for param_name, param_value in parameters.items():
                    if isinstance(param_value, str):
                        # Check for various reference patterns
                        if '{' in param_value:
                            print(f"      📋 {param_name}: {param_value}")
                            
                            # Count braces
                            open_braces = param_value.count('{')
                            close_braces = param_value.count('}')
                            
                            if open_braces != close_braces:
                                malformed_refs.append(f"{param_name}: {param_value}")
                                print(f"      ❌ MALFORMED: {open_braces} open braces, {close_braces} close braces")
                            else:
                                correct_refs.append(f"{param_name}: {param_value}")
                                print(f"      ✅ Well-formed reference")
                
                if malformed_refs:
                    print(f"      ⚠️  Malformed references: {len(malformed_refs)}")
                    for ref in malformed_refs:
                        print(f"         - {ref}")
                        
                if correct_refs:
                    print(f"      ✅ Correct references: {len(correct_refs)}")
                    for ref in correct_refs:
                        print(f"         - {ref}")
        
        print("\n✅ Parameter debugging complete!")
        
    except Exception as e:
        print(f"❌ Error debugging parameters: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_workflow_parameters()) 