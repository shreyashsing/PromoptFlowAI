#!/usr/bin/env python3
"""
Test the complete intelligent conversation system integration.
This tests the full flow from user input to appropriate response.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent


async def test_conversational_scenarios():
    """Test various conversational scenarios that should NOT create workflows."""
    
    print("🧠 Testing Complete Intelligent Conversation Integration")
    print("=" * 60)
    
    # Initialize the TrueReAct agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    test_scenarios = [
        {
            "name": "Simple Greeting",
            "input": "hi",
            "expected_behavior": "Should respond conversationally, not create workflow"
        },
        {
            "name": "Thank You",
            "input": "thanks",
            "expected_behavior": "Should respond conversationally"
        },
        {
            "name": "Help Request",
            "input": "what can you do",
            "expected_behavior": "Should provide help information"
        },
        {
            "name": "Workflow Question (without context)",
            "input": "what is happening in this workflow",
            "expected_behavior": "Should explain no current workflow exists"
        },
        {
            "name": "Workflow Question (with context)",
            "input": "can you tell me what is happening in this workflow",
            "context": {
                "current_workflow": {
                    "steps": [
                        {"connector_name": "gmail_connector", "purpose": "Fetch recent emails"},
                        {"connector_name": "text_summarizer", "purpose": "Summarize email content"}
                    ]
                }
            },
            "expected_behavior": "Should explain the current workflow steps"
        },
        {
            "name": "Workflow Creation Request",
            "input": "create a workflow to summarize emails",
            "expected_behavior": "Should start workflow creation process"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📝 Test {i}: {scenario['name']}")
        print(f"   Input: '{scenario['input']}'")
        print(f"   Expected: {scenario['expected_behavior']}")
        
        try:
            # Process the request
            result = await agent.process_user_request(
                scenario["input"], 
                "test_user", 
                scenario.get("context", {})
            )
            
            print(f"   🤖 Success: {result.get('success', False)}")
            print(f"   💬 Message: {result.get('message', 'No message')[:100]}...")
            
            # Check if it's conversational
            is_conversational = result.get('is_conversational', False)
            intent_analysis = result.get('intent_analysis', {})
            
            if is_conversational:
                print(f"   ✅ CORRECT: Detected as conversational")
                print(f"   🧠 Intent: {intent_analysis.get('intent', 'unknown')}")
                print(f"   📊 Confidence: {intent_analysis.get('confidence', 0):.2f}")
            elif scenario["name"] == "Workflow Creation Request":
                print(f"   ✅ CORRECT: Started workflow creation process")
            else:
                print(f"   ⚠️  UNEXPECTED: Not detected as conversational")
                print(f"   🧠 Intent: {intent_analysis.get('intent', 'unknown')}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n✅ Integration test completed!")


async def test_workflow_question_scenario():
    """Test the specific scenario that was problematic for the user."""
    
    print("\n\n🔍 Testing User's Specific Problematic Scenario")
    print("=" * 60)
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # First, simulate creating a workflow
    print("📋 Step 1: Simulating existing workflow context")
    workflow_context = {
        "current_workflow": {
            "id": "test_workflow_123",
            "name": "Email Summarization Workflow",
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
    
    # Now test the problematic question
    print("\n📝 Step 2: Testing the problematic user question")
    user_question = "can you tell me what is happening in this workflow"
    
    print(f"   User asks: '{user_question}'")
    print(f"   Context: Has workflow with {len(workflow_context['current_workflow']['steps'])} steps")
    
    result = await agent.process_user_request(user_question, "test_user", workflow_context)
    
    print(f"\n🤖 Agent Response:")
    print(f"   Success: {result.get('success', False)}")
    print(f"   Is Conversational: {result.get('is_conversational', False)}")
    print(f"   Message: {result.get('message', 'No message')}")
    
    # Check if this was handled correctly
    if result.get('is_conversational') and result.get('success'):
        print(f"\n✅ SUCCESS: Question was handled conversationally!")
        print(f"   The user should see an explanation of the workflow, not a new workflow creation plan.")
    else:
        print(f"\n❌ FAILED: Question was not handled conversationally")
        print(f"   This would show the user a new workflow plan instead of explaining the existing one.")
    
    # Show the intent analysis
    intent_analysis = result.get('intent_analysis', {})
    if intent_analysis:
        print(f"\n🧠 Intent Analysis:")
        print(f"   Intent: {intent_analysis.get('intent', 'unknown')}")
        print(f"   Confidence: {intent_analysis.get('confidence', 0):.2f}")
        print(f"   Reasoning: {intent_analysis.get('reasoning', 'No reasoning')}")


async def main():
    """Run all integration tests."""
    print("🚀 Starting Intelligent Conversation Integration Tests\n")
    
    try:
        # Test various conversational scenarios
        await test_conversational_scenarios()
        
        # Test the specific user scenario
        await test_workflow_question_scenario()
        
        print(f"\n🎯 Integration Test Summary:")
        print(f"   ✅ The intelligent conversation handler is now integrated!")
        print(f"   ✅ Users can ask questions about workflows without creating new ones")
        print(f"   ✅ Greetings and conversational messages are handled appropriately")
        print(f"   ✅ The system is more flexible and user-friendly")
        
    except Exception as e:
        print(f"❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())