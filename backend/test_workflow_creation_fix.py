#!/usr/bin/env python3
"""
Test script to verify the workflow creation fix for True ReAct Agent.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.true_react_agent import TrueReActAgent

async def test_workflow_creation():
    """Test workflow creation for a complex request."""
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test the exact request that was failing
    request = "Build me a workflow that finds the top 5 recent blogs posted by Google using Perplexity, summarizes all 5 into one combined summary, and sends the summarized text to my Gmail (shreyashbarca10@gmail.com) in the email body"
    
    print("Testing workflow creation...")
    print("=" * 80)
    print(f"Request: {request}")
    print("=" * 80)
    
    result = await agent.process_user_request(request, "test_user")
    
    print(f"\nResult:")
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error', 'None')}")
    
    if result['success']:
        workflow = result.get('workflow', {})
        print(f"Workflow ID: {workflow.get('id', 'None')}")
        print(f"Steps: {workflow.get('total_steps', 0)}")
        
        steps = workflow.get('steps', [])
        for i, step in enumerate(steps, 1):
            print(f"  Step {i}: {step.get('connector_name')} - {step.get('purpose')}")
    else:
        print(f"Reasoning trace: {result.get('reasoning_trace', [])}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_workflow_creation())