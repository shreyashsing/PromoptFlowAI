#!/usr/bin/env python3
"""
Simple test to verify the reference resolution fix is working
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import IntelligentParameterResolver, ConnectorIntelligence
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.services.workflow_graph import WorkflowGraph
from app.models.base import WorkflowNode

async def test_simple_reference_resolution():
    """Test reference resolution without full workflow execution"""
    
    print("🧪 Testing simple reference resolution...")
    
    # Create parameter resolver
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create a mock workflow graph
    graph = WorkflowGraph()
    
    # Add a code node
    code_node = WorkflowNode(
        id="code-1",
        connector_name="code",
        parameters={"code": "return {'result': 'Hello World'}"},
        position={"x": 100, "y": 100}
    )
    graph.add_node(code_node)
    
    # Simulate code node completion
    code_context = graph.node_contexts["code-1"]
    code_context.output_data = {"main": {"result": "Hello World", "status": "success"}}
    code_context.transition_to(NodeState.SUCCESS, "Code executed")
    
    # Create a gmail node that references the code node
    gmail_node = WorkflowNode(
        id="gmail-2",
        connector_name="gmail_connector",
        parameters={
            "to": "test@example.com",
            "subject": "Test: {code.status}",
            "body": "The result is: {code.result}"
        },
        position={"x": 300, "y": 100}
    )
    graph.add_node(gmail_node)
    
    # Add connection
    graph.add_connection("code-1", "gmail-2", "main", "main")
    
    # Create context for gmail node
    gmail_context = graph.node_contexts["gmail-2"]
    gmail_context.workflow_graph = graph
    
    # Prepare input data
    input_data = graph.prepare_node_input("gmail-2")
    print(f"📊 Input data: {input_data}")
    
    # Resolve parameters
    resolved_params = await resolver.resolve_parameters(gmail_node, input_data, gmail_context)
    
    print(f"✅ Resolved parameters: {resolved_params}")
    
    # Check results
    expected_subject = "Test: success"
    expected_body = "The result is: Hello World"
    
    actual_subject = resolved_params.get("subject", "")
    actual_body = resolved_params.get("body", "")
    
    success = True
    if actual_subject != expected_subject:
        print(f"❌ Subject mismatch: expected '{expected_subject}', got '{actual_subject}'")
        success = False
    
    if actual_body != expected_body:
        print(f"❌ Body mismatch: expected '{expected_body}', got '{actual_body}'")
        success = False
    
    if success:
        print("🎉 SUCCESS: All references resolved correctly!")
        print(f"   Subject: {actual_subject}")
        print(f"   Body: {actual_body}")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(test_simple_reference_resolution())
    sys.exit(0 if success else 1)