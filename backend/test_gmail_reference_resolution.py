#!/usr/bin/env python3
"""
Test Gmail connector reference resolution specifically
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.unified_workflow_orchestrator import IntelligentParameterResolver, ConnectorIntelligence
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.services.workflow_graph import WorkflowGraph
from app.models.base import WorkflowNode

async def test_gmail_reference_resolution():
    """Test that Gmail connector properly resolves references to code node output"""
    
    print("🧪 Testing Gmail reference resolution...")
    
    # Create parameter resolver
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create a mock workflow graph
    graph = WorkflowGraph()
    
    # Add a code node
    code_node = WorkflowNode(
        id="code-3",
        connector_name="code",
        parameters={"code": "return {combinedText: 'Blog content here', blogCount: 5}"},
        position={"x": 100, "y": 100}
    )
    graph.add_node(code_node)
    
    # Simulate code node completion with the exact structure from your logs
    code_context = graph.node_contexts["code-3"]
    code_context.output_data = {
        "main": {
            'combinedText': 'Sample blog content from AI research',
            'blogCount': 3,
            'timestamp': '2025-08-05T10:34:41.977Z',
            'sourceType': 'object',
            'originalKeys': ['results', 'metadata']
        }
    }
    code_context.transition_to(NodeState.SUCCESS, "Code executed")
    
    # Create a Gmail node that references the code node
    gmail_node = WorkflowNode(
        id="gmail_connector-4",
        connector_name="gmail_connector",
        parameters={
            "to": "test@example.com",
            "subject": "Blog Analysis Complete",
            "body": "Analysis complete! Found {code.blogCount} blog posts. Combined content: {code.combinedText}. Processed at {code.timestamp}"
        },
        position={"x": 300, "y": 100}
    )
    graph.add_node(gmail_node)
    
    # Add connection
    graph.add_connection("code-3", "gmail_connector-4", "main", "main")
    
    # Mark code node as completed
    graph.mark_node_completed("code-3", code_context.output_data)
    
    # Create context for gmail node
    gmail_context = graph.node_contexts["gmail_connector-4"]
    gmail_context.workflow_graph = graph
    
    # Prepare input data
    input_data = graph.prepare_node_input("gmail_connector-4")
    print(f"📊 Input data for Gmail: {input_data}")
    
    # Resolve parameters
    resolved_params = await resolver.resolve_parameters(gmail_node, input_data, gmail_context)
    
    print(f"✅ Resolved Gmail parameters:")
    for key, value in resolved_params.items():
        print(f"   {key}: {value}")
    
    # Check if references were resolved correctly
    expected_body = "Analysis complete! Found 3 blog posts. Combined content: Sample blog content from AI research. Processed at 2025-08-05T10:34:41.977Z"
    actual_body = resolved_params.get("body", "")
    
    if "3 blog posts" in actual_body and "Sample blog content from AI research" in actual_body:
        print("🎉 SUCCESS: Gmail references resolved correctly!")
        return True
    else:
        print("❌ FAILED: Gmail references not resolved correctly")
        print(f"   Expected to contain: '3 blog posts' and 'Sample blog content from AI research'")
        print(f"   Actual body: {actual_body}")
        return False

async def test_gmail_with_json_object():
    """Test what happens when Gmail receives the JSON object directly"""
    
    print("\n🧪 Testing Gmail with JSON object input...")
    
    # Create parameter resolver
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create a mock workflow graph
    graph = WorkflowGraph()
    
    # Create a Gmail node with a reference that might be getting the whole object
    gmail_node = WorkflowNode(
        id="gmail_connector-4",
        connector_name="gmail_connector",
        parameters={
            "to": "test@example.com",
            "subject": "Test",
            "body": "{code.result}"  # This might be getting the whole object
        },
        position={"x": 300, "y": 100}
    )
    graph.add_node(gmail_node)
    
    # Create context for gmail node
    gmail_context = graph.node_contexts["gmail_connector-4"]
    gmail_context.workflow_graph = graph
    
    # Simulate input data that contains the JSON object
    input_data = {
        "main": {
            'combinedText': '',
            'blogCount': 0,
            'timestamp': '2025-08-05T10:34:41.977Z',
            'sourceType': 'object',
            'originalKeys': []
        }
    }
    
    print(f"📊 Input data: {input_data}")
    
    # Resolve parameters
    resolved_params = await resolver.resolve_parameters(gmail_node, input_data, gmail_context)
    
    print(f"✅ Resolved parameters: {resolved_params}")
    
    # Check what the body contains
    body = resolved_params.get("body", "")
    if isinstance(body, str) and "{" in body and "}" in body:
        print("❌ ISSUE: Body contains JSON object as string")
        return False
    else:
        print("✅ Body looks normal")
        return True

async def main():
    test1 = await test_gmail_reference_resolution()
    test2 = await test_gmail_with_json_object()
    
    success = test1 and test2
    print(f"\n{'🎉 All tests passed!' if success else '❌ Some tests failed!'}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)