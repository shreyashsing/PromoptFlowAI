#!/usr/bin/env python3
"""
Debug the True ReAct agent flow.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def debug_true_react_flow():
    """Debug the True ReAct agent flow."""
    
    user_message = "how is youtube extracting data from video and transferring it to text summariser"
    user_id = "test_user"
    
    print(f"Debugging True ReAct flow for: '{user_message}'")
    print("="*80)
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test analyze_user_intent directly
    print("1. TRUE REACT ANALYZE_USER_INTENT:")
    print("-" * 50)
    intent_result = await agent.analyze_user_intent(user_message)
    print(f"Intent: {intent_result['intent']}")
    print(f"Confidence: {intent_result['confidence']}")
    print(f"Reasoning: {intent_result['reasoning']}")
    print(f"Needs Workflow: {intent_result['needs_workflow']}")
    print(f"Extracted Info: {intent_result['extracted_info']}")
    
    # Test with session context (post-execution)
    session_context = {
        "executed_workflow": {"id": "test_workflow"},
        "awaiting_approval": False
    }
    
    print(f"\n2. TRUE REACT WITH SESSION CONTEXT:")
    print("-" * 50)
    intent_result_with_context = await agent.analyze_user_intent(user_message, session_context)
    print(f"Intent: {intent_result_with_context['intent']}")
    print(f"Confidence: {intent_result_with_context['confidence']}")
    print(f"Reasoning: {intent_result_with_context['reasoning']}")
    print(f"Needs Workflow: {intent_result_with_context['needs_workflow']}")
    
    # Summary
    print(f"\n3. SUMMARY:")
    print("-" * 50)
    if intent_result['intent'] == "technical_question":
        print("✅ SUCCESS: True ReAct correctly identifies technical question")
        if not intent_result['needs_workflow']:
            print("✅ CORRECT: Technical questions don't need new workflows")
            print("   They should be handled by intelligent conversation handler")
        else:
            print("❌ ISSUE: Technical questions shouldn't need new workflows")
    else:
        print(f"❌ FAILURE: True ReAct identifies as {intent_result['intent']} instead of technical_question")

if __name__ == "__main__":
    asyncio.run(debug_true_react_flow())