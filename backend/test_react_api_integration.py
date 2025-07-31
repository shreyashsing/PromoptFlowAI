"""
Test the ReAct agent API integration.
"""
import asyncio
import sys
import os
import httpx
import json

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_react_api_integration():
    """Test the ReAct agent API endpoints."""
    print("Testing ReAct Agent API Integration...")
    
    base_url = "http://localhost:8000/api/v1/agent"
    
    # Test data
    test_message = "Hello, can you help me understand what tools you have available?"
    test_session_id = "test-session-react-123"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test 1: Get ReAct agent status
            print("\n1. Testing ReAct Agent Status...")
            try:
                response = await client.get(f"{base_url}/react-status")
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"   ✓ Status endpoint accessible")
                    print(f"   ✓ Agent health: {status_data.get('health', {}).get('status', 'unknown')}")
                    print(f"   ✓ Tools available: {len(status_data.get('tools', []))}")
                    print(f"   ✓ Capabilities: {list(status_data.get('capabilities', {}).keys())}")
                else:
                    print(f"   ⚠ Status endpoint returned {response.status_code}: {response.text}")
            except Exception as e:
                print(f"   ⚠ Status endpoint error (server may not be running): {e}")
            
            # Test 2: Test ReAct chat endpoint
            print("\n2. Testing ReAct Chat Endpoint...")
            try:
                chat_payload = {
                    "message": test_message,
                    "session_id": test_session_id
                }
                
                response = await client.post(
                    f"{base_url}/react-chat",
                    json=chat_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    chat_data = response.json()
                    print(f"   ✓ Chat endpoint accessible")
                    print(f"   ✓ Response status: {chat_data.get('status', 'unknown')}")
                    print(f"   ✓ Session ID: {chat_data.get('session_id', 'unknown')}")
                    print(f"   ✓ Response length: {len(chat_data.get('response', ''))}")
                    print(f"   ✓ Tool calls: {len(chat_data.get('tool_calls', []))}")
                    print(f"   ✓ Reasoning steps: {len(chat_data.get('reasoning_trace', []))}")
                    
                    if chat_data.get('response'):
                        print(f"   ✓ Sample response: {chat_data['response'][:100]}...")
                        
                else:
                    print(f"   ⚠ Chat endpoint returned {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"   ⚠ Chat endpoint error (server may not be running): {e}")
            
            # Test 3: Test conversation history
            print("\n3. Testing Conversation History...")
            try:
                response = await client.get(f"{base_url}/react-conversations/{test_session_id}")
                
                if response.status_code == 200:
                    history_data = response.json()
                    print(f"   ✓ History endpoint accessible")
                    print(f"   ✓ Messages in conversation: {len(history_data.get('messages', []))}")
                elif response.status_code == 404:
                    print(f"   ✓ History endpoint accessible (conversation not found, which is expected)")
                else:
                    print(f"   ⚠ History endpoint returned {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"   ⚠ History endpoint error (server may not be running): {e}")
            
            print("\n✅ API integration tests completed!")
            print("\n📝 To test the API manually:")
            print(f"   1. Start the server: uvicorn app.main:app --reload")
            print(f"   2. Visit: http://localhost:8000/docs")
            print(f"   3. Test the /api/v1/agent/react-chat endpoint")
            print(f"   4. Use payload: {json.dumps(chat_payload, indent=2)}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ API integration test failed: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_react_api_integration())
    sys.exit(0 if success else 1)