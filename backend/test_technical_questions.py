#!/usr/bin/env python3
"""
Test the technical question detection and response system.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import get_conversation_handler

async def test_technical_questions():
    """Test technical question detection and responses."""
    
    test_cases = [
        # The original user question that failed
        "but how's extracted content from youtube is processing",
        
        # Other technical questions
        "How does YouTube connector extract content?",
        "What data is the text summarizer processing?",
        "How does data flow from YouTube to text summarizer?",
        "What parameters does Gmail connector use?",
        "How is the YouTube connector working?",
        "What format does the YouTube connector output?",
        "How does the processing work in this workflow?",
        "What data is being stored by the Notion connector?",
        
        # Non-technical questions for comparison
        "Create a new workflow",
        "Hi there",
        "I need help with automation"
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
            print(f"Reasoning: {intent_analysis.reasoning}")
            
            # Test response generation
            if intent_analysis.intent.value == "technical_question":
                response = await conversation_handler.generate_conversational_response(
                    intent_analysis.intent, test_case
                )
                print(f"\nResponse Preview: {response[:200]}...")
                print("✅ SUCCESS: Technical question detected and response generated!")
            else:
                print(f"❌ Not detected as technical question (detected as: {intent_analysis.intent.value})")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_technical_questions())