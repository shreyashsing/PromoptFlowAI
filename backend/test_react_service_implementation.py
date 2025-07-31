#!/usr/bin/env python3
"""
Test script to verify ReAct Agent Service implementation.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_react_service_implementation():
    """Test the ReAct Agent Service implementation."""
    print("Testing ReAct Agent Service implementation...")
    
    try:
        # Import the service
        from app.services.react_agent_service import ReactAgentService, get_react_agent_service
        print("✓ Successfully imported ReactAgentService")
        
        # Create service instance
        service = ReactAgentService()
        print("✓ Successfully created ReactAgentService instance")
        
        # Test initialization
        await service.initialize()
        print("✓ Successfully initialized ReactAgentService")
        
        # Test health check
        health = await service.health_check()
        print(f"✓ Health check completed: {health['status']}")
        print(f"  - Tools available: {health['tools_available']}")
        print(f"  - LLM configured: {health['llm_configured']}")
        print(f"  - Agent ready: {health['agent_ready']}")
        print(f"  - Active sessions: {health['active_sessions']}")
        
        # Test tool registry
        tools = await service.get_available_tools()
        print(f"✓ Retrieved {len(tools)} available tools")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test conversation management
        session_id = "test-session-123"
        user_id = "test-user"
        
        # Test conversation creation and message processing
        print(f"\n✓ Testing conversation management...")
        
        # Get conversation history (should be empty initially)
        history = await service.get_conversation_history(session_id)
        print(f"  - Initial conversation status: {history['status']}")
        
        # Test process request (will use fallback if Azure OpenAI not configured)
        print(f"\n✓ Testing request processing...")
        response = await service.process_request(
            query="Hello, can you help me test the system?",
            session_id=session_id,
            user_id=user_id
        )
        
        print(f"  - Response status: {response['status']}")
        print(f"  - Processing time: {response['processing_time_ms']}ms")
        print(f"  - Iterations used: {response['iterations_used']}")
        print(f"  - Tools used: {response['tools_used']}")
        print(f"  - Response: {response['response'][:100]}...")
        
        # Test conversation history after interaction
        history = await service.get_conversation_history(session_id)
        print(f"  - Conversation after interaction: {history['summary']['message_count']} messages")
        
        # Test session cleanup
        cleanup_result = await service.cleanup_session(session_id)
        print(f"  - Session cleanup: {'successful' if cleanup_result else 'failed'}")
        
        print(f"\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_react_service_implementation())
    sys.exit(0 if success else 1)