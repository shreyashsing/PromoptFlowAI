"""
Test Workflow Parameter Merge Fix

This test verifies that the workflow update endpoint properly merges
node parameters instead of replacing them entirely.
"""
import asyncio
import json
from typing import Dict, Any, List

# Import the merge function to test it directly
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.workflows import _merge_workflow_nodes
from app.models.base import WorkflowNode, NodePosition


def test_parameter_merge_function():
    """Test the _merge_workflow_nodes function directly."""
    
    print("🧪 Testing Workflow Node Parameter Merge Function")
    print("=" * 60)
    
    # Existing nodes in database (complete with all parameters)
    existing_nodes = [
        {
            "id": "gmail_connector-0",
            "connector_name": "gmail_connector",
            "position": {"x": 100, "y": 100},
            "parameters": {
                "action": "search",
                "query": "from:manager@company.com",
                "max_results": 10,
                "include_spam_trash": False,
                "label_ids": ["INBOX"],
                "format": "full"
            },
            "dependencies": []
        },
        {
            "id": "google_sheets-1",
            "connector_name": "google_sheets",
            "position": {"x": 300, "y": 100},
            "parameters": {
                "action": "write",
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "range": "Sheet1!A1:D4",
                "values": [["Subject", "Sender", "Date", "Snippet"]]
            },
            "dependencies": ["gmail_connector-0"]
        }
    ]
    
    print("\n1. Existing Nodes (from database):")
    for node in existing_nodes:
        print(f"   {node['id']}: {len(node['parameters'])} parameters")
        print(f"      Parameters: {list(node['parameters'].keys())}")
    
    # Updated nodes from frontend (user modified only max_results in Gmail node)
    updated_nodes = [
        WorkflowNode(
            id="gmail_connector-0",
            connector_name="gmail_connector",
            position=NodePosition(x=100, y=100),
            parameters={
                "max_results": 20  # Only the modified parameter
            },
            dependencies=[]
        ),
        WorkflowNode(
            id="google_sheets-1",
            connector_name="google_sheets",
            position=NodePosition(x=300, y=100),
            parameters={
                "action": "write",
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "range": "Sheet1!A1:D4",
                "values": [["Subject", "Sender", "Date", "Snippet"]]
            },
            dependencies=["gmail_connector-0"]
        )
    ]
    
    print("\n2. Updated Nodes (from frontend):")
    for node in updated_nodes:
        print(f"   {node.id}: {len(node.parameters)} parameters")
        print(f"      Parameters: {list(node.parameters.keys())}")
    
    # Test the merge function
    merged_nodes = _merge_workflow_nodes(existing_nodes, updated_nodes)
    
    print("\n3. Merged Nodes (result):")
    for node in merged_nodes:
        print(f"   {node['id']}: {len(node['parameters'])} parameters")
        print(f"      Parameters: {list(node['parameters'].keys())}")
    
    # Verify the merge worked correctly
    print("\n4. Verification:")
    
    # Check Gmail node
    gmail_node = next(node for node in merged_nodes if node['id'] == 'gmail_connector-0')
    expected_gmail_params = {
        "action": "search",
        "query": "from:manager@company.com", 
        "max_results": 20,  # Updated value
        "include_spam_trash": False,
        "label_ids": ["INBOX"],
        "format": "full"
    }
    
    if gmail_node['parameters'] == expected_gmail_params:
        print("   ✅ Gmail node parameters merged correctly")
        print(f"      - Preserved existing parameters: action, query, include_spam_trash, label_ids, format")
        print(f"      - Updated parameter: max_results = {gmail_node['parameters']['max_results']}")
    else:
        print("   ❌ Gmail node parameters merge failed")
        print(f"      Expected: {expected_gmail_params}")
        print(f"      Actual: {gmail_node['parameters']}")
    
    # Check Google Sheets node (should be unchanged)
    sheets_node = next(node for node in merged_nodes if node['id'] == 'google_sheets-1')
    if len(sheets_node['parameters']) == 4:  # action, spreadsheet_id, range, values
        print("   ✅ Google Sheets node parameters preserved correctly")
    else:
        print("   ❌ Google Sheets node parameters not preserved")
    
    print(f"\n🎯 Parameter Merge Function Test Complete!")
    
    return merged_nodes


def test_edge_cases():
    """Test edge cases for parameter merging."""
    
    print("\n" + "=" * 60)
    print("🧪 Testing Edge Cases")
    print("=" * 60)
    
    # Test case 1: New node (not in existing)
    print("\n1. Testing new node addition:")
    existing_nodes = [
        {
            "id": "node-1",
            "connector_name": "test",
            "position": {"x": 0, "y": 0},
            "parameters": {"param1": "value1"},
            "dependencies": []
        }
    ]
    
    updated_nodes = [
        WorkflowNode(
            id="node-1",
            connector_name="test",
            position=NodePosition(x=0, y=0),
            parameters={"param1": "updated_value1"},
            dependencies=[]
        ),
        WorkflowNode(
            id="node-2",  # New node
            connector_name="new_test",
            position=NodePosition(x=100, y=0),
            parameters={"param2": "value2"},
            dependencies=[]
        )
    ]
    
    merged = _merge_workflow_nodes(existing_nodes, updated_nodes)
    print(f"   Result: {len(merged)} nodes (expected: 2)")
    print(f"   New node added: {'node-2' in [n['id'] for n in merged]}")
    
    # Test case 2: Empty parameters
    print("\n2. Testing empty parameters:")
    existing_nodes = [
        {
            "id": "node-1",
            "connector_name": "test",
            "position": {"x": 0, "y": 0},
            "parameters": {"param1": "value1", "param2": "value2"},
            "dependencies": []
        }
    ]
    
    updated_nodes = [
        WorkflowNode(
            id="node-1",
            connector_name="test",
            position=NodePosition(x=0, y=0),
            parameters={},  # Empty parameters
            dependencies=[]
        )
    ]
    
    merged = _merge_workflow_nodes(existing_nodes, updated_nodes)
    merged_params = merged[0]['parameters']
    print(f"   Original parameters preserved: {len(merged_params)} (expected: 2)")
    print(f"   Parameters: {list(merged_params.keys())}")
    
    # Test case 3: Parameter deletion (explicit None values)
    print("\n3. Testing parameter deletion:")
    existing_nodes = [
        {
            "id": "node-1",
            "connector_name": "test", 
            "position": {"x": 0, "y": 0},
            "parameters": {"param1": "value1", "param2": "value2", "param3": "value3"},
            "dependencies": []
        }
    ]
    
    updated_nodes = [
        WorkflowNode(
            id="node-1",
            connector_name="test",
            position=NodePosition(x=0, y=0),
            parameters={"param1": "updated_value1", "param2": None},  # param2 set to None for deletion
            dependencies=[]
        )
    ]
    
    merged = _merge_workflow_nodes(existing_nodes, updated_nodes)
    merged_params = merged[0]['parameters']
    print(f"   Parameters after update: {merged_params}")
    print(f"   param2 handling: {'param2' in merged_params} (None values are preserved)")


if __name__ == "__main__":
    test_parameter_merge_function()
    test_edge_cases()