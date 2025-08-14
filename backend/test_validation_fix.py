#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_validation_fix():
    """Test that the validation fix allows clear workflow requests to proceed."""
    
    print("🧪 Testing Validation Fix")
    print("=" * 50)
    
    # Initialize the agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test the specific user request that was failing
    test_message = "find top 5 blogs posted on ai agents and send it to shreyashbarca10@gmail.com"
    
    print(f"📝 Testing message: '{test_message}'")
    print()
    
    # Process the request
    test_user_id = "test-user-123"
    result = await agent.process_user_request(test_message, test_user_id)
    
    print(f"🎯 Success: {result.get('success', False)}")
    print(f"🎯 Phase: {result.get('phase', 'unknown')}")
    print(f"🎯 Is Conversational: {result.get('is_conversational', False)}")
    print(f"🎯 Needs Clarification: {result.get('needs_clarification', False)}")
    
    if result.get('message'):
        print(f"🎯 Message: {result['message'][:200]}...")
    
    print()
    
    # Check if it proceeds to workflow creation instead of asking for clarification
    if result.get('phase') == 'conversational' and result.get('needs_clarification'):
        print("❌ FAILED: Still asking for clarification despite clear request")
        print("❌ The validation fix needs more work")
    elif result.get('phase') == 'planning' or result.get('success'):
        print("✅ SUCCESS: Proceeding with workflow creation")
        print("✅ The validation fix is working!")
    else:
        print(f"🤔 UNCLEAR: Got phase '{result.get('phase')}' - need to investigate")
    
    print()
    print("🧪 Testing additional similar requests...")
    
    # Test more similar requests
    test_cases = [
        "search for top 10 AI articles and email them to user@example.com",
        "find latest blog posts about machine learning and send to test@gmail.com",
        "get 5 best articles on automation and email to admin@company.com"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case}")
        result = await agent.process_user_request(test_case, test_user_id)
        
        if result.get('needs_clarification'):
            status = "❌"
            outcome = "asking for clarification"
        elif result.get('phase') == 'planning' or result.get('success'):
            status = "✅"
            outcome = "proceeding with workflow"
        else:
            status = "🤔"
            outcome = f"phase: {result.get('phase')}"
        
        print(f"  {status} {outcome}")
        print()

if __name__ == "__main__":
    asyncio.run(test_validation_fix())