#!/usr/bin/env python3
"""
Test script to verify FastAPI endpoints are properly configured.
"""
import sys
sys.path.append('.')

from app.main import app
from fastapi.testclient import TestClient

def test_endpoints():
    """Test that all required endpoints are available."""
    client = TestClient(app)
    
    # Test basic health endpoints
    response = client.get("/")
    print(f"Root endpoint: {response.status_code}")
    
    response = client.get("/health")
    print(f"Health endpoint: {response.status_code}")
    
    # Test API documentation
    response = client.get("/docs")
    print(f"API docs endpoint: {response.status_code}")
    
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    print(f"OpenAPI schema: {response.status_code}")
    
    if response.status_code == 200:
        openapi_data = response.json()
        paths = openapi_data.get("paths", {})
        
        # Check for required endpoints
        required_endpoints = [
            "/api/v1/agent/run-agent",
            "/api/v1/agent/chat-agent", 
            "/api/v1/workflows",
            "/api/v1/executions/{execution_id}"
        ]
        
        print("\nChecking required endpoints:")
        for endpoint in required_endpoints:
            # Handle parameterized endpoints
            endpoint_key = endpoint.replace("{execution_id}", "{execution_id}")
            if endpoint_key in paths:
                print(f"✓ {endpoint}")
            else:
                # Check if it exists with different parameter format
                found = False
                for path in paths.keys():
                    if endpoint.replace("{execution_id}", "").rstrip("/") in path:
                        print(f"✓ {endpoint} (found as {path})")
                        found = True
                        break
                if not found:
                    print(f"✗ {endpoint}")
        
        print(f"\nTotal endpoints available: {len(paths)}")
        print("Available endpoints:")
        for path, methods in paths.items():
            method_list = list(methods.keys())
            print(f"  {path}: {method_list}")

if __name__ == "__main__":
    test_endpoints()