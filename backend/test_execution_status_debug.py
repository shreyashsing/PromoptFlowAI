#!/usr/bin/env python3
"""
Debug script to check what's happening with execution status.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_supabase_client
from app.services.workflow_orchestrator import WorkflowOrchestrator

async def debug_execution_status():
    """Debug the execution status issue."""
    
    print("🔍 Debugging execution status issue...")
    
    try:
        # Get the most recent execution from the database
        supabase = get_supabase_client()
        
        # Get recent executions
        executions_response = supabase.table("workflow_executions").select("*").order("started_at", desc=True).limit(3).execute()
        
        if not executions_response.data:
            print("❌ No executions found in database")
            return False
            
        print(f"📊 Found {len(executions_response.data)} recent executions:")
        
        for i, execution in enumerate(executions_response.data):
            print(f"\n🔸 Execution {i+1}:")
            print(f"   ID: {execution['id']}")
            print(f"   Status: {execution['status']}")
            print(f"   Started: {execution['started_at']}")
            print(f"   Completed: {execution.get('completed_at', 'N/A')}")
            print(f"   Error: {execution.get('error_message', 'None')}")
            print(f"   Duration: {execution.get('duration_ms', 'N/A')}ms")
            
            # Check node results
            if 'result' in execution and execution['result']:
                result_data = execution['result']
                if 'node_results' in result_data:
                    node_results = result_data['node_results']
                    print(f"   Node Results: {len(node_results)} nodes")
                    
                    for j, node in enumerate(node_results):
                        print(f"     Node {j+1}: {node['connector_name']} - {node['status']}")
                        if node.get('error'):
                            print(f"       Error: {node['error']}")
            
        # Test the orchestrator's get_execution_status method
        print(f"\n🧪 Testing orchestrator.get_execution_status()...")
        orchestrator = WorkflowOrchestrator()
        
        latest_execution_id = executions_response.data[0]['id']
        print(f"   Testing with execution ID: {latest_execution_id}")
        
        execution_result = await orchestrator.get_execution_status(latest_execution_id)
        
        if execution_result:
            print(f"✅ Orchestrator returned execution result:")
            print(f"   Status: {execution_result.status}")
            print(f"   Error: {execution_result.error}")
            print(f"   Node Results: {len(execution_result.node_results)} nodes")
            
            # Check individual node statuses
            failed_nodes = [nr for nr in execution_result.node_results if nr.status.value == 'failed']
            completed_nodes = [nr for nr in execution_result.node_results if nr.status.value == 'completed']
            
            print(f"   Completed nodes: {len(completed_nodes)}")
            print(f"   Failed nodes: {len(failed_nodes)}")
            
            if failed_nodes:
                print(f"   Failed node details:")
                for node in failed_nodes:
                    print(f"     - {node.connector_name}: {node.error}")
                    
        else:
            print(f"❌ Orchestrator returned None for execution {latest_execution_id}")
            
    except Exception as e:
        print(f"❌ Error during debug: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("🎯 Debug completed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(debug_execution_status())
    sys.exit(0 if success else 1)