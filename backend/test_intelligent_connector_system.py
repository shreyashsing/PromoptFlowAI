#!/usr/bin/env python3
"""
Test the intelligent connector explanation system.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import get_conversation_handler

async def test_intelligent_system():
    """Test the intelligent connector system with various questions."""
    
    test_cases = [
        # Original failing case
        "How does the YouTube connector extract video content?",
        
        # Different types of technical questions
        "What data format does Gmail connector output?",
        "How does data flow from YouTube to text summarizer?",
        "What parameters does the Notion connector use?",
        "How does the Perplexity connector process search queries?",
        
        # Questions about connectors that might not exist yet
        "How does the Slack connector handle message processing?",
        "What authentication does the Salesforce connector use?",
        
        # Complex workflow questions
        "How do connectors communicate with each other in a workflow?",
        "What happens when a connector fails in the middle of processing?"
    ]
    
    conversation_handler = await get_conversation_handler()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}: {test_case}")
        print('='*80)
        
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
                
                print(f"\nResponse Preview:")
                print("-" * 50)
                print(response[:400] + "..." if len(response) > 400 else response)
                print("-" * 50)
                
                # Check quality of response
                if "I'd be happy to explain" in response:
                    print("❌ ISSUE: Still getting generic fallback")
                elif len(response) < 100:
                    print("❌ ISSUE: Response too short, lacks detail")
                elif "technical" in response.lower() and ("api" in response.lower() or "data" in response.lower()):
                    print("✅ SUCCESS: Detailed technical explanation generated!")
                else:
                    print("⚠️  PARTIAL: Response generated but quality unclear")
            else:
                print(f"❌ Not detected as technical question (got: {intent_analysis.intent.value})")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_intelligent_system())