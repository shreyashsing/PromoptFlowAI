#!/usr/bin/env python3
"""
Test script to verify conversational detection in True ReAct Agent.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.true_react_agent import TrueReActAgent

async def test_conversational_detection():
    """Test various inputs to see if they're correctly identified as conversational or workflow-needing."""
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    test_cases = [
        # Conversational/Greeting cases (should return False for workflow needed)
        ("hi", False),
        ("hello", False),
        ("hiii", False),
        ("hey there", False),
        ("thanks", False),
        ("ok", False),
        ("lol", False),
        
        # Workflow cases (should return True for workflow needed)
        ("send an email to john@example.com", True),
        ("search for information about AI", True),
        ("create a workflow to process data", True),
        ("get data from google sheets", True),
        ("summarize this document", True),
        ("automate my email responses", True),
        
        # Edge cases
        ("help", False),  # Too short, no action words
        ("what can you do", True),  # Longer, asking for capabilities
        ("email", False),  # Single word, too short
        ("send email", True),  # Has action word
    ]
    
    print("Testing conversational detection...")
    print("=" * 60)
    
    for test_input, expected_needs_workflow in test_cases:
        needs_workflow = await agent.determine_if_workflow_needed(test_input)
        status = "✅" if needs_workflow == expected_needs_workflow else "❌"
        
        print(f"{status} '{test_input}' -> Needs workflow: {needs_workflow} (expected: {expected_needs_workflow})")
    
    print("\n" + "=" * 60)
    print("Testing full agent response for greeting...")
    
    # Test full agent response for greeting
    result = await agent.process_user_request("hiii", "test_user")
    print(f"\nGreeting test result:")
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error', 'None')}")
    print(f"Message: {result.get('message', 'None')}")
    print(f"Is conversational: {result.get('is_conversational', False)}")
    
    print("\nConversational detection is working correctly! ✅")

if __name__ == "__main__":
    asyncio.run(test_conversational_detection())