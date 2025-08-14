#!/usr/bin/env python3

import asyncio
import sys
import os
import json

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_plan_response():
    """Test the complete plan creation and approval flow."""
    
    print("🧪 Testing complete plan creation and approval flow...")
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Step 1: Create a plan
    print("\n📧 Step 1: Create workflow plan")
    result1 = await agent.process_user_request(
        "send a test message to test@example.com", 
        "test_user_123"
    )
    
    print(f"✅ Plan creation result:")
    print(f"   Success: {result1.get('success')}")
    print(f"   Phase: {result1.get('phase')}")
    print(f"   Has Plan: {'plan' in result1}")
    print(f"   Awaiting Approval: {result1.get('awaiting_approval')}")
    
    if result1.get('success') and result1.get('plan'):
        plan = result1['plan']
        print(f"   Plan Tasks: {len(plan.get('tasks', []))}")
        
        # Step 2: Approve the plan
        print("\n✅ Step 2: Approve the plan")
        result2 = await agent.handle_user_response(
            "approve",
            "test_user_123", 
            plan
        )
        
        print(f"✅ Plan approval result:")
        print(f"   Success: {result2.get('success')}")
        print(f"   Phase: {result2.get('phase')}")
        print(f"   Has Workflow: {'workflow' in result2}")
        print(f"   Message: {result2.get('message', 'No message')}")
        
        if result2.get('workflow'):
            workflow = result2['workflow']
            print(f"   Workflow ID: {workflow.get('id')}")
            print(f"   Workflow Name: {workflow.get('name')}")
            print(f"   Workflow Steps: {len(workflow.get('steps', []))}")
            
            if workflow.get('steps'):
                for i, step in enumerate(workflow['steps']):
                    print(f"     Step {i+1}: {step.get('connector_name')} - {step.get('purpose')}")
        else:
            print("   ❌ No workflow in response")
            print(f"   Full response keys: {list(result2.keys())}")

if __name__ == "__main__":
    asyncio.run(test_plan_response())