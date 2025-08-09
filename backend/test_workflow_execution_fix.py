#!/usr/bin/env python3
"""
Test the actual workflow execution with the reference resolution fix
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge

async def test_workflow_execution():
    """Test that a real workflow execution resolves references correctly"""
    
    print("🧪 Testing workflow execution with reference resolution...")
    
    # Create a simple workflow
    workflow = WorkflowPlan(
        id="test-workflow-exec",
        user_id="test-user",
        name="Workflow Execution Test",
        description="Test workflow execution with reference resolution",
        nodes=[
            WorkflowNode(
                id="code-1",
                connector_name="code",
                parameters={
                    "code": """
// Simple code that returns structured data
return {
    result: "Data from code node",
    count: 42,
    status: "success"
};
"""
                },
                position={"x": 100, "y": 100}
            ),
            WorkflowNode(
                id="code-2",
                connector_name="code",
                parameters={
                    "code": """
// Code that uses reference to previous node
const message = `Processing: {code.result} with count {code.count}`;
return {
    processed_message: message,
    original_status: "{code.status}"
};
"""
                },
                position={"x": 300, "y": 100}
            )
        ],
        edges=[
            WorkflowEdge(
                id="edge-1",
                source="code-1",
                target="code-2"
            )
        ]
    )
    
    # Execute the workflow
    orchestrator = UnifiedWorkflowOrchestrator()
    
    try:
        result = await orchestrator.execute_workflow(workflow)
        
        print(f"✅ Workflow execution completed!")
        print(f"   Status: {result.status}")
        print(f"   Nodes executed: {len(result.node_contexts)}")
        
        # Check the final result
        if "code-2" in result.node_contexts:
            final_context = result.node_contexts["code-2"]
            if final_context.output_data and "main" in final_context.output_data:
                final_data = final_context.output_data["main"]
                print(f"   Final output: {final_data}")
                
                # Check if references were resolved
                if isinstance(final_data, dict):
                    processed_message = final_data.get("processed_message", "")
                    original_status = final_data.get("original_status", "")
                    
                    if "Data from code node" in processed_message and "42" in processed_message:
                        print("🎉 SUCCESS: References resolved correctly in workflow execution!")
                        return True
                    else:
                        print(f"❌ FAILED: References not resolved. Message: {processed_message}")
                        return False
        
        print("❌ FAILED: Could not find expected output data")
        return False
        
    except Exception as e:
        print(f"❌ FAILED: Workflow execution failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_workflow_execution())
    sys.exit(0 if success else 1)