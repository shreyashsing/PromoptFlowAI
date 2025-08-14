#!/usr/bin/env python3

import asyncio
import sys
import os
import json

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_api_fix():
    """Test that the API fix works for the specific user request."""
    
    print("🧪 Testing API Fix")
    print("=" * 50)
    
    with TestClient(app) as client:
    
    # Test the specific user request that was failing
    test_message = "find top 5 blogs posted on ai agents and send it to shreyashbarca10@gmail.com"
    
    print(f"📝 Testing message: '{test_message}'")
    print()
    
        # Make the API request
        response = client.post(
            "/api/v1/agent/true-react/build-workflow",
            json={
                "request": test_message,
                "session_id": "test-session-123"
            },
            headers={
                "Authorization": "Bearer test-token"  # This will fail auth but we can see the intent analysis
            }
        )
    
        print(f"🎯 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"🎯 Success: {result.get('success', False)}")
            print(f"🎯 Phase: {result.get('phase', 'unknown')}")
            print(f"🎯 Is Conversational: {result.get('is_conversational', False)}")
            print(f"🎯 Needs Clarification: {result.get('needs_clarification', False)}")
            
            if result.get('message'):
                print(f"🎯 Message: {result['message'][:200]}...")
            
            print()
            
            # Check if it proceeds to workflow creation instead of asking for clarification
            if result.get('phase') == 'conversational' and result.get('needs_clarification'):
                print("❌ FAILED: Still asking for clarification despite clear request")
                print("❌ The API fix needs more work")
            elif result.get('phase') == 'planning' or result.get('success'):
                print("✅ SUCCESS: Proceeding with workflow creation")
                print("✅ The API fix is working!")
            else:
                print(f"🤔 UNCLEAR: Got phase '{result.get('phase')}' - need to investigate")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")

if __name__ == "__main__":
    test_api_fix()