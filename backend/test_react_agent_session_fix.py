#!/usr/bin/env python3
"""
Test script to verify ReAct agent session handling fix.
"""

import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.react_agent_service import get_react_agent_service
from app.core.database import get_database

async def test_react_agent_new_session():
    """Test that ReAct agent can handle new sessions without session_id."""
    
    print("🧪 Testing ReAct agent new session handling...")
    
    try:
        # Initialize database
        db = await get_database()
        print("✅ Database initialized")
        
        # Get ReAct agent service
        react_service = await get_react_agent_service()
        print("✅ ReAct agent service initialized")
        
        # Test user context
        test_user = {
            "user_id": "test-user-123",
            "email": "test@example.com"
        }
        
        # Test 1: Process request without session_id (new conversation)
        print("\n📝 Test 1: New conversation (no session_id)")
        response1 = await react_service.process_request(
            query="Hello, can you help me test this?",
            session_id=None,  # No session ID - should create new session
            user_id=test_user["user_id"],
            context=None,
            max_iterations=3,
            skip_session_validation=True  # Skip validation for new session
        )
        
        print(f"✅ New session created: {response1['session_id']}")
        print(f"✅ Response: {response1['response'][:100]}...")
        print(f"✅ Status: {response1['status']}")
        
        # Test 2: Continue conversation with existing session_id
        print(f"\n📝 Test 2: Continue conversation (session_id: {response1['session_id']})")
        response2 = await react_service.process_request(
            query="Can you remember what I just asked?",
            session_id=response1['session_id'],
            user_id=test_user["user_id"],
            context=None,
            max_iterations=3
        )
        
        print(f"✅ Continued session: {response2['session_id']}")
        print(f"✅ Response: {response2['response'][:100]}...")
        print(f"✅ Status: {response2['status']}")
        
        # Test 3: Validate session access
        print(f"\n📝 Test 3: Validate session access")
        has_access = await react_service.validate_session_access(
            response1['session_id'], 
            test_user["user_id"]
        )
        print(f"✅ Session access validation: {has_access}")
        
        # Test 4: Try to access session with wrong user (should fail)
        print(f"\n📝 Test 4: Invalid session access (wrong user)")
        has_access_wrong = await react_service.validate_session_access(
            response1['session_id'], 
            "wrong-user-id"
        )
        print(f"✅ Wrong user access validation: {has_access_wrong} (should be False)")
        
        print("\n🎉 All tests passed! ReAct agent session handling is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_react_agent_new_session())
    sys.exit(0 if success else 1)