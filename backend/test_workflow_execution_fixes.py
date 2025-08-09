#!/usr/bin/env python3
"""
Test the workflow execution fixes:
1. Database schema fixes (error column, dependency_resolution_time_ms column)
2. Workflow status completion fix
3. Execution status API fix
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator
from app.models.base import WorkflowPlan, WorkflowNode, NodePosition
from app.models.execution import ExecutionStatus

async def test_workflow_execution_fixes():
    """Test that workflow execution completes properly and status is correct"""
    print("🧪 Testing workflow execution fixes...")
    
    try:
        # Register connectors first
        from app.connectors.core.register import register_core_connectors
        register_result = register_core_connectors()
        print(f"📦 Registered {register_result['registered']} connectors")
        
        orchestrator = UnifiedWorkflowOrchestrator()
        
        # Create a simple test workflow
        import uuid
        test_user_id = str(uuid.uuid4())
        
        workflow = WorkflowPlan(
            id=str(uuid.uuid4()),
            name="Test Workflow Fixes",
            description="Test workflow to verify execution fixes",
            user_id=test_user_id,
            nodes=[
                WorkflowNode(
                    id="code-test",
                    connector_name="code",
                    parameters={
                        "language": "javascript",
                        "code": "return { message: 'Test successful', timestamp: new Date().toISOString() };",
                        "input_data": {},
                        "timeout": 30,
                        "safe_mode": True
                    },
                    position=NodePosition(x=100, y=100)
                )
            ],
            edges=[],
            triggers=[]
        )
        
        print("🚀 Executing test workflow...")
        
        # Execute the workflow
        execution_result = await orchestrator.execute_workflow(workflow)
        
        print(f"📊 Execution completed!")
        print(f"   Execution ID: {execution_result.execution_id}")
        print(f"   Status: {execution_result.status}")
        print(f"   Duration: {execution_result.total_duration_ms}ms")
        
        # Test 1: Check that status is COMPLETED (not RUNNING)
        if execution_result.status == ExecutionStatus.COMPLETED:
            print("✅ Status fix working: Execution status is COMPLETED")
        else:
            print(f"❌ Status fix failed: Expected COMPLETED, got {execution_result.status}")
            return False
        
        # Test 2: Check that we can retrieve execution status
        print("\n🔍 Testing execution status retrieval...")
        
        retrieved_status = await orchestrator.get_execution_status(execution_result.execution_id)
        
        if retrieved_status:
            print("✅ Execution status retrieval working")
            print(f"   Retrieved status: {retrieved_status.status}")
            print(f"   Retrieved execution ID: {retrieved_status.execution_id}")
        else:
            print("❌ Execution status retrieval failed")
            return False
        
        # Test 3: Verify database schema has required columns
        print("\n🗄️ Testing database schema...")
        
        from app.core.database import get_supabase_client
        supabase = get_supabase_client()
        
        # Check if the execution was stored properly
        response = supabase.table('workflow_executions').select('*').eq('id', execution_result.execution_id).execute()
        
        if response.data:
            execution_data = response.data[0]
            print("✅ Database storage working")
            
            # Check for required columns
            required_columns = ['error', 'dependency_resolution_time_ms']
            for column in required_columns:
                if column in execution_data:
                    print(f"✅ Column '{column}' exists in database")
                else:
                    print(f"❌ Column '{column}' missing from database")
                    return False
        else:
            print("❌ Execution not found in database")
            return False
        
        print("\n🎉 All workflow execution fixes are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test"""
    print("🚀 Testing Workflow Execution Fixes")
    print("=" * 50)
    
    success = await test_workflow_execution_fixes()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Workflow execution fixes are working.")
        print("✅ Status completion fix applied")
        print("✅ Database schema updated")
        print("✅ Execution status API working")
    else:
        print("⚠️  Some tests failed - check the implementation")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        exit(1)