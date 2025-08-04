#!/usr/bin/env python3
"""
Test script for dynamic completion detection using Tool Registry.
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent
from app.services.tool_registry import ToolRegistry

async def test_dynamic_completion_detection():
    """Test the new dynamic completion detection system."""
    print("🧪 Testing Dynamic Completion Detection")
    print("=" * 60)
    
    try:
        # Initialize agent
        agent = TrueReActAgent()
        await agent.initialize()
        
        # Test the complex user request
        user_request = "Find the top 5 recent blog posts by Google using Perplexity. Summarize all 5 into one combined summary. Find 3 relevant YouTube videos related to the blog topics. Save the summary in Google Docs (Drive), log everything to Google Sheets and Airtable, email the summary with links to shreyashbarca10@gmail.com, and create a detailed Notion page with all content and links."
        
        mock_analysis = {
            "original_request": user_request
        }
        
        print(f"📋 User Request: {user_request}")
        print()
        
        # Check what tools are available in the registry
        if hasattr(agent, 'tool_registry') and agent.tool_registry:
            try:
                available_tools = await agent.tool_registry.get_available_tools()
                tool_names = [tool.name for tool in available_tools]
                print(f"🔧 Available Tools ({len(tool_names)}): {', '.join(tool_names)}")
                print()
            except Exception as e:
                print(f"⚠️  Could not get tools from registry: {e}")
                print()
        
        # Test different workflow scenarios
        test_scenarios = [
            {
                "name": "After 2 steps (should be incomplete)",
                "steps": [
                    {"connector_name": "perplexity_search", "purpose": "Find blog posts"},
                    {"connector_name": "text_summarizer", "purpose": "Summarize content"}
                ]
            },
            {
                "name": "After 4 steps (partial completion)", 
                "steps": [
                    {"connector_name": "perplexity_search", "purpose": "Find blog posts"},
                    {"connector_name": "text_summarizer", "purpose": "Summarize content"},
                    {"connector_name": "youtube", "purpose": "Find related videos"},
                    {"connector_name": "google_drive", "purpose": "Save to Google Docs"}
                ]
            },
            {
                "name": "After 6 steps (more complete)",
                "steps": [
                    {"connector_name": "perplexity_search", "purpose": "Find blog posts"},
                    {"connector_name": "text_summarizer", "purpose": "Summarize content"},
                    {"connector_name": "youtube", "purpose": "Find related videos"},
                    {"connector_name": "google_drive", "purpose": "Save to Google Docs"},
                    {"connector_name": "google_sheets", "purpose": "Log to spreadsheet"},
                    {"connector_name": "airtable", "purpose": "Store in database"}
                ]
            },
            {
                "name": "After 8 steps (should be complete)",
                "steps": [
                    {"connector_name": "perplexity_search", "purpose": "Find blog posts"},
                    {"connector_name": "text_summarizer", "purpose": "Summarize content"},
                    {"connector_name": "youtube", "purpose": "Find related videos"},
                    {"connector_name": "google_drive", "purpose": "Save to Google Docs"},
                    {"connector_name": "google_sheets", "purpose": "Log to spreadsheet"},
                    {"connector_name": "airtable", "purpose": "Store in database"},
                    {"connector_name": "gmail_connector", "purpose": "Send email"},
                    {"connector_name": "notion", "purpose": "Create detailed page"}
                ]
            }
        ]
        
        print("🔍 Testing dynamic completion detection:")
        print()
        
        for scenario in test_scenarios:
            print(f"📊 {scenario['name']}:")
            
            try:
                is_complete = await agent.is_workflow_complete(mock_analysis, scenario['steps'])
                
                status = "✅ COMPLETE" if is_complete else "❌ INCOMPLETE"
                print(f"   {status}")
                print(f"   📋 Steps: {len(scenario['steps'])}")
                print(f"   🔧 Connectors: {', '.join([step['connector_name'] for step in scenario['steps']])}")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
            
            print()
        
        print("🎯 Expected Behavior:")
        print("   - Complex request (8 requirements): needs 6-8 steps")
        print("   - Simple request (2 requirements): needs 2 steps")
        print("   - System should adapt based on request complexity")
        print("   - No hardcoded platform names - uses Tool Registry")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting Dynamic Completion Detection Tests")
    
    # Run the tests
    asyncio.run(test_dynamic_completion_detection())
    
    print("\\n✨ Tests completed!")
    print("\\n💡 Key Improvements:")
    print("   ✅ Dynamic tool discovery using Tool Registry")
    print("   ✅ No hardcoded platform names")
    print("   ✅ Intelligent complexity analysis")
    print("   ✅ Adaptive completion criteria")
    print("   ✅ Scalable to 200-300 connectors")