"""
Test Gmail to Google Sheets Workflow Fix

This test verifies that the parameter resolution fix works in a real workflow execution.
"""
import asyncio
import json
from typing import Dict, Any

from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, NodePosition


def create_test_workflow():
    """Create a test workflow with Gmail -> Google Sheets."""
    
    # Gmail connector node
    gmail_node = WorkflowNode(
        id="gmail_connector-0",
        connector_name="gmail_connector",
        position=NodePosition(x=100, y=100),
        parameters={
            "action": "search",
            "query": "from:manager@company.com",
            "max_results": 3
        }
    )
    
    # Google Sheets connector node with template parameters
    sheets_node = WorkflowNode(
        id="google_sheets-1", 
        connector_name="google_sheets",
        position=NodePosition(x=300, y=100),
        parameters={
            "action": "write",
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "range": "Sheet1!A1:D4",
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
        },
        dependencies=["gmail_connector-0"]
    )
    
    # Edge connecting Gmail to Google Sheets
    edge = WorkflowEdge(
        id="edge-0",
        source="gmail_connector-0",
        target="google_sheets-1"
    )
    
    return WorkflowPlan(
        id="test-workflow",
        name="Gmail to Google Sheets Test",
        description="Test workflow for parameter resolution",
        user_id="test-user",
        nodes=[gmail_node, sheets_node],
        edges=[edge]
    )


async def test_parameter_resolution_in_workflow():
    """Test parameter resolution in actual workflow execution."""
    
    print("🧪 Testing Parameter Resolution in Workflow Execution")
    print("=" * 60)
    
    # Create test workflow
    workflow = create_test_workflow()
    
    print("\n1. Created test workflow:")
    print(f"   - Nodes: {len(workflow.nodes)}")
    print(f"   - Edges: {len(workflow.edges)}")
    
    # Create orchestrator
    orchestrator = UnifiedWorkflowOrchestrator()
    
    # Mock Gmail connector output (simulating successful Gmail execution)
    mock_gmail_output = {
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
        "total_count": 3
    }
    
    print("\n2. Mock Gmail output created")
    
    # Test parameter resolution for Google Sheets node
    sheets_node = workflow.nodes[1]  # Google Sheets node
    
    # Create mock execution context
    from app.models.enhanced_execution import NodeExecutionContext, NodeState
    from app.services.workflow_graph import WorkflowGraph
    
    # Create workflow graph with Gmail output
    graph = WorkflowGraph()
    gmail_context = NodeExecutionContext(
        node_id="gmail_connector-0",
        state=NodeState.SUCCESS,
        output_data={"main": mock_gmail_output}
    )
    graph.node_contexts["gmail_connector-0"] = gmail_context
    
    # Create context for Google Sheets node
    sheets_context = NodeExecutionContext(
        node_id="google_sheets-1",
        state=NodeState.WAITING
    )
    sheets_context.workflow_graph = graph
    
    # Input data for parameter resolution
    input_data = {
        "gmail_connector": mock_gmail_output
    }
    
    print("\n3. Testing parameter resolution...")
    
    # Resolve parameters
    resolved_params = await orchestrator.parameter_resolver.resolve_parameters(
        sheets_node, input_data, sheets_context
    )
    
    print("\n4. Parameter Resolution Results:")
    print("   Original template values:")
    for i, row in enumerate(sheets_node.parameters["values"]):
        if i > 0:  # Skip header row
            print(f"     Row {i}: {row[0]} | {row[1]}")
    
    print("\n   Resolved values:")
    for i, row in enumerate(resolved_params["values"]):
        if i > 0:  # Skip header row
            print(f"     Row {i}: {row[0]} | {row[1]}")
    
    # Verify resolution
    success = True
    expected_subjects = ["Weekly Team Update", "Project Status Report", "Budget Review Meeting"]
    
    for i, expected_subject in enumerate(expected_subjects):
        actual_subject = resolved_params["values"][i + 1][0]  # +1 to skip header
        if actual_subject != expected_subject:
            print(f"   ❌ Row {i+1} subject mismatch:")
            print(f"      Expected: {expected_subject}")
            print(f"      Actual: {actual_subject}")
            success = False
    
    if success:
        print("   ✅ All parameters resolved correctly!")
    
    print(f"\n🎯 Workflow Parameter Resolution Test {'PASSED' if success else 'FAILED'}!")
    
    return success


if __name__ == "__main__":
    asyncio.run(test_parameter_resolution_in_workflow())