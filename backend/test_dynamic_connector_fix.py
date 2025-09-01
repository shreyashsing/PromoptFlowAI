#!/usr/bin/env python3
"""
Test the dynamic connector info fix.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import get_conversation_handler

async def test_dynamic_connector_fix():
    """Test the dynamic connector info system."""
    
    test_cases = [
        "How does the YouTube connector extract video content?",
        "What data format does Gmail connector output?",
        "How does data flow from YouTube to text summarizer?"
    ]
    
    conversation_handler = await get_conversation_handler()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test_case}")
        print('='*60)
        
        try:
            # Test intent analysis
            intent_analysis = await conversation_handler.analyze_intent(test_case)
            
            print(f"Intent: {intent_analysis.intent.value}")
            print(f"Confidence: {intent_analysis.confidence}")
            
            # Test response generation
            if intent_analysis.intent.value == "technical_question":
                response = await conversation_handler.generate_conversational_response(
                    intent_analysis.intent, test_case
                )
                print(f"\nResponse Preview: {response[:300]}...")
                
                if "I'd be happy to explain" in response:
                    print("❌ STILL FAILING: Getting fallback response instead of dynamic explanation")
                else:
                    print("✅ SUCCESS: Dynamic explanation generated!")
            else:
                print(f"❌ Not detected as technical question")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_dynamic_connector_fix())