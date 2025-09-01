#!/usr/bin/env python3
"""
Debug the complete intent analysis flow.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import IntelligentConversationHandler

async def debug_intent_flow():
    """Debug the complete intent analysis flow."""
    
    user_message = "how is youtube extracting data from video and transferring it to text summariser"
    
    print(f"Debugging intent flow for: '{user_message}'")
    print("="*80)
    
    handler = IntelligentConversationHandler()
    await handler.initialize()
    
    # Test rule-based detection directly
    print("1. RULE-BASED DETECTION:")
    print("-" * 40)
    rule_result = handler._rule_based_intent_detection(user_message)
    print(f"Intent: {rule_result.intent.value}")
    print(f"Confidence: {rule_result.confidence}")
    print(f"Reasoning: {rule_result.reasoning}")
    print(f"Extracted Info: {rule_result.extracted_info}")
    
    # Test AI analysis
    print(f"\n2. AI ANALYSIS:")
    print("-" * 40)
    ai_result = await handler._ai_intent_analysis(user_message)
    if ai_result:
        print(f"Intent: {ai_result.intent.value}")
        print(f"Confidence: {ai_result.confidence}")
        print(f"Reasoning: {ai_result.reasoning}")
        print(f"Extracted Info: {ai_result.extracted_info}")
    else:
        print("AI analysis returned None")
    
    # Test synthesis
    print(f"\n3. SYNTHESIS:")
    print("-" * 40)
    final_result = await handler._synthesize_intent_analysis(user_message, None, rule_result, ai_result)
    print(f"Final Intent: {final_result.intent.value}")
    print(f"Final Confidence: {final_result.confidence}")
    print(f"Final Reasoning: {final_result.reasoning}")
    print(f"Final Extracted Info: {final_result.extracted_info}")
    
    # Test full analysis
    print(f"\n4. FULL ANALYSIS:")
    print("-" * 40)
    full_result = await handler.analyze_intent(user_message)
    print(f"Full Intent: {full_result.intent.value}")
    print(f"Full Confidence: {full_result.confidence}")
    print(f"Full Reasoning: {full_result.reasoning}")
    
    # Summary
    print(f"\n5. SUMMARY:")
    print("-" * 40)
    if full_result.intent.value == "technical_question":
        print("✅ SUCCESS: Correctly identified as technical question")
    else:
        print(f"❌ FAILURE: Identified as {full_result.intent.value} instead of technical_question")
        
        # Debug where it went wrong
        if rule_result.intent.value == "technical_question":
            print("   - Rule-based detection worked correctly")
            if ai_result and ai_result.intent.value != "technical_question":
                print(f"   - AI analysis overrode with {ai_result.intent.value}")
            else:
                print("   - Issue in synthesis logic")
        else:
            print(f"   - Rule-based detection failed: {rule_result.intent.value}")

if __name__ == "__main__":
    asyncio.run(debug_intent_flow())