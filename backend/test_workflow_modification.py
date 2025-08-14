#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_workflow_modification():
    """Test workflow modification with conversational input."""
    
    print("🧪 Testing workflow modification with conversational input...")
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # First, create a workflow
    print("\n📧 Step 1: Create initial workflow")
    result1 = await agent.process_user_request(
        "send a test message to test@example.com", 
        "test_user_123"
    )
    
    print(f"✅ Initial workflow - Success: {result1.get('success')}, Phase: {result1.get('phase')}")
    
    # Simulate approval and execution (this would normally happen via the plan-response endpoint)
    if result1.get('success') and result1.get('plan'):
        print("\n✅ Step 2: Simulate plan approval and execution")
        
        # Simulate the execution result
        executed_workflow = {
            "id": "workflow_123",
            "name": "Test Email Workflow",
            "steps": [
                {
                    "connector_name": "gmail_connector",
                    "purpose": "Send test email",
                    "parameters": {"to": "test@example.com", "subject": "Test", "body": "Test message"}
                }
            ]
        }
        
        # Now test workflow modification with a conversational input
        print("\n💬 Step 3: Test conversational input after workflow execution")
        
        # Simulate session context (this would normally be stored by the API)
        session_context = {
            "executed_workflow": executed_workflow,
            "original_plan": result1.get('plan'),
            "user_id": "test_user_123",
            "completed_at": 1234567890,
            "awaiting_approval": False
        }
        
        # Test the handle_workflow_modification method directly
        result2 = await agent.handle_workflow_modification(
            "hii", 
            "test_user_123", 
            session_context
        )
        
        print(f"✅ Conversational input result:")
        print(f"   Success: {result2.get('success')}")
        print(f"   Phase: {result2.get('phase')}")
        print(f"   Is Conversational: {result2.get('is_conversational')}")
        print(f"   Error: {result2.get('error')}")
        print(f"   Has Plan: {'plan' in result2}")
        
        if result2.get('message'):
            print(f"   Message: {result2['message'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_workflow_modification())