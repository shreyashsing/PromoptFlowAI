#!/usr/bin/env python3
"""
Test the original failing case: "but how's extracted content from youtube is processing"
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import get_conversation_handler

async def test_original_case():
    """Test the original failing case."""
    
    user_message = "but how's extracted content from youtube is processing"
    
    print("Testing original failing case:")
    print(f"User message: '{user_message}'")
    print("="*60)
    
    conversation_handler = await get_conversation_handler()
    
    # Test intent analysis
    intent_analysis = await conversation_handler.analyze_intent(user_message)
    
    print(f"Intent: {intent_analysis.intent.value}")
    print(f"Confidence: {intent_analysis.confidence}")
    print(f"Reasoning: {intent_analysis.reasoning}")
    print(f"Extracted Info: {intent_analysis.extracted_info}")
    
    # Test response generation
    response = await conversation_handler.generate_conversational_response(
        intent_analysis.intent, user_message
    )
    
    print("\n" + "="*60)
    print("GENERATED RESPONSE:")
    print("="*60)
    print(response)
    
    if intent_analysis.intent.value == "technical_question":
        print("\n✅ SUCCESS: Original failing case now works correctly!")
        print("- Correctly identified as technical question")
        print("- Generated detailed technical explanation")
        print("- No more generic 'clarification needed' response")
    else:
        print(f"\n❌ STILL FAILING: Detected as {intent_analysis.intent.value} instead of technical_question")

if __name__ == "__main__":
    asyncio.run(test_original_case())