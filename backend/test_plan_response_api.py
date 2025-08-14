#!/usr/bin/env python3

import asyncio
import sys
import os
import json

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_plan_response_api():
    """Test what the plan-response API endpoint actually returns."""
    
    print("🧪 Testing plan-response API endpoint...")
    
    # Mock user context
    mock_user = {
        'user_id': 'test_user_123',
        'email': 'test@example.com'
    }
    
    # Create a mock plan (this would normally come from the planning phase)
    mock_plan = {
        "summary": "Send a test email message to test@example.com",
        "tasks": [
            {
                "task_number": 1,
                "description": "Send a test email message to test@example.com",
                "suggested_tool": "gmail_connector",
                "reasoning": "Enhanced planner selected gmail_connector for optimal workflow execution",
                "inputs": ["user request"],
                "outputs": ["email sent"],
                "estimated_duration": 5.0
            }
        ],
        "data_flow": "Optimized sequence with intelligent tool chaining",
        "estimated_steps": 1,
        "enhanced_planning": True
    }
    
    try:
        
        agent = TrueReActAgent()
        await agent.initialize()
        
        result = await agent.handle_user_response(
            "approve",
            "test_user_123", 
            mock_plan
        )
        
        print(f"✅ Plan approval result:")
        print(f"   Success: {result.get('success')}")
        print(f"   Phase: {result.get('phase')}")
        print(f"   Has Workflow: {'workflow' in result}")
        print(f"   Message: {result.get('message', 'No message')}")
        
        if result.get('workflow'):
            workflow = result['workflow']
            print(f"   Workflow Keys: {list(workflow.keys())}")
            print(f"   Workflow ID: {workflow.get('id')}")
            print(f"   Workflow Name: {workflow.get('name')}")
            print(f"   Workflow Steps: {len(workflow.get('steps', []))}")
            
            if workflow.get('steps'):
                for i, step in enumerate(workflow['steps']):
                    print(f"     Step {i+1}: {step.get('connector_name')} - {step.get('purpose')}")
                    print(f"       Parameters: {step.get('parameters', {})}")
        else:
            print("   ❌ No workflow in response")
            print(f"   Full response keys: {list(result.keys())}")
            
        # Now let's see what the API endpoint would return
        print(f"\n🔍 What the API endpoint would return:")
        print(f"   result.get('workflow'): {result.get('workflow') is not None}")
        if result.get('workflow'):
            print(f"   Workflow object: {json.dumps(result['workflow'], indent=2)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_plan_response_api())