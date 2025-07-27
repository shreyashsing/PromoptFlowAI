#!/usr/bin/env python3
"""
Test script for conversation API endpoints.
"""
import asyncio
import httpx
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

async def test_conversation_api():
    """Test the conversation API endpoints."""
    
    async with httpx.AsyncClient() as client:
        # Test headers with dev token
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer dev-test-token"
        }
        
        print("🧪 Testing Conversation API Endpoints")
        print("=" * 50)
        
        # Test 1: List conversations (should be empty initially)
        print("\n1. Testing GET /api/v1/agent/conversations")
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/agent/conversations",
                headers=headers
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                conversations = response.json()
                print(f"Found {len(conversations)} conversations")
                for conv in conversations[:3]:  # Show first 3
                    print(f"  - {conv['session_id']}: {conv['state']} ({len(conv.get('messages', []))} messages)")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: Start a new conversation
        print("\n2. Testing POST /api/v1/agent/run-agent")
        session_id = None
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/agent/run-agent",
                headers=headers,
                json={"prompt": "Create a workflow to send me daily weather updates"}
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                session_id = data["session_id"]
                print(f"Created conversation: {session_id}")
                print(f"State: {data['conversation_state']}")
                print(f"Response: {data['message'][:100]}...")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: Continue the conversation
        if session_id:
            print("\n3. Testing POST /api/v1/agent/chat-agent")
            try:
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/agent/chat-agent",
                    headers=headers,
                    json={
                        "message": "Yes, that sounds good. Please create the workflow.",
                        "session_id": session_id
                    }
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"State: {data['conversation_state']}")
                    print(f"Response: {data['message'][:100]}...")
                else:
                    print(f"Error: {response.text}")
            except Exception as e:
                print(f"Error: {e}")
        
        # Test 4: Get specific conversation
        if session_id:
            print(f"\n4. Testing GET /api/v1/agent/conversations/{session_id}")
            try:
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/agent/conversations/{session_id}",
                    headers=headers
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"Session: {data['session_id']}")
                    print(f"Messages: {len(data['messages'])}")
                    print(f"State: {data['state']}")
                    print(f"Created: {data['created_at']}")
                else:
                    print(f"Error: {response.text}")
            except Exception as e:
                print(f"Error: {e}")
        
        # Test 5: List conversations again (should show the new one)
        print("\n5. Testing GET /api/v1/agent/conversations (after creating)")
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/agent/conversations",
                headers=headers
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                conversations = response.json()
                print(f"Found {len(conversations)} conversations")
                for conv in conversations[:3]:  # Show first 3
                    print(f"  - {conv['session_id']}: {conv['state']} ({len(conv.get('messages', []))} messages)")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 6: Delete conversation
        if session_id:
            print(f"\n6. Testing DELETE /api/v1/agent/conversations/{session_id}")
            try:
                response = await client.delete(
                    f"{API_BASE_URL}/api/v1/agent/conversations/{session_id}",
                    headers=headers
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"Result: {data['message']}")
                else:
                    print(f"Error: {response.text}")
            except Exception as e:
                print(f"Error: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Conversation API test completed!")

if __name__ == "__main__":
    asyncio.run(test_conversation_api())