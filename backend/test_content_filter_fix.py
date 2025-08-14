#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import IntelligentConversationHandler, ConversationIntent

async def test_content_filter_fix():
    """Test that the content filter fix works for the specific user request."""
    
    print("🧪 Testing Content Filter Fix")
    print("=" * 50)
    
    # Initialize the handler
    handler = IntelligentConversationHandler()
    await handler.initialize()
    
    # Test the specific user request that was failing
    test_message = "find top 5 blogs posted on ai agents and send it to shreyashbarca10@gmail.com"
    
    print(f"📝 Testing message: '{test_message}'")
    print()
    
    # Analyze intent
    result = await handler.analyze_intent(test_message)
    
    print(f"🎯 Intent: {result.intent.value}")
    print(f"🎯 Confidence: {result.confidence}")
    print(f"🎯 Reasoning: {result.reasoning}")
    print(f"🎯 Extracted Info: {result.extracted_info}")
    print()
    
    # Check if it correctly identifies as workflow creation
    if result.intent == ConversationIntent.WORKFLOW_CREATION:
        print("✅ SUCCESS: Correctly identified as WORKFLOW_CREATION")
        print("✅ The content filter fix is working!")
    else:
        print(f"❌ FAILED: Expected WORKFLOW_CREATION, got {result.intent.value}")
        print("❌ The fix needs more work")
    
    print()
    print("🧪 Testing additional similar requests...")
    
    # Test more similar requests
    test_cases = [
        "search for top 10 AI articles and email them to user@example.com",
        "find latest blog posts about machine learning and send to test@gmail.com",
        "get 5 best articles on automation and email to admin@company.com",
        "collect recent posts about AI and send them to my email address"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case}")
        result = await handler.analyze_intent(test_case)
        status = "✅" if result.intent == ConversationIntent.WORKFLOW_CREATION else "❌"
        print(f"  {status} {result.intent.value} (confidence: {result.confidence})")
        print()

if __name__ == "__main__":
    asyncio.run(test_content_filter_fix())