#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import IntelligentConversationHandler

async def test_various_cases():
    """Test various edge cases to ensure the fix is robust."""
    
    handler = IntelligentConversationHandler()
    await handler.initialize()
    
    test_cases = [
        {
            "message": "Create a template for customer support responses about product features",
            "expected": "workflow_creation",
            "description": "Simple template creation request"
        },
        {
            "message": "Generate automated responses for customer inquiries about skincare products",
            "expected": "workflow_creation", 
            "description": "Automated response generation"
        },
        {
            "message": "Build a system to automate customer service replies",
            "expected": "workflow_creation",
            "description": "Customer service automation"
        },
        {
            "message": "How does the Gmail connector process email content?",
            "expected": "technical_question",
            "description": "Technical question about connector processing"
        },
        {
            "message": "What data is extracted from YouTube videos by the connector?",
            "expected": "technical_question", 
            "description": "Technical question about data extraction"
        },
        {
            "message": "I want to create a workflow that sends emails",
            "expected": "workflow_creation",
            "description": "Basic workflow creation"
        },
        {
            "message": "What content does the text summarizer use?",
            "expected": "technical_question",
            "description": "Technical question about content processing"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test {i}: {case['description']}")
        print(f"Message: {case['message']}")
        
        result = await handler.analyze_intent(case['message'])
        
        print(f"Expected: {case['expected']}")
        print(f"Actual: {result.intent.value}")
        print(f"Confidence: {result.confidence}")
        
        success = result.intent.value == case['expected']
        results.append(success)
        
        if success:
            print("✅ PASS")
        else:
            print("❌ FAIL")
        
        print("-" * 50)
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"❌ {total - passed} tests failed")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(test_various_cases())