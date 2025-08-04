#!/usr/bin/env python3
"""
Test script for requirement detection in completion analysis.
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.true_react_agent import TrueReActAgent

async def test_requirement_detection():
    """Test the new requirement detection system."""
    print("🧪 Testing Requirement Detection")
    print("=" * 50)
    
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
        
        # Test the 7-step scenario (missing Notion)
        seven_steps = [
            {"connector_name": "perplexity_search", "purpose": "Find blog posts"},
            {"connector_name": "text_summarizer", "purpose": "Summarize content"},
            {"connector_name": "youtube", "purpose": "Find related videos"},
            {"connector_name": "google_drive", "purpose": "Save to Google Docs"},
            {"connector_name": "google_sheets", "purpose": "Log to spreadsheet"},
            {"connector_name": "airtable", "purpose": "Store in database"},
            {"connector_name": "gmail_connector", "purpose": "Send email"}
        ]
        
        # Test the 8-step scenario (complete)
        eight_steps = seven_steps + [
            {"connector_name": "notion", "purpose": "Create detailed page"}
        ]
        
        print("🔍 Testing requirement detection:")
        print()
        
        # Test 7 steps (should be INCOMPLETE)
        print("📊 7 steps (missing Notion):")
        try:
            is_complete = await agent.is_workflow_complete(mock_analysis, seven_steps)
            status = "✅ COMPLETE" if is_complete else "❌ INCOMPLETE"
            print(f"   {status}")
            print(f"   📋 Steps: {len(seven_steps)}")
            print(f"   🔧 Connectors: {', '.join([step['connector_name'] for step in seven_steps])}")
            print(f"   🎯 Expected: INCOMPLETE (missing notion)")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        print()
        
        # Test 8 steps (should be COMPLETE)
        print("📊 8 steps (complete):")
        try:
            is_complete = await agent.is_workflow_complete(mock_analysis, eight_steps)
            status = "✅ COMPLETE" if is_complete else "❌ INCOMPLETE"
            print(f"   {status}")
            print(f"   📋 Steps: {len(eight_steps)}")
            print(f"   🔧 Connectors: {', '.join([step['connector_name'] for step in eight_steps])}")
            print(f"   🎯 Expected: COMPLETE (all requirements satisfied)")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        print()
        
        # Manual requirement parsing test
        print("🔍 Manual Requirement Parsing Test:")
        request_lower = user_request.lower()
        
        platform_requirements = {
            'perplexity': 'perplexity_search',
            'youtube': 'youtube', 
            'google docs': 'google_drive',
            'drive': 'google_drive',
            'google sheets': 'google_sheets',
            'sheets': 'google_sheets',
            'airtable': 'airtable',
            'email': 'gmail_connector',
            'gmail': 'gmail_connector',
            'notion': 'notion'
        }
        
        explicit_requirements = []
        for platform, connector in platform_requirements.items():
            if platform in request_lower:
                explicit_requirements.append(f"{connector} (for {platform})")
        
        print(f"📋 Detected Requirements ({len(explicit_requirements)}):")
        for req in explicit_requirements:
            print(f"   - {req}")
        
        print()
        
        # Check satisfaction for 7 steps
        completed_connectors_7 = [step['connector_name'] for step in seven_steps]
        satisfied_7 = []
        missing_7 = []
        
        for req in explicit_requirements:
            connector_name = req.split(' (')[0]
            if connector_name in completed_connectors_7:
                satisfied_7.append(req)
            else:
                missing_7.append(req)
        
        print(f"📊 7-Step Analysis:")
        print(f"   Satisfied ({len(satisfied_7)}): {', '.join([req.split(' (')[0] for req in satisfied_7])}")
        print(f"   Missing ({len(missing_7)}): {', '.join([req.split(' (')[0] for req in missing_7])}")
        
        print()
        
        # Check satisfaction for 8 steps
        completed_connectors_8 = [step['connector_name'] for step in eight_steps]
        satisfied_8 = []
        missing_8 = []
        
        for req in explicit_requirements:
            connector_name = req.split(' (')[0]
            if connector_name in completed_connectors_8:
                satisfied_8.append(req)
            else:
                missing_8.append(req)
        
        print(f"📊 8-Step Analysis:")
        print(f"   Satisfied ({len(satisfied_8)}): {', '.join([req.split(' (')[0] for req in satisfied_8])}")
        print(f"   Missing ({len(missing_8)}): {', '.join([req.split(' (')[0] for req in missing_8])}")
        
        print()
        print("🎯 Expected Results:")
        print("   - 7 steps: INCOMPLETE (missing notion)")
        print("   - 8 steps: COMPLETE (all requirements satisfied)")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting Requirement Detection Test")
    
    # Run the test
    asyncio.run(test_requirement_detection())
    
    print("\\n✨ Test completed!")