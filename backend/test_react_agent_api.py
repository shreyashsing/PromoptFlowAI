"""
Test script for ReAct agent API endpoints.
Tests the newly implemented API endpoints for functionality and validation.
"""
import asyncio
import json
import uuid
from fastapi.testclient import TestClient
from app.main import app

# Create test client
client = TestClient(app)

def get_test_token():
    """Create a test JWT token for authentication."""
    # For testing purposes, we'll use a mock token
    # In a real scenario, this would be a valid JWT token
    return "test_token_123"

def test_react_agent_status():
    """Test the ReAct agent status endpoint."""
    print("Testing ReAct agent status endpoint...")
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/react/status", headers=headers)
    print(f"Status endpoint response: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Agent status: {data.get('status')}")
        print(f"Tools available: {data.get('tools_available', 0)}")
        print(f"Initialized: {data.get('initialized', False)}")
    else:
        print(f"Error: {response.text}")

def test_react_agent_tools():
    """Test the available tools endpoint."""
    print("\nTesting available tools endpoint...")
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/react/tools", headers=headers)
    print(f"Tools endpoint response: {response.status_code}")
    
    if response.status_code == 200:
        tools = response.json()
        print(f"Available tools count: {len(tools)}")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
    else:
        print(f"Error: {response.text}")

def test_react_agent_chat():
    """Test the ReAct agent chat endpoint."""
    print("\nTesting ReAct agent chat endpoint...")
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with a simple query
    chat_request = {
        "query": "Hello, can you help me test the ReAct agent?",
        "max_iterations": 5
    }
    
    response = client.post("/api/v1/react/chat", json=chat_request, headers=headers)
    print(f"Chat endpoint response: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data.get('response', 'No response')[:100]}...")
        print(f"Session ID: {data.get('session_id')}")
        print(f"Status: {data.get('status')}")
        print(f"Processing time: {data.get('processing_time_ms')}ms")
        print(f"Iterations used: {data.get('iterations_used')}")
        print(f"Tools used: {data.get('tools_used')}")
        return data.get('session_id')
    else:
        print(f"Error: {response.text}")
        return None

def test_conversation_history(session_id):
    """Test the conversation history endpoint."""
    if not session_id:
        print("\nSkipping conversation history test (no session ID)")
        return
    
    print(f"\nTesting conversation history endpoint for session {session_id}...")
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(f"/api/v1/react/conversations/{session_id}", headers=headers)
    print(f"History endpoint response: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Messages count: {len(data.get('messages', []))}")
        print(f"Status: {data.get('status')}")
        print(f"Created at: {data.get('created_at')}")
    else:
        print(f"Error: {response.text}")

def test_input_validation():
    """Test input validation on the chat endpoint."""
    print("\nTesting input validation...")
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test empty query
    response = client.post("/api/v1/react/chat", json={"query": ""}, headers=headers)
    print(f"Empty query response: {response.status_code}")
    
    # Test query too long
    long_query = "x" * 6000  # Exceeds 5000 char limit
    response = client.post("/api/v1/react/chat", json={"query": long_query}, headers=headers)
    print(f"Long query response: {response.status_code}")
    
    # Test invalid session ID
    response = client.post("/api/v1/react/chat", json={
        "query": "test",
        "session_id": "invalid-session-id"
    }, headers=headers)
    print(f"Invalid session ID response: {response.status_code}")
    
    # Test invalid max_iterations
    response = client.post("/api/v1/react/chat", json={
        "query": "test",
        "max_iterations": 25  # Exceeds limit of 20
    }, headers=headers)
    print(f"Invalid max_iterations response: {response.status_code}")

def test_react_agent_metrics():
    """Test the metrics endpoint."""
    print("\nTesting ReAct agent metrics endpoint...")
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/react/metrics", headers=headers)
    print(f"Metrics endpoint response: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Agent initialized: {data.get('agent_status', {}).get('initialized')}")
        print(f"Tools available: {data.get('tools', {}).get('available_count')}")
        print(f"WebSocket connections: {data.get('connections', {}).get('total_websocket_connections')}")
    else:
        print(f"Error: {response.text}")

def test_react_agent_health():
    """Test the health endpoint."""
    print("\nTesting ReAct agent health endpoint...")
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/react/health", headers=headers)
    print(f"Health endpoint response: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Overall status: {data.get('status')}")
        print("Health checks:")
        for check_name, check_data in data.get('checks', {}).items():
            print(f"  - {check_name}: {check_data.get('status')}")
    else:
        print(f"Error: {response.text}")

def main():
    """Run all tests."""
    print("Starting ReAct Agent API Tests")
    print("=" * 50)
    
    try:
        # Test basic endpoints
        test_react_agent_status()
        test_react_agent_tools()
        
        # Test chat functionality
        session_id = test_react_agent_chat()
        test_conversation_history(session_id)
        
        # Test validation
        test_input_validation()
        
        # Test monitoring endpoints
        test_react_agent_metrics()
        test_react_agent_health()
        
        print("\n" + "=" * 50)
        print("ReAct Agent API Tests Completed")
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()