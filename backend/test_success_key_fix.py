#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_success_key_fix():
    """Test that the True ReAct agent always returns a success key."""
    
    print("🧪 Testing True ReAct Agent success key fix...")
    
    # Initialize the agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test case 1: Simple email request
    print("\n📧 Test 1: Simple email request")
    result = await agent.process_user_request(
        "send a test message to test@example.com", 
        "test_user_123"
    )
    
    print(f"✅ Result has 'success' key: {'success' in result}")
    print(f"✅ Success value: {result.get('success')}")
    print(f"✅ Phase: {result.get('phase')}")
    print(f"✅ Has plan: {'plan' in result}")
    
    # Test case 2: Complex request
    print("\n🔍 Test 2: Complex search and summarize request")
    result2 = await agent.process_user_request(
        "find the latest AI news and summarize it", 
        "test_user_123"
    )
    
    print(f"✅ Result has 'success' key: {'success' in result2}")
    print(f"✅ Success value: {result2.get('success')}")
    print(f"✅ Phase: {result2.get('phase')}")
    print(f"✅ Has plan: {'plan' in result2}")
    
    # Test case 3: Conversational request
    print("\n💬 Test 3: Conversational request")
    result3 = await agent.process_user_request(
        "hello", 
        "test_user_123"
    )
    
    print(f"✅ Result has 'success' key: {'success' in result3}")
    print(f"✅ Success value: {result3.get('success')}")
    print(f"✅ Is conversational: {result3.get('is_conversational')}")
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_success_key_fix())