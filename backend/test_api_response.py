#!/usr/bin/env python3

import asyncio
import sys
import os
import json

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_api_response():
    """Test the API response directly."""
    
    print("🧪 Testing API response for workflow request...")
    
    try:
        
        agent = TrueReActAgent()
        await agent.initialize()
        
        result = await agent.process_user_request(
            "hii",
            "test_user_123"
        )
        
        print(f"✅ API Response:")
        print(f"   Success: {result.get('success')}")
        print(f"   Phase: {result.get('phase')}")
        print(f"   Has Plan: {'plan' in result}")
        print(f"   Has Message: {'message' in result}")
        print(f"   Awaiting Approval: {result.get('awaiting_approval')}")
        
        if result.get('plan'):
            plan = result['plan']
            print(f"   Plan Tasks: {len(plan.get('tasks', []))}")
            if plan.get('tasks'):
                print(f"   First Task: {plan['tasks'][0].get('description', 'No description')}")
        
        if result.get('message'):
            print(f"   Message Preview: {result['message'][:100]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_response())