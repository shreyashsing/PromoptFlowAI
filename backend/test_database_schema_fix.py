#!/usr/bin/env python3
"""
Test script to verify the database schema fix for parallel execution.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_supabase_client
from app.models.execution import ExecutionResult, NodeExecutionResult, ExecutionStatus

async def test_database_schema_fix():
    """Test that the parallel executor can store execution results properly."""
    
    print("🧪 Testing database schema fix for parallel execution...")
    
    try:
        # Get an existing workflow ID from the database
        supabase = get_supabase_client()
        workflows_response = supabase.table("workflows").select("id, user_id").limit(1).execute()
        
        if not workflows_response.data:
            print("❌ No workflows found in database. Please create a workflow first.")
            return False
            
        workflow = workflows_response.data[0]
        
        # Create a mock execution result
        execution_result = ExecutionResult(
            execution_id=str(uuid.uuid4()),
            workflow_id=workflow["id"],
            user_id=workflow["user_id"],
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_duration_ms=5000,
            node_results=[
                NodeExecutionResult(
                    node_id="node-1",
                    connector_name="test_connector",
                    status=ExecutionStatus.COMPLETED,
                    result={"message": "Test successful"},
                    error=None,
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    duration_ms=2500
                )
            ]
        )
        
        # Test the database storage format
        
        # Convert execution result to match existing database schema exactly
        execution_data = {
            "id": execution_result.execution_id,
            "workflow_id": execution_result.workflow_id,
            "user_id": execution_result.user_id,
            "status": execution_result.status.value,
            "trigger_type": "manual",  # TODO: Support other trigger types
            "execution_log": [],  # Parallel execution doesn't use execution log
            "result": {
                "node_results": [
                    {
                        "node_id": nr.node_id,
                        "connector_name": nr.connector_name,
                        "status": nr.status.value,
                        "result": nr.result,
                        "error": nr.error,
                        "started_at": nr.started_at.isoformat(),
                        "completed_at": nr.completed_at.isoformat() if nr.completed_at else None,
                        "duration_ms": nr.duration_ms
                    }
                    for nr in execution_result.node_results
                ]
            },
            "error_message": execution_result.error,
            "started_at": execution_result.started_at.isoformat(),
            "completed_at": execution_result.completed_at.isoformat() if execution_result.completed_at else None,
            "duration_ms": execution_result.total_duration_ms
        }
        
        print("✅ Execution data structure created successfully")
        print(f"📊 Data structure: {list(execution_data.keys())}")
        
        # Try to insert the data
        response = supabase.table("workflow_executions").insert(execution_data).execute()
        
        if response.data:
            print("✅ Successfully stored execution result in database!")
            print(f"📝 Stored execution ID: {execution_result.execution_id}")
            
            # Clean up the test data
            supabase.table("workflow_executions").delete().eq("id", execution_result.execution_id).execute()
            print("🧹 Cleaned up test data")
            
        else:
            print(f"❌ Failed to store execution result: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error during database schema test: {str(e)}")
        return False
    
    print("🎉 Database schema fix test completed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_database_schema_fix())
    sys.exit(0 if success else 1)