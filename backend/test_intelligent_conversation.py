#!/usr/bin/env python3
"""
Test the intelligent conversation handler to ensure it properly detects
different types of user intents and provides appropriate responses.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.intelligent_conversation_handler import (
    IntelligentConversationHandler, 
    ConversationIntent,
    get_conversation_handler
)


async def test_intent_detection():
    """Test various user messages to see if intents are detected correctly."""
    
    print("🧠 Testing Intelligent Conversation Handler")
    print("=" * 50)
    
    handler = await get_conversation_handler()
    
    # Test cases with expected intents
    test_cases = [
        # Greetings
        ("hi", ConversationIntent.GREETING),
        ("hello", ConversationIntent.GREETING),
        ("good morning", ConversationIntent.GREETING),
        
        # Conversational
        ("thanks", ConversationIntent.CONVERSATIONAL),
        ("ok", ConversationIntent.CONVERSATIONAL),
        ("cool", ConversationIntent.CONVERSATIONAL),
        
        # Help requests
        ("help", ConversationIntent.HELP_REQUEST),
        ("what can you do", ConversationIntent.HELP_REQUEST),
        ("how to use this", ConversationIntent.HELP_REQUEST),
        
        # Workflow creation
        ("create a workflow to summarize emails", ConversationIntent.WORKFLOW_CREATION),
        ("build an automation for gmail", ConversationIntent.WORKFLOW_CREATION),
        ("I want to automate my spreadsheet updates", ConversationIntent.WORKFLOW_CREATION),
        ("send an email with search results", ConversationIntent.WORKFLOW_CREATION),
        
        # Workflow questions (with context)
        ("what is happening in this workflow", ConversationIntent.WORKFLOW_QUESTION),
        ("can you explain the steps", ConversationIntent.WORKFLOW_QUESTION),
        ("how does this work", ConversationIntent.WORKFLOW_QUESTION),
        
        # Approval responses (with context)
        ("approve", ConversationIntent.APPROVAL_RESPONSE),
        ("looks good", ConversationIntent.APPROVAL_RESPONSE),
        ("proceed", ConversationIntent.APPROVAL_RESPONSE),
        
        # Workflow modifications
        ("change the first step to use gmail", ConversationIntent.WORKFLOW_MODIFICATION),
        ("modify the email connector", ConversationIntent.WORKFLOW_MODIFICATION),
        ("use sheets instead", ConversationIntent.WORKFLOW_MODIFICATION),
    ]
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for message, expected_intent in test_cases:
        print(f"\n📝 Testing: '{message}'")
        
        # Create appropriate context for certain intents
        context = {}
        if expected_intent == ConversationIntent.WORKFLOW_QUESTION:
            context["current_workflow"] = {
                "steps": [{"connector_name": "gmail", "purpose": "Fetch emails"}]
            }
        elif expected_intent == ConversationIntent.APPROVAL_RESPONSE:
            context["awaiting_approval"] = True
        elif expected_intent == ConversationIntent.WORKFLOW_MODIFICATION:
            context["current_workflow"] = {
                "steps": [{"connector_name": "perplexity", "purpose": "Search"}]
            }
        
        analysis = await handler.analyze_intent(message, context)
        
        print(f"   🎯 Expected: {expected_intent.value}")
        print(f"   🤖 Detected: {analysis.intent.value}")
        print(f"   📊 Confidence: {analysis.confidence:.2f}")
        print(f"   💭 Reasoning: {analysis.reasoning}")
        
        if analysis.intent == expected_intent:
            print("   ✅ CORRECT")
            correct_predictions += 1
        else:
            print("   ❌ INCORRECT")
    
    print(f"\n📊 Results: {correct_predictions}/{total_tests} correct ({correct_predictions/total_tests*100:.1f}%)")
    
    return correct_predictions / total_tests


async def test_conversational_responses():
    """Test that appropriate conversational responses are generated."""
    
    print("\n\n💬 Testing Conversational Response Generation")
    print("=" * 50)
    
    handler = await get_conversation_handler()
    
    test_messages = [
        ("hi", ConversationIntent.GREETING),
        ("thanks", ConversationIntent.CONVERSATIONAL),
        ("help", ConversationIntent.HELP_REQUEST),
        ("what is happening in this workflow", ConversationIntent.WORKFLOW_QUESTION),
    ]
    
    for message, intent in test_messages:
        print(f"\n📝 Message: '{message}' (Intent: {intent.value})")
        
        # Create context for workflow questions
        context = {}
        if intent == ConversationIntent.WORKFLOW_QUESTION:
            context["current_workflow"] = {
                "steps": [
                    {"connector_name": "gmail_connector", "purpose": "Fetch recent emails"},
                    {"connector_name": "text_summarizer", "purpose": "Summarize email content"}
                ]
            }
        
        response = await handler.generate_conversational_response(intent, message, context)
        print(f"🤖 Response: {response}")


async def test_workflow_question_scenario():
    """Test the specific scenario from the user's complaint."""
    
    print("\n\n🔍 Testing User's Specific Scenario")
    print("=" * 50)
    
    handler = await get_conversation_handler()
    
    # Simulate the user's scenario
    context = {
        "current_workflow": {
            "steps": [
                {"connector_name": "gmail_connector", "purpose": "Fetch the most recent email from inbox"},
                {"connector_name": "text_summarizer", "purpose": "Summarize the email content"}
            ]
        }
    }
    
    user_message = "can you tell me what is happening in this workflow"
    
    print(f"📝 User message: '{user_message}'")
    print(f"📋 Context: Has current workflow with {len(context['current_workflow']['steps'])} steps")
    
    analysis = await handler.analyze_intent(user_message, context)
    
    print(f"\n🧠 Intent Analysis:")
    print(f"   Intent: {analysis.intent.value}")
    print(f"   Confidence: {analysis.confidence:.2f}")
    print(f"   Reasoning: {analysis.reasoning}")
    
    if analysis.intent == ConversationIntent.WORKFLOW_QUESTION:
        response = await handler.generate_conversational_response(
            analysis.intent, user_message, context
        )
        print(f"\n💬 Generated Response:")
        print(response)
        print("\n✅ SUCCESS: This should be a conversational response, not a new workflow plan!")
    else:
        print(f"\n❌ FAILED: Expected WORKFLOW_QUESTION but got {analysis.intent.value}")


async def main():
    """Run all tests."""
    print("🚀 Starting Intelligent Conversation Handler Tests\n")
    
    try:
        # Test intent detection accuracy
        accuracy = await test_intent_detection()
        
        # Test conversational responses
        await test_conversational_responses()
        
        # Test the specific user scenario
        await test_workflow_question_scenario()
        
        print(f"\n🎯 Overall Test Summary:")
        print(f"   Intent Detection Accuracy: {accuracy*100:.1f}%")
        
        if accuracy > 0.8:
            print("   ✅ Intent detection is working well!")
        else:
            print("   ⚠️ Intent detection needs improvement")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())