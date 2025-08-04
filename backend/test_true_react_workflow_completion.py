#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent
from app.services.tool_registry import ToolRegistry

async def test_workflow_completion():
    """Test that the True ReAct agent creates all required steps for a complex request."""
    
    # Initialize the agent
    tool_registry = ToolRegistry()
    await tool_registry.initialize()
    
    agent = TrueReActAgent(tool_registry)
    await agent.initialize()
    
    # Test request that should require 5 steps
    request = "Find the top 5 recent blogs posted by Google using Perplexity. Summarize them into one combined summary. Store the summary in Google Drive as a Google Doc, log the metadata to Google Sheets, and send the summarized text to my Gmail (shreyashbarca10@gmail.com) in the email body, including a link to the Google Doc"
    
    print(f"🧪 Testing request: {request}")
    print("=" * 80)
    
    try:
        result = await agent.process_user_request(request, "test_session")
        
        if result.get('success'):
            workflow = result.get('workflow', {})
            steps = workflow.get('steps', [])
            
            print(f"✅ Workflow created successfully!")
            print(f"📊 Total steps: {len(steps)}")
            print("\n🔄 Workflow steps:")
            
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step['connector_name']}: {step.get('purpose', 'No purpose')}")
            
            # Check if all expected connectors are present
            expected_connectors = ['perplexity_search', 'text_summarizer', 'google_drive', 'google_sheets', 'gmail_connector']
            actual_connectors = [step['connector_name'] for step in steps]
            
            print(f"\n🎯 Expected connectors: {expected_connectors}")
            print(f"🎯 Actual connectors: {actual_connectors}")
            
            missing = set(expected_connectors) - set(actual_connectors)
            if missing:
                print(f"❌ Missing connectors: {missing}")
                return False
            else:
                print("✅ All expected connectors are present!")
                return True
                
        else:
            print(f"❌ Workflow creation failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_workflow_completion())
    if success:
        print("\n🎉 Test PASSED - All expected connectors were created!")
        sys.exit(0)
    else:
        print("\n💥 Test FAILED - Missing expected connectors!")
        sys.exit(1)