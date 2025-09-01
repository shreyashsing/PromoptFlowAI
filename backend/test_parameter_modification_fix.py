#!/usr/bin/env python3

import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_parameter_modification():
    """Test the parameter modification fix"""
    
    # Create a mock workflow with Gmail connector
    workflow = {
        "steps": [
            {
                "connector_name": "gmail_connector",
                "task_number": 1,
                "parameters": {
                    "to": "shreyashbarca10@gmail.com",
                    "subject": "Test Message",
                    "body": "Hello World"
                }
            }
        ]
    }
    
    # Create a change object like the one from the logs
    change = {
        "type": "parameter_change",
        "task_number": 1,
        "current_connector": "gmail_connector",
        "parameter": "to",
        "old_value": "shreyashbarca10@gmail.com",
        "new_value": "19sumanshreya@gmail.com",
        "reason": "User requested to change the recipient email address."
    }
    
    # Create agent instance
    agent = TrueReActAgent()
    
    # Test the AI parameter modification function directly
    step = workflow["steps"][0]
    result = await agent._ai_modify_parameters(
        step, 
        change["reason"], 
        workflow, 
        change
    )
    
    print("🔍 Parameter modification test results:")
    print(f"Input change: {json.dumps(change, indent=2)}")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Verify the result
    expected_result = {"to": "19sumanshreya@gmail.com"}
    if result == expected_result:
        print("✅ Test PASSED: Parameter modification works correctly")
        return True
    else:
        print(f"❌ Test FAILED: Expected {expected_result}, got {result}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_parameter_modification())
    sys.exit(0 if success else 1)