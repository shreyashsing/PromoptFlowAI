"""
Test the core ReAct agent infrastructure.
"""
import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.react_agent_service import ReactAgentService
from app.services.tool_registry import ToolRegistry
from app.services.conversation_memory_manager import ConversationMemoryManager

async def test_react_agent_infrastructure():
    """Test the core ReAct agent infrastructure components."""
    print("Testing ReAct Agent Infrastructure...")
    
    try:
        # Test Tool Registry
        print("\n1. Testing Tool Registry...")
        tool_registry = ToolRegistry()
        await tool_registry.initialize()
        
        tools = await tool_registry.get_available_tools()
        print(f"   ✓ Tool Registry initialized with {len(tools)} tools")
        
        metadata = await tool_registry.get_tool_metadata()
        print(f"   ✓ Retrieved metadata for {len(metadata)} tools")
        
        # Test Conversation Memory Manager
        print("\n2. Testing Conversation Memory Manager...")
        memory_manager = ConversationMemoryManager()
        await memory_manager.initialize()
        print(f"   ✓ Memory Manager initialized")
        
        # Test creating a conversation
        conversation = await memory_manager.get_or_create_conversation(
            session_id="test-session-123",
            user_id="test-user-456"
        )
        print(f"   ✓ Created conversation: {conversation.session_id}")
        
        # Test adding a message
        await memory_manager.add_message(
            session_id="test-session-123",
            role="user",
            content="Hello, this is a test message"
        )
        print(f"   ✓ Added message to conversation")
        
        # Test ReAct Agent Service
        print("\n3. Testing ReAct Agent Service...")
        react_service = ReactAgentService()
        await react_service.initialize()
        print(f"   ✓ ReAct Agent Service initialized")
        
        # Test processing a request
        response = await react_service.process_request(
            query="Test query for ReAct agent",
            user_id="test-user-456"
        )
        print(f"   ✓ Processed request, got response: {response['status']}")
        
        # Test health check
        health = await react_service.health_check()
        print(f"   ✓ Health check: {health['status']}")
        
        # Test getting available tools
        available_tools = await react_service.get_available_tools()
        print(f"   ✓ Retrieved {len(available_tools)} available tools")
        
        print("\n✅ All infrastructure tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Infrastructure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_react_agent_infrastructure())
    sys.exit(0 if success else 1)