#!/usr/bin/env python3
"""
Test script to verify the plan-response endpoint works correctly.
"""
import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from app.core.config import settings

async def test_plan_response_endpoint():
    """Test that the plan-response endpoint is accessible."""
    
    # Test data
    test_request = {
        "response": "approve",
        "session_id": "test_session_123",
        "current_plan": {
            "summary": "Test workflow",
            "tasks": [
                {
                    "task_number": 1,
                    "description": "Test task",
                    "suggested_tool": "text_summarizer",
                    "reasoning": "Test reasoning",
                    "inputs": ["test_input"],
                    "outputs": ["test_output"]
                }
            ],
            "data_flow": "test_flow",
            "estimated_steps": "1"
        }
    }
    
    # Test the endpoint URL
    base_url = "http://localhost:8000"
    endpoint_url = f"{base_url}/api/v1/agent/true-react/plan-response"
    
    print(f"🧪 Testing endpoint: {endpoint_url}")
    
    try:
        # Test OPTIONS request (CORS preflight)
        options_response = requests.options(endpoint_url)
        print(f"📋 OPTIONS response: {options_response.status_code}")
        
        # Test POST request (this will fail due to auth, but should not be 404)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer fake_token_for_testing"
        }
        
        post_response = requests.post(
            endpoint_url, 
            json=test_request, 
            headers=headers
        )
        
        print(f"📋 POST response: {post_response.status_code}")
        
        if post_response.status_code == 404:
            print("❌ Endpoint still returns 404 - not found")
        elif post_response.status_code == 401:
            print("✅ Endpoint found but requires authentication (expected)")
        elif post_response.status_code == 422:
            print("✅ Endpoint found but validation failed (expected)")
        else:
            print(f"📋 Response: {post_response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")

if __name__ == "__main__":
    asyncio.run(test_plan_response_endpoint())