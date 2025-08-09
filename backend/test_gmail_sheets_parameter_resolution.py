"""
Test Gmail to Google Sheets Parameter Resolution

This test reproduces and fixes the issue where Gmail connector output
is not properly resolved when passed to Google Sheets connector.
"""
import asyncio
import json
from typing import Dict, Any

from app.services.unified_workflow_orchestrator import IntelligentParameterResolver, ConnectorIntelligence
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.models.base import WorkflowNode, NodePosition
from app.services.workflow_graph import WorkflowGraph


def create_mock_gmail_output():
    """Create mock Gmail connector output that matches real structure."""
    return {
        "result": [
            {
                "subject": "Weekly Team Update",
                "from": "manager@company.com",
                "date": "2025-01-07",
                "snippet": "This week's accomplishments and next week's goals..."
            },
            {
                "subject": "Project Status Report",
                "from": "lead@company.com", 
                "date": "2025-01-06",
                "snippet": "Current project status and upcoming milestones..."
            },
            {
                "subject": "Budget Review Meeting",
                "from": "finance@company.com",
                "date": "2025-01-05", 
                "snippet": "Quarterly budget review and planning session..."
            }
        ],
        "total_count": 3,
        "connector_name": "gmail_connector"
    }


def create_mock_workflow_graph():
    """Create a mock workflow graph with Gmail connector output."""
    graph = WorkflowGraph()
    
    # Create Gmail node context with output
    gmail_context = NodeExecutionContext(
        node_id="gmail_connector-0",
        state=NodeState.SUCCESS,
        output_data={
            "main": create_mock_gmail_output()
        }
    )
    
    # Add to graph
    graph.node_contexts["gmail_connector-0"] = gmail_context
    
    return graph


async def test_parameter_resolution():
    """Test parameter resolution for Gmail to Google Sheets workflow."""
    
    print("🧪 Testing Gmail to Google Sheets Parameter Resolution")
    print("=" * 60)
    
    # Create parameter resolver
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Create mock workflow graph
    graph = create_mock_workflow_graph()
    
    # Create Google Sheets node with template parameters
    sheets_node = WorkflowNode(
        id="google_sheets-1",
        connector_name="google_sheets",
        position=NodePosition(x=100, y=100),
        parameters={
            "action": "write",
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "range": "Sheet1!A1:D10",
            "values": [
                ["Subject", "Sender", "Date", "Snippet"],
                [
                    "{gmail_connector.result[0].subject}",
                    "{gmail_connector.result[0].from}",
                    "{gmail_connector.result[0].date}",
                    "{gmail_connector.result[0].snippet}"
                ],
                [
                    "{gmail_connector.result[1].subject}",
                    "{gmail_connector.result[1].from}",
                    "{gmail_connector.result[1].date}",
                    "{gmail_connector.result[1].snippet}"
                ],
                [
                    "{gmail_connector.result[2].subject}",
                    "{gmail_connector.result[2].from}",
                    "{gmail_connector.result[2].date}",
                    "{gmail_connector.result[2].snippet}"
                ]
            ]
        }
    )
    
    # Create execution context
    context = NodeExecutionContext(
        node_id="google_sheets-1",
        state=NodeState.WAITING
    )
    context.workflow_graph = graph
    
    # Input data (this would normally come from the workflow orchestrator)
    input_data = {
        "gmail_connector": create_mock_gmail_output()
    }
    
    print("\n1. Original Parameters (with templates):")
    print(json.dumps(sheets_node.parameters["values"], indent=2))
    
    # Resolve parameters
    print("\n2. Resolving parameters...")
    resolved_params = await resolver.resolve_parameters(sheets_node, input_data, context)
    
    print("\n3. Resolved Parameters:")
    print(json.dumps(resolved_params["values"], indent=2))
    
    # Verify resolution worked
    print("\n4. Verification:")
    first_row_data = resolved_params["values"][1]  # Skip header row
    
    expected_subject = "Weekly Team Update"
    actual_subject = first_row_data[0]
    
    if actual_subject == expected_subject:
        print(f"   ✅ Subject resolved correctly: {actual_subject}")
    else:
        print(f"   ❌ Subject resolution failed:")
        print(f"      Expected: {expected_subject}")
        print(f"      Actual: {actual_subject}")
    
    expected_sender = "manager@company.com"
    actual_sender = first_row_data[1]
    
    if actual_sender == expected_sender:
        print(f"   ✅ Sender resolved correctly: {actual_sender}")
    else:
        print(f"   ❌ Sender resolution failed:")
        print(f"      Expected: {expected_sender}")
        print(f"      Actual: {actual_sender}")
    
    # Check if any template variables remain unresolved
    all_resolved = True
    for row in resolved_params["values"]:
        for cell in row:
            if isinstance(cell, str) and '{' in cell and '}' in cell:
                print(f"   ❌ Unresolved template found: {cell}")
                all_resolved = False
    
    if all_resolved:
        print("   ✅ All template variables resolved successfully!")
    
    print(f"\n🎯 Parameter Resolution Test Complete!")
    return resolved_params


async def test_edge_cases():
    """Test edge cases in parameter resolution."""
    
    print("\n" + "=" * 60)
    print("🧪 Testing Edge Cases")
    print("=" * 60)
    
    connector_intel = ConnectorIntelligence()
    resolver = IntelligentParameterResolver(connector_intel)
    
    # Test case 1: Missing array index
    print("\n1. Testing missing array index...")
    
    input_data = {
        "gmail_connector": {
            "result": [
                {"subject": "Only Email"}
            ]
        }
    }
    
    node = WorkflowNode(
        id="test-1",
        connector_name="test",
        position=NodePosition(x=0, y=0),
        parameters={
            "value": "{gmail_connector.result[5].subject}"  # Index 5 doesn't exist
        }
    )
    
    context = NodeExecutionContext(node_id="test-1", state=NodeState.WAITING)
    resolved = await resolver.resolve_parameters(node, input_data, context)
    
    print(f"   Result: {resolved['value']}")
    
    # Test case 2: Non-existent field
    print("\n2. Testing non-existent field...")
    
    node.parameters = {
        "value": "{gmail_connector.result[0].nonexistent_field}"
    }
    
    resolved = await resolver.resolve_parameters(node, input_data, context)
    print(f"   Result: {resolved['value']}")
    
    # Test case 3: Complex nested structure
    print("\n3. Testing complex nested structure...")
    
    input_data = {
        "complex_connector": {
            "data": {
                "items": [
                    {"info": {"title": "Nested Title"}}
                ]
            }
        }
    }
    
    node.parameters = {
        "value": "{complex_connector.data.items[0].info.title}"
    }
    
    resolved = await resolver.resolve_parameters(node, input_data, context)
    print(f"   Result: {resolved['value']}")


if __name__ == "__main__":
    asyncio.run(test_parameter_resolution())
    asyncio.run(test_edge_cases())