#!/usr/bin/env python3

import asyncio
import sys
import os
import json
from fastapi.testclient import TestClient as FastAPITestClient

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.main import app
from app.core.auth import get_current_user

# Mock user for testing
def mock_get_current_user():
    return {"user_id": "test-user-123", "email": "test@example.com"}

# Override the dependency
app.dependency_overrides[get_current_user] = mock_get_current_user

def test_workflow_creation_422():
    """Test workflow creation to reproduce the 422 error."""
    
    client = FastAPITestClient(app)
    
    # Test different payload structures to identify the validation issue
    
    # Test 1: Minimal valid payload
    print("Test 1: Minimal valid payload")
    payload1 = {
        "name": "Test Workflow",
        "description": "A test workflow",
        "nodes": [],
        "edges": [],
        "triggers": []
    }
    
    response1 = client.post("/api/v1/workflows", json=payload1)
    print(f"Status: {response1.status_code}")
    if response1.status_code != 201:
        print(f"Error: {response1.text}")
    print()
    
    # Test 2: Payload with a simple node
    print("Test 2: Payload with a simple node")
    payload2 = {
        "name": "Test Workflow 2",
        "description": "A test workflow with a node",
        "nodes": [
            {
                "id": "node1",
                "connector_name": "gmail",
                "parameters": {"subject": "test"},
                "position": {"x": 100, "y": 100},
                "dependencies": []
            }
        ],
        "edges": [],
        "triggers": []
    }
    
    response2 = client.post("/api/v1/workflows", json=payload2)
    print(f"Status: {response2.status_code}")
    if response2.status_code != 201:
        print(f"Error: {response2.text}")
    print()
    
    # Test 3: Payload with missing required fields
    print("Test 3: Payload with missing name")
    payload3 = {
        "description": "A test workflow without name",
        "nodes": [],
        "edges": [],
        "triggers": []
    }
    
    response3 = client.post("/api/v1/workflows", json=payload3)
    print(f"Status: {response3.status_code}")
    if response3.status_code != 201:
        print(f"Error: {response3.text}")
    print()
    
    # Test 4: Payload with invalid node structure
    print("Test 4: Payload with invalid node structure")
    payload4 = {
        "name": "Test Workflow 4",
        "description": "A test workflow with invalid node",
        "nodes": [
            {
                "id": "node1",
                "connector_name": "gmail",
                "parameters": {"subject": "test"},
                # Missing position field
                "dependencies": []
            }
        ],
        "edges": [],
        "triggers": []
    }
    
    response4 = client.post("/api/v1/workflows", json=payload4)
    print(f"Status: {response4.status_code}")
    if response4.status_code != 201:
        print(f"Error: {response4.text}")
    print()
    
    # Test 5: Empty payload
    print("Test 5: Empty payload")
    payload5 = {}
    
    response5 = client.post("/api/v1/workflows", json=payload5)
    print(f"Status: {response5.status_code}")
    if response5.status_code != 201:
        print(f"Error: {response5.text}")
    print()

def test_workflow_validation_details():
    """Test specific validation scenarios."""
    
    client = FastAPITestClient(app)
    
    # Test with various invalid payloads to understand validation
    test_cases = [
        {
            "name": "Empty name",
            "payload": {"name": "", "description": "test"}
        },
        {
            "name": "Name too long",
            "payload": {"name": "x" * 101, "description": "test"}
        },
        {
            "name": "Description too long", 
            "payload": {"name": "test", "description": "x" * 501}
        },
        {
            "name": "Invalid node - missing id",
            "payload": {
                "name": "test",
                "nodes": [{"connector_name": "gmail", "position": {"x": 0, "y": 0}}]
            }
        },
        {
            "name": "Invalid node - missing position",
            "payload": {
                "name": "test", 
                "nodes": [{"id": "node1", "connector_name": "gmail"}]
            }
        },
        {
            "name": "Invalid edge - missing fields",
            "payload": {
                "name": "test",
                "edges": [{"id": "edge1"}]
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"Testing: {test_case['name']}")
        response = client.post("/api/v1/workflows", json=test_case['payload'])
        print(f"Status: {response.status_code}")
        if response.status_code == 422:
            try:
                error_detail = response.json()
                print(f"Validation error: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error text: {response.text}")
        print("-" * 50)

if __name__ == "__main__":
    print("Testing workflow creation to debug 422 errors...\n")
    test_workflow_creation_422()
    print("\n" + "="*60 + "\n")
    test_workflow_validation_details()