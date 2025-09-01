#!/usr/bin/env python3

import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_full_parameter_modification():
    """Test the full parameter modification workflow"""
    
    # Create a mock workflow with Gmail connector
    workflow = {
        "steps": [
            {
                "connector_name": "gmail_connector",
                "task_number": 1,
                "step_number": 1,
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
    
    # Test the full parameter modification function
    result = await agent._modify_connector_parameters(
        workflow, 
        change, 
        "test_user_id"
    )
    
    print("🔍 Full parameter modification test results:")
    print(f"Input change: {json.dumps(change, indent=2)}")
    print(f"Result: {json.dumps(result, indent=2)}")
    print(f"Updated workflow: {json.dumps(workflow, indent=2)}")
    
    # Verify the result
    if (result.get("success") and 
        workflow["steps"][0]["parameters"]["to"] == "19sumanshreya@gmail.com"):
        print("✅ Test PASSED: Full parameter modification works correctly")
        return True
    else:
        print("❌ Test FAILED: Full parameter modification did not work as expected")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_parameter_modification())
    sys.exit(0 if success else 1)