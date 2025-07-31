"""
Basic test to verify ReAct agent API endpoints are accessible.
"""
import requests
import json

def test_basic_endpoint_access():
    """Test basic endpoint accessibility."""
    print("Testing ReAct Agent API Endpoint Accessibility")
    print("=" * 50)
    
    # Assuming the server is running on localhost:8000
    base_url = "http://localhost:8000"
    
    # Test endpoints
    endpoints_to_test = [
        ("/api/v1/react/status", "GET"),
        ("/api/v1/react/tools", "GET"), 
        ("/api/v1/react/chat", "POST"),
        ("/api/v1/react/metrics", "GET"),
        ("/api/v1/react/health", "GET"),
    ]
    
    print("Note: This test requires the FastAPI server to be running.")
    print("Start the server with: python -m uvicorn app.main:app --reload")
    print()
    
    for endpoint, method in endpoints_to_test:
        url = f"{base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, json={"query": "test"}, timeout=5)
            
            print(f"✓ {method} {endpoint}: {response.status_code}")
            
            if response.status_code == 404:
                print(f"  ⚠️  Endpoint not found!")
            elif response.status_code in [401, 403]:
                print(f"  ✓ Requires authentication (expected)")
            elif response.status_code == 422:
                print(f"  ✓ Validation error (expected for test data)")
            else:
                print(f"  ℹ️  Response: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"✗ {method} {endpoint}: Server not running")
        except requests.exceptions.Timeout:
            print(f"✗ {method} {endpoint}: Timeout")
        except Exception as e:
            print(f"✗ {method} {endpoint}: Error - {e}")
    
    print("\n" + "=" * 50)
    print("Basic endpoint accessibility test completed")

def test_openapi_spec():
    """Test OpenAPI specification accessibility."""
    print("\nTesting OpenAPI specification...")
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=5)
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
            
    except requests.exceptions.ConnectionError:
        print("✗ Server not running - cannot test OpenAPI spec")
    except Exception as e:
        print(f"✗ OpenAPI test error: {e}")

if __name__ == "__main__":
    test_basic_endpoint_access()
    test_openapi_spec()