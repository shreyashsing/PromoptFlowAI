#!/usr/bin/env python3
"""
Simple test for technical question handling.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import get_conversation_handler

async def test_simple_technical_question():
    """Test a simple technical question."""
    
    user_message = "How does the YouTube connector extract video content?"
    
    print(f"Testing: {user_message}")
    print("="*60)
    
    try:
        conversation_handler = await get_conversation_handler()
        
        # Test intent analysis
        intent_analysis = await conversation_handler.analyze_intent(user_message)
        
        print(f"Intent: {intent_analysis.intent.value}")
        print(f"Confidence: {intent_analysis.confidence}")
        print(f"Reasoning: {intent_analysis.reasoning}")
        
        # Test response generation
        response = await conversation_handler.generate_conversational_response(
            intent_analysis.intent, user_message
        )
        
        print(f"\nResponse:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        # Check if it's working
        if intent_analysis.intent.value == "technical_question":
            if "I'd be happy to explain the technical details" in response:
                print("\n❌ ISSUE: Still getting generic fallback response")
                print("The dynamic connector system needs debugging")
            else:
                print("\n✅ SUCCESS: Dynamic technical explanation generated!")
        else:
            print(f"\n❌ ISSUE: Not detected as technical question (got: {intent_analysis.intent.value})")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_technical_question())