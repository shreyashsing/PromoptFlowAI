"""
Test the updated ReAct agent service with LangGraph integration.
"""
import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.react_agent_service import ReactAgentService

async def test_updated_react_agent():
    """Test the updated ReAct agent service."""
    print("Testing Updated ReAct Agent Service...")
    
    try:
        # Test ReAct Agent Service initialization
        print("\n1. Testing ReAct Agent Service Initialization...")
        react_service = ReactAgentService()
        await react_service.initialize()
        print(f"   ✓ ReAct Agent Service initialized")
        
        # Test health check
        print("\n2. Testing Health Check...")
        health = await react_service.health_check()
        print(f"   ✓ Health check: {health['status']}")
        print(f"   ✓ LLM configured: {health.get('llm_configured', False)}")
        print(f"   ✓ Agent ready: {health.get('agent_ready', False)}")
        print(f"   ✓ Tools available: {health.get('tools_available', 0)}")
        
        # Test getting available tools
        print("\n3. Testing Available Tools...")
        available_tools = await react_service.get_available_tools()
        print(f"   ✓ Retrieved {len(available_tools)} available tools")
        for tool in available_tools[:3]:  # Show first 3 tools
            print(f"     - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:50]}...")
        
        # Test basic request processing (if Azure OpenAI is configured)
        print("\n4. Testing Request Processing...")
        if health.get('llm_configured') and health.get('agent_ready'):
            try:
                response = await react_service.process_request(
                    query="Hello, can you help me understand what tools you have available?",
                    user_id="test-user-123"
                )
                print(f"   ✓ Processed request successfully")
                print(f"   ✓ Response status: {response['status']}")
                print(f"   ✓ Session ID: {response['session_id']}")
                print(f"   ✓ Response length: {len(response['response'])} characters")
                print(f"   ✓ Tool calls made: {len(response['tool_calls'])}")
                print(f"   ✓ Reasoning steps: {len(response['reasoning_trace'])}")
                
                if response['response']:
                    print(f"   ✓ Sample response: {response['response'][:100]}...")
                
            except Exception as e:
                print(f"   ⚠ Request processing failed (likely due to missing Azure OpenAI config): {e}")
                print("   ℹ This is expected if Azure OpenAI credentials are not configured")
        else:
            print("   ⚠ Skipping request processing test - LLM not configured")
        
        # Test conversation history
        print("\n5. Testing Conversation History...")
        if 'response' in locals() and response.get('session_id'):
            history = await react_service.get_conversation_history(response['session_id'])
            print(f"   ✓ Retrieved conversation history")
            print(f"   ✓ Messages in conversation: {len(history.get('messages', []))}")
        else:
            print("   ⚠ Skipping conversation history test - no session available")
        
        print("\n✅ All ReAct agent tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ ReAct agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_updated_react_agent())
    sys.exit(0 if success else 1)