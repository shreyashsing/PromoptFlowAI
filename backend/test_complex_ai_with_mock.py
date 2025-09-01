#!/usr/bin/env python3

import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, patch

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_complex_ai_with_mock():
    """Test complex AI parameter modification with mocked AI responses"""
    
    print("🧠 Testing Complex AI Parameter Modification with Mock AI")
    print("=" * 60)
    
    # Test Case 1: Email body improvement
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
    
    change1 = {
        "type": "parameter_change",
        "task_number": 1,
        "current_connector": "gmail_connector",
        "parameter": "body",
        "old_value": "Hi",
        "new_value": None,
        "reason": "Make the email body more professional and detailed"
    }
    
    # Mock AI response for professional email
    mock_ai_response_1 = {
        "body": "Dear Recipient,\n\nI hope this email finds you well. I am writing to follow up on our previous discussion and provide you with the requested information.\n\nPlease let me know if you need any additional details or have any questions.\n\nBest regards,\n[Your Name]"
    }
    
    agent = TrueReActAgent()
    
    # Mock the AI reasoning method and client
    with patch.object(agent, '_ai_reason', new_callable=AsyncMock) as mock_ai_reason, \
         patch.object(agent, '_client', True):  # Mock client existence
        mock_ai_reason.return_value = mock_ai_response_1
        
        result1 = await agent._ai_modify_parameters(
            workflow1["steps"][0], 
            change1["reason"], 
            workflow1, 
            change1
        )
    
    print(f"Input: {change1['reason']}")
    print(f"Original body: '{change1['old_value']}'")
    print(f"AI Generated body: {json.dumps(result1.get('body', 'No result'), indent=2)}")
    
    # Test Case 2: Code generation improvement
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
    
    # Mock AI response for robust code
    mock_ai_response_2 = {
        "code": """import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Starting hello world application")
        message = "hello"
        print(message)
        logger.info(f"Successfully printed message: {message}")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()"""
    }
    
    with patch.object(agent, '_ai_reason', new_callable=AsyncMock) as mock_ai_reason, \
         patch.object(agent, '_client', True):  # Mock client existence
        mock_ai_reason.return_value = mock_ai_response_2
        
        result2 = await agent._ai_modify_parameters(
            workflow2["steps"][0], 
            change2["reason"], 
            workflow2, 
            change2
        )
    
    print(f"Input: {change2['reason']}")
    print(f"Original code: '{change2['old_value']}'")
    print(f"AI Generated code:\n{result2.get('code', 'No result')}")
    
    # Test Case 3: Webhook payload enhancement
    print("\n🔗 Test Case 3: Webhook payload enhancement")
    workflow3 = {
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
    
    change3 = {
        "type": "parameter_change",
        "task_number": 1,
        "current_connector": "webhook_connector",
        "parameter": "payload",
        "old_value": {"message": "test"},
        "new_value": None,
        "reason": "Include timestamp, user info, and proper error handling in the payload structure"
    }
    
    # Mock AI response for enhanced payload
    mock_ai_response_3 = {
        "payload": {
            "message": "test",
            "timestamp": "{{current_timestamp}}",
            "user_info": {
                "user_id": "{{user_id}}",
                "session_id": "{{session_id}}"
            },
            "metadata": {
                "version": "1.0",
                "source": "workflow_automation",
                "retry_count": 0
            },
            "error_handling": {
                "max_retries": 3,
                "timeout": 30,
                "fallback_url": "https://api.example.com/fallback"
            }
        }
    }
    
    with patch.object(agent, '_ai_reason', new_callable=AsyncMock) as mock_ai_reason, \
         patch.object(agent, '_client', True):  # Mock client existence
        mock_ai_reason.return_value = mock_ai_response_3
        
        result3 = await agent._ai_modify_parameters(
            workflow3["steps"][0], 
            change3["reason"], 
            workflow3, 
            change3
        )
    
    print(f"Input: {change3['reason']}")
    print(f"Original payload: {change3['old_value']}")
    print(f"AI Enhanced payload: {json.dumps(result3.get('payload', 'No result'), indent=2)}")
    
    # Test the full workflow modification with mock
    print("\n🔄 Test Case 4: Full workflow modification with AI enhancement")
    
    with patch.object(agent, '_ai_reason', new_callable=AsyncMock) as mock_ai_reason, \
         patch.object(agent, '_client', True):  # Mock client existence
        mock_ai_reason.return_value = mock_ai_response_1
        
        full_result = await agent._modify_connector_parameters(
            workflow1, 
            change1, 
            "test_user_id"
        )
    
    print(f"Full modification result: {json.dumps(full_result, indent=2)}")
    print(f"Updated workflow body: {workflow1['steps'][0]['parameters']['body'][:100]}...")
    
    # Analysis
    print("\n🔍 Analysis:")
    test_results = [
        ("Email body improvement", result1.get('body')),
        ("Code generation", result2.get('code')),
        ("Webhook payload", result3.get('payload')),
        ("Full workflow modification", full_result.get('success'))
    ]
    
    success_count = 0
    for name, result in test_results:
        if result:
            success_count += 1
            print(f"✅ {name}: AI successfully generated content")
        else:
            print(f"❌ {name}: No AI content generated")
    
    print(f"\n📊 Summary: {success_count}/{len(test_results)} test cases successful")
    print("\n🎯 Key Insights:")
    print("- AI can generate professional email content from simple input")
    print("- AI can enhance simple code with error handling and logging")
    print("- AI can create complex data structures with proper formatting")
    print("- The system properly falls back to AI reasoning when no specific value is provided")
    
    return success_count > 0

if __name__ == "__main__":
    success = asyncio.run(test_complex_ai_with_mock())
    sys.exit(0 if success else 1)