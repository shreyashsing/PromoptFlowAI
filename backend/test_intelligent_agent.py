#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent
from app.services.tool_registry import ToolRegistry

async def test_intelligent_workflow_creation():
    """Test that the agent can handle complex requests without hardcoded patterns."""
    
    # Initialize the agent
    tool_registry = ToolRegistry()
    await tool_registry.initialize()
    
    agent = TrueReActAgent(tool_registry)
    await agent.initialize()
    
    # Test various complex requests to ensure no hardcoding
    test_requests = [
        {
            "name": "Complex Google Blog Analysis",
            "request": "Find the top 5 recent blogs posted by Google using Perplexity. Summarize them into one combined summary. Store the summary in Google Drive as a Google Doc, log the metadata to Google Sheets, and send the summarized text to my Gmail (shreyashbarca10@gmail.com) in the email body, including a link to the Google Doc",
            "expected_min_steps": 5,
            "expected_connectors": ["perplexity_search", "text_summarizer", "google_drive", "google_sheets", "gmail_connector"]
        },
        {
            "name": "Data Processing Pipeline",
            "request": "Search for recent AI research papers, summarize the key findings, and create a comprehensive report in Google Drive",
            "expected_min_steps": 3,
            "expected_connectors": ["perplexity_search", "text_summarizer", "google_drive"]
        },
        {
            "name": "Communication Workflow",
            "request": "Find information about the latest tech trends and email a summary to my team",
            "expected_min_steps": 2,
            "expected_connectors": ["perplexity_search", "gmail_connector"]
        }
    ]
    
    print("🧪 Testing Intelligent Agent (No Hardcoded Patterns)")
    print("=" * 60)
    
    all_passed = True
    
    for test_case in test_requests:
        print(f"\n📋 Test: {test_case['name']}")
        print(f"Request: {test_case['request']}")
        print("-" * 40)
        
        try:
            result = await agent.process_user_request(test_case['request'], f"test_{test_case['name'].lower().replace(' ', '_')}")
            
            if result.get('success'):
                workflow = result.get('workflow', {})
                steps = workflow.get('steps', [])
                actual_connectors = [step['connector_name'] for step in steps]
                
                print(f"✅ Workflow created with {len(steps)} steps")
                for i, step in enumerate(steps, 1):
                    print(f"  {i}. {step['connector_name']}: {step.get('purpose', 'No purpose')}")
                
                # Check minimum steps
                if len(steps) >= test_case['expected_min_steps']:
                    print(f"✅ Minimum steps requirement met ({len(steps)} >= {test_case['expected_min_steps']})")
                else:
                    print(f"❌ Insufficient steps ({len(steps)} < {test_case['expected_min_steps']})")
                    all_passed = False
                
                # Check for expected connectors (flexible - not all required)
                found_connectors = set(actual_connectors) & set(test_case['expected_connectors'])
                if len(found_connectors) >= len(test_case['expected_connectors']) * 0.6:  # At least 60% match
                    print(f"✅ Good connector selection: {list(found_connectors)}")
                else:
                    print(f"⚠️  Unexpected connector selection: {actual_connectors}")
                    print(f"   Expected some of: {test_case['expected_connectors']}")
                
            else:
                print(f"❌ Workflow creation failed: {result.get('error', 'Unknown error')}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Agent is working intelligently!")
        return True
    else:
        print("💥 SOME TESTS FAILED - Agent needs improvement")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_intelligent_workflow_creation())
    sys.exit(0 if success else 1)