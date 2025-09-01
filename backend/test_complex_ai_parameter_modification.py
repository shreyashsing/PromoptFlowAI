#!/usr/bin/env python3

import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_complex_ai_parameter_modification():
    """Test complex AI parameter modification scenarios where AI needs to think and generate content"""
    
    print("🧠 Testing Complex AI Parameter Modification Scenarios")
    print("=" * 60)
    
    # Test Case 1: Email body improvement request
    print("\n📧 Test Case 1: Email body improvement")
    workflow1 = {
        "steps": [
            {
                "connector_name": "gmail_connector",
                "task_number": 1,
                "parameters": {
                    "to": "user@example.com",
                    "subject": "Test",
                    "body": "Hi"
                }
            }
        ]
    }
    
    # User wants to make the email more professional
    change1 = {
        "type": "parameter_change",
        "task_number": 1,
        "current_connector": "gmail_connector",
        "parameter": "body",
        "old_value": "Hi",
        "new_value": None,  # No specific new value - AI needs to generate
        "reason": "Make the email body more professional and detailed"
    }
    
    agent = TrueReActAgent()
    
    # Test without specific new_value - should fall back to AI reasoning
    result1 = await agent._ai_modify_parameters(
        workflow1["steps"][0], 
        change1["reason"], 
        workflow1, 
        change1
    )
    
    print(f"Input: {change1['reason']}")
    print(f"Original body: '{change1['old_value']}'")
    print(f"AI Result: {json.dumps(result1, indent=2)}")
    
    # Test Case 2: Code generation request
    print("\n💻 Test Case 2: Code generation improvement")
    workflow2 = {
        "steps": [
            {
                "connector_name": "code_connector",
                "task_number": 1,
                "parameters": {
                    "language": "python",
                    "code": "print('hello')",
                    "description": "Simple hello world"
                }
            }
        ]
    }
    
    change2 = {
        "type": "parameter_change",
        "task_number": 1,
        "current_connector": "code_connector",
        "parameter": "code",
        "old_value": "print('hello')",
        "new_value": None,
        "reason": "Add error handling and make the code more robust with logging"
    }
    
    result2 = await agent._ai_modify_parameters(
        workflow2["steps"][0], 
        change2["reason"], 
        workflow2, 
        change2
    )
    
    print(f"Input: {change2['reason']}")
    print(f"Original code: '{change2['old_value']}'")
    print(f"AI Result: {json.dumps(result2, indent=2)}")
    
    # Test Case 3: Data formatting improvement
    print("\n📊 Test Case 3: Data formatting improvement")
    workflow3 = {
        "steps": [
            {
                "connector_name": "google_sheets_connector",
                "task_number": 1,
                "parameters": {
                    "spreadsheet_id": "abc123",
                    "range": "A1:B10",
                    "values": [["Name", "Age"], ["John", "25"]]
                }
            }
        ]
    }
    
    change3 = {
        "type": "parameter_change",
        "task_number": 1,
        "current_connector": "google_sheets_connector",
        "parameter": "values",
        "old_value": [["Name", "Age"], ["John", "25"]],
        "new_value": None,
        "reason": "Add more sample data with proper formatting and include headers with styling"
    }
    
    result3 = await agent._ai_modify_parameters(
        workflow3["steps"][0], 
        change3["reason"], 
        workflow3, 
        change3
    )
    
    print(f"Input: {change3['reason']}")
    print(f"Original values: {change3['old_value']}")
    print(f"AI Result: {json.dumps(result3, indent=2)}")
    
    # Test Case 4: Webhook payload enhancement
    print("\n🔗 Test Case 4: Webhook payload enhancement")
    workflow4 = {
        "steps": [
            {
                "connector_name": "webhook_connector",
                "task_number": 1,
                "parameters": {
                    "url": "https://api.example.com/webhook",
                    "method": "POST",
                    "payload": {"message": "test"}
                }
            }
        ]
    }
    
    change4 = {
        "type": "parameter_change",
        "task_number": 1,
        "current_connector": "webhook_connector",
        "parameter": "payload",
        "old_value": {"message": "test"},
        "new_value": None,
        "reason": "Include timestamp, user info, and proper error handling in the payload structure"
    }
    
    result4 = await agent._ai_modify_parameters(
        workflow4["steps"][0], 
        change4["reason"], 
        workflow4, 
        change4
    )
    
    print(f"Input: {change4['reason']}")
    print(f"Original payload: {change4['old_value']}")
    print(f"AI Result: {json.dumps(result4, indent=2)}")
    
    # Analyze results
    print("\n🔍 Analysis:")
    test_cases = [
        ("Email body improvement", result1),
        ("Code generation", result2),
        ("Data formatting", result3),
        ("Webhook payload", result4)
    ]
    
    ai_generated_count = 0
    for name, result in test_cases:
        if result and len(result) > 0:
            ai_generated_count += 1
            print(f"✅ {name}: AI generated content")
        else:
            print(f"❌ {name}: No AI content generated")
    
    print(f"\n📊 Summary: {ai_generated_count}/{len(test_cases)} test cases generated AI content")
    
    return ai_generated_count > 0

if __name__ == "__main__":
    success = asyncio.run(test_complex_ai_parameter_modification())
    sys.exit(0 if success else 1)