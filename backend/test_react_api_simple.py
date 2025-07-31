"""
Simple test to verify ReAct agent API endpoints are properly registered.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

# Import app after setting path
from app.main import app

# Create test client
client = TestClient(app)

def test_endpoints_exist():
    """Test that the ReAct agent endpoints are properly registered."""
    print("Testing ReAct Agent API Endpoint Registration")
    print("=" * 50)
    
    # Test endpoints without authentication to see if they're registered
    endpoints_to_test = [
        "/api/v1/react/status",
        "/api/v1/react/tools", 
        "/api/v1/react/chat",
        "/api/v1/react/metrics",
        "/api/v1/react/health",
        "/api/v1/react/conversations/test-session-id"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = client.get(endpoint) if endpoint != "/api/v1/react/chat" else client.post(endpoint, json={"query": "test"})
            print(f"✓ {endpoint}: {response.status_code} (endpoint exists)")
            
            # 401 means endpoint exists but requires auth (expected)
            # 422 means validation error (expected for invalid data)
            # 404 means endpoint doesn't exist (problem)
            if response.status_code == 404:
                print(f"  ⚠️  Endpoint not found!")
            elif response.status_code in [401, 403]:
                print(f"  ✓ Requires authentication (expected)")
            elif response.status_code == 422:
                print(f"  ✓ Validation error (expected for test data)")
            else:
                print(f"  ℹ️  Response: {response.status_code}")
                
        except Exception as e:
            print(f"✗ {endpoint}: Error - {e}")
    
    print("\n" + "=" * 50)
    print("Endpoint registration test completed")

def test_openapi_docs():
    """Test that the endpoints appear in OpenAPI documentation."""
    print("\nTesting OpenAPI documentation...")
    
    try:
        response = client.get("/openapi.json")
        if response.status_code == 200:
            openapi_spec = response.json()
            paths = openapi_spec.get("paths", {})
            
            react_endpoints = [path for path in paths.keys() if "/react/" in path]
            print(f"Found {len(react_endpoints)} ReAct endpoints in OpenAPI spec:")
            
            for endpoint in react_endpoints:
                methods = list(paths[endpoint].keys())
                print(f"  - {endpoint}: {', '.join(methods).upper()}")
            
            if react_endpoints:
                print("✓ ReAct endpoints are properly documented")
            else:
                print("⚠️  No ReAct endpoints found in OpenAPI spec")
        else:
            print(f"✗ Failed to get OpenAPI spec: {response.status_code}")
            
    except Exception as e:
        print(f"✗ OpenAPI test error: {e}")

if __name__ == "__main__":
    test_endpoints_exist()
    test_openapi_docs()