#!/usr/bin/env python3
"""
Simple test to verify the True ReAct endpoint is working.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_endpoints():
    client = TestClient(app)
    
    print("🔍 Testing health endpoint...")
    health_response = client.get("/api/v1/agent/health")
    print(f"Health status: {health_response.status_code}")
    
    print("\n🔍 Testing True ReAct endpoint...")
    test_payload = {"query": "Test workflow", "session_id": "test"}
    react_response = client.post("/api/v1/agent/true-react/build-workflow", json=test_payload)
    print(f"True ReAct status: {react_response.status_code}")
    
    if react_response.status_code == 404:
        print("❌ Still getting 404 - route not found")
    else:
        print("✅ Endpoint found!")
    
    print(f"\n📋 Available routes:")
    for route in app.routes:
        if hasattr(route, 'path') and '/agent/' in route.path:
            methods = list(route.methods) if hasattr(route, 'methods') else ['GET']
            print(f"  {methods[0]} {route.path}")

if __name__ == "__main__":
    test_endpoints()