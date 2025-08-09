#!/usr/bin/env python3
"""
Test the reference resolution fix for {code.result} issue
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge
from app.models.enhanced_execution import NodeState, NodeExecutionContext
from app.services.workflow_graph import WorkflowGraph

async def test_reference_resolution():
    """Test that {code.result} references are properly resolved"""
    
    print("🧪 Testing reference resolution fix...")
    
    # Create a simple workflow with code connector and gmail connector
    workflow = WorkflowPlan(
        id="test-workflow",
        user_id="test-user",
        name="Reference Resolution Test",
        description="Test workflow for reference resolution",
        nodes=[
            WorkflowNode(
                id="code-1",
                connector_name="code",
                parameters={
                    "code": "return {'result': 'Hello from code node!'}"
                },
                position={"x": 100, "y": 100}
            ),
            WorkflowNode(
                id="gmail_connector-2",
                connector_name="gmail_connector",
                parameters={
                    "to": "test@example.com",
                    "subject": "Test Email",
                    "body": "Message: {code.result}"  # This should resolve properly
                },
                position={"x": 300, "y": 100}
            )
        ],
        edges=[
            WorkflowEdge(
                id="edge-1",
                source="code-1",
                target="gmail_connector-2"
            )
        ]
    )
    
    # Create workflow graph
    graph = WorkflowGraph()
    
    # Manually build the graph
    for node in workflow.nodes:
        graph.add_node(node)
    
    for edge in workflow.edges:
        graph.add_connection(
            from_node=edge.source,
            to_node=edge.target,
            from_output="main",
            to_input="main"
        )
    
    # Simulate code node completion
    code_context = graph.node_contexts["code-1"]
    code_context.output_data = {"main": {"result": "Hello from code node!"}}
    code_context.transition_to(NodeState.SUCCESS, "Code executed successfully")
    
    # Mark code node as completed
    graph.mark_node_completed("code-1", {"main": {"result": "Hello from code node!"}})
    
    # Test parameter resolution for gmail node
    orchestrator = UnifiedWorkflowOrchestrator()
    parameter_resolver = orchestrator.parameter_resolver
    
    # Get gmail node and its context
    gmail_node = graph.nodes["gmail_connector-2"]
    gmail_context = graph.node_contexts["gmail_connector-2"]
    gmail_context.workflow_graph = graph  # Add graph reference
    
    # Prepare input data
    input_data = graph.prepare_node_input("gmail_connector-2")
    print(f"📊 Input data for gmail node: {input_data}")
    
    # Resolve parameters
    resolved_params = await parameter_resolver.resolve_parameters(
        gmail_node, input_data, gmail_context
    )
    
    print(f"✅ Resolved parameters: {resolved_params}")
    
    # Check if the reference was resolved correctly
    expected_body = "Message: Hello from code node!"
    actual_body = resolved_params.get("body", "")
    
    if actual_body == expected_body:
        print("🎉 SUCCESS: Reference resolution working correctly!")
        print(f"   Expected: {expected_body}")
        print(f"   Actual:   {actual_body}")
        return True
    else:
        print("❌ FAILED: Reference not resolved correctly")
        print(f"   Expected: {expected_body}")
        print(f"   Actual:   {actual_body}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_reference_resolution())
    sys.exit(0 if success else 1)