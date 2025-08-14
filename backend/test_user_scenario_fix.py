#!/usr/bin/env python3
"""
Test the specific user scenario that was problematic:
"can you tell me what is happening in this workflow"
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent


async def test_user_scenario():
    """Test the exact scenario the user reported as problematic."""
    
    print("🔍 Testing User's Specific Scenario Fix")
    print("=" * 50)
    
    # Initialize the agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Simulate the user's scenario - they have an existing workflow and ask about it
    print("📋 Scenario: User has created an email summarization workflow")
    print("📝 User asks: 'can you tell me what is happening in this workflow'")
    print("🎯 Expected: Should explain the workflow, NOT create a new one")
    
    # Create session context with an executed workflow (like after user created one)
    session_context = {
        "executed_workflow": {
            "id": "workflow_123",
            "name": "Email Summarization",
            "steps": [
                {
                    "connector_name": "gmail_connector",
                    "purpose": "Fetch the most recent email from inbox",
                    "parameters": {"query": "in:inbox", "max_results": 1}
                },
                {
                    "connector_name": "text_summarizer",
                    "purpose": "Summarize the email content", 
                    "parameters": {"max_length": 100}
                }
            ]
        }
    }
    
    user_question = "can you tell me what is happening in this workflow"
    
    print(f"\n🤖 Processing user question...")
    
    try:
        result = await agent.process_user_request(user_question, "test_user", session_context)
        
        print(f"\n📊 Results:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Is Conversational: {result.get('is_conversational', False)}")
        print(f"   Error: {result.get('error', 'None')}")
        
        if result.get('success') and result.get('is_conversational'):
            print(f"\n✅ SUCCESS! The question was handled conversationally.")
            print(f"\n💬 Agent Response:")
            print(f"   {result.get('message', 'No message')}")
            
            # Check if it explains the workflow instead of creating a new one
            message = result.get('message', '')
            if 'Step 1:' in message and 'Step 2:' in message:
                print(f"\n🎉 PERFECT! The agent explained the existing workflow steps.")
            else:
                print(f"\n⚠️  The response doesn't seem to explain the workflow steps.")
                
        elif result.get('success') and not result.get('is_conversational'):
            print(f"\n❌ FAILED: The question was treated as workflow creation.")
            print(f"   This would show the user a new workflow plan instead of explaining the existing one.")
            
        else:
            print(f"\n❌ FAILED: The request failed with error: {result.get('error', 'Unknown')}")
            
        # Show intent analysis if available
        intent_analysis = result.get('intent_analysis', {})
        if intent_analysis:
            print(f"\n🧠 Intent Analysis:")
            print(f"   Intent: {intent_analysis.get('intent', 'unknown')}")
            print(f"   Confidence: {intent_analysis.get('confidence', 0):.2f}")
            print(f"   Reasoning: {intent_analysis.get('reasoning', 'No reasoning')}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run the user scenario test."""
    print("🚀 Testing User Scenario Fix\n")
    
    await test_user_scenario()
    
    print(f"\n🎯 Summary:")
    print(f"   The intelligent conversation handler should now properly detect")
    print(f"   when users are asking about existing workflows and provide")
    print(f"   explanatory responses instead of creating new workflows.")


if __name__ == "__main__":
    asyncio.run(main())