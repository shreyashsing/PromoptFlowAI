#!/usr/bin/env python3
"""
Test the real Gmail parameter resolution issue with the actual data structures.
This simulates the exact scenario where templates aren't being resolved.
"""

import asyncio
import json
from unittest.mock import MagicMock
from typing import Dict, Any

from app.services.unified_workflow_orchestrator import IntelligentParameterResolver
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.services.workflow_graph import WorkflowGraph
from app.models.base import WorkflowNode, NodePosition


class MockWorkflowGraph:
    """Mock workflow graph that simulates the real data structure."""
    
    def __init__(self):
        self.node_contexts = {}
        self.nodes = {}
    
    def add_gmail_node_result(self, node_id: str, gmail_data: Dict[str, Any]):
        """Add a Gmail node result to the graph."""
        context = NodeExecutionContext(
            node_id=node_id,
            state=NodeState.SUCCESS,
            output_data={
                "main": gmail_data,  # This is how the data is actually stored
                "raw": gmail_data
            }
        )
        self.node_contexts[node_id] = context
        
        # Add the node
        node = WorkflowNode(
            id=node_id,
            connector_name="gmail_connector",
            position=NodePosition(x=0, y=0),
            parameters={}
        )
        self.nodes[node_id] = node


async def test_real_parameter_resolution():
    """Test parameter resolution with the real data structure."""
    print("=== Testing Real Gmail Parameter Resolution ===")
    
    # Create mock Gmail data as it would be returned by the connector
    gmail_data = {
        "query": "is:unread in:inbox",
        "total_results": 1,
        "returned_results": 1,
        "messages": [
            {
                "id": "msg1",
                "subject": "Social Media Update",
                "sender": "social@example.com",
                "snippet": "Check out this social media post",
                "date": "2024-01-15T10:00:00Z"
            }
        ]
    }
    
    # Create mock workflow graph with Gmail node result
    graph = MockWorkflowGraph()
    graph.add_gmail_node_result("gmail-connector-1", gmail_data)
    
    # Create parameter resolver
    from app.services.unified_workflow_orchestrator import ConnectorIntelligence
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create mock context with graph reference
    context = NodeExecutionContext(
        node_id="google-sheets-1",
        state=NodeState.WAITING
    )
    context.workflow_graph = graph
    
    # Test the problematic template values
    template_values = [
        "{gmail_connector.result.messages[0].subject}",
        "{gmail_connector.result.messages[0].sender}",
        "{gmail_connector.result.messages[0].snippet}",
        "{gmail_connector.result.messages[1].subject}",  # Should be empty
        "{gmail_connector.result.messages[1].sender}",   # Should be empty
        "{gmail_connector.result.messages[1].snippet}",  # Should be empty
    ]
    
    print("Testing template resolution:")
    resolved_values = []
    
    for template in template_values:
        try:
            # This simulates how the parameter resolver is called
            resolved = await resolver._resolve_parameter_references(template, {}, {}, context)
            resolved_values.append(resolved)
            print(f"  '{template}' -> '{resolved}'")
        except Exception as e:
            print(f"  '{template}' -> ERROR: {e}")
            resolved_values.append("")
    
    # Check if resolution worked
    expected_values = [
        "Social Media Update",
        "social@example.com", 
        "Check out this social media post",
        "",  # Empty for missing index
        "",  # Empty for missing index
        ""   # Empty for missing index
    ]
    
    print(f"\nExpected: {expected_values}")
    print(f"Got:      {resolved_values}")
    
    if resolved_values == expected_values:
        print("✅ SUCCESS: Parameter resolution works correctly!")
    else:
        print("❌ FAILED: Parameter resolution still has issues")
        
        # Show what would appear in Google Sheets
        print("\nWhat would appear in Google Sheets:")
        for i, value in enumerate(resolved_values):
            if value.startswith("{") and value.endswith("}"):
                print(f"  Row {i+1}: TEMPLATE NOT RESOLVED - {value}")
            else:
                print(f"  Row {i+1}: {value}")


async def test_different_node_naming():
    """Test with different node naming patterns."""
    print("\n=== Testing Different Node Naming Patterns ===")
    
    gmail_data = {
        "messages": [
            {
                "subject": "Test Email",
                "sender": "test@example.com",
                "snippet": "This is a test"
            }
        ]
    }
    
    # Test different node naming patterns
    node_patterns = [
        ("gmail-connector-1", "gmail_connector"),
        ("gmail_connector-1", "gmail_connector"),
        ("gmail-1", "gmail_connector"),
        ("node-gmail-1", "gmail_connector")
    ]
    
    from app.services.unified_workflow_orchestrator import ConnectorIntelligence
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    for node_id, reference_name in node_patterns:
        print(f"\nTesting node_id='{node_id}', reference='{reference_name}':")
        
        graph = MockWorkflowGraph()
        graph.add_gmail_node_result(node_id, gmail_data)
        
        context = NodeExecutionContext(node_id="test", state=NodeState.WAITING)
        context.workflow_graph = graph
        
        template = f"{{{reference_name}.result.messages[0].subject}}"
        
        try:
            resolved = await resolver._resolve_parameter_references(template, {}, {}, context)
            print(f"  '{template}' -> '{resolved}'")
            
            if resolved == "Test Email":
                print("  ✅ SUCCESS")
            else:
                print("  ❌ FAILED")
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_real_parameter_resolution())
    asyncio.run(test_different_node_naming())