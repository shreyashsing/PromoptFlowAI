#!/usr/bin/env python3
"""
Test script to verify ReAct agent API can handle new sessions.
"""

import asyncio
import json
import sys
import os
import httpx

# Test the ReAct agent API endpoint directly
async def test_react_api_new_session():
    """Test that ReAct agent API can handle new sessions without session_id."""
    
    print("🧪 Testing ReAct agent API new session handling...")
    
    base_url = "http://localhost:8000"
    
    # Test payload without session_id (new conversation)
    payload = {
        "query": "Hello, can you help me test this ReAct agent?",
        "max_iterations": 3
        # No session_id - should create new session
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer dev-test-token"  # Use dev token for testing
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"📝 Making POST request to {base_url}/api/v1/react/chat")
            print(f"📝 Payload: {json.dumps(payload, indent=2)}")
            
            response = await client.post(
                f"{base_url}/api/v1/react/chat",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            print(f"📝 Response status: {response.status_code}")
            print(f"📝 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success! ReAct agent API handled new session correctly")
                print(f"✅ Session ID: {result.get('session_id')}")
                print(f"✅ Response: {result.get('response', '')[:100]}...")
                print(f"✅ Status: {result.get('status')}")
                print(f"✅ Iterations used: {result.get('iterations_used')}")
                print(f"✅ Tools used: {result.get('tools_used')}")
                return True
            else:
                print(f"❌ API request failed with status {response.status_code}")
                print(f"❌ Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_react_api_new_session())
    sys.exit(0 if success else 1)