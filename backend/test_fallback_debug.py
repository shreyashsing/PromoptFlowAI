#!/usr/bin/env python3
"""
Debug script to see what the fallback logic is doing.
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

def test_fallback_logic():
    """Test the fallback logic manually."""
    print("🧪 Testing Fallback Logic")
    print("=" * 40)
    
    # Test the complex user request
    user_request = "Find the top 5 recent blog posts by Google using Perplexity. Summarize all 5 into one combined summary. Find 3 relevant YouTube videos related to the blog topics. Save the summary in Google Docs (Drive), log everything to Google Sheets and Airtable, email the summary with links to shreyashbarca10@gmail.com, and create a detailed Notion page with all content and links."
    
    # Test the 8-step complete scenario
    complete_steps = [
        {"connector_name": "perplexity_search", "purpose": "Find blog posts"},
        {"connector_name": "text_summarizer", "purpose": "Summarize content"},
        {"connector_name": "youtube", "purpose": "Find related videos"},
        {"connector_name": "google_drive", "purpose": "Save to Google Docs"},
        {"connector_name": "google_sheets", "purpose": "Log to spreadsheet"},
        {"connector_name": "airtable", "purpose": "Store in database"},
        {"connector_name": "gmail_connector", "purpose": "Send email"},
        {"connector_name": "notion", "purpose": "Create detailed page"}
    ]
    
    print(f"📋 User Request: {user_request}")
    print()
    print(f"🔧 Complete Workflow Steps ({len(complete_steps)}):")
    for i, step in enumerate(complete_steps, 1):
        print(f"   {i}. {step['connector_name']}: {step['purpose']}")
    print()
    
    # Analyze request complexity
    original_request = user_request.lower()
    
    action_indicators = ['find', 'search', 'get', 'retrieve', 'summarize', 'process', 'analyze', 
                       'save', 'store', 'log', 'email', 'send', 'create', 'upload', 'generate']
    
    platform_indicators = ['google', 'drive', 'docs', 'sheets', 'gmail', 'youtube', 'airtable', 
                         'notion', 'perplexity', 'slack', 'discord', 'twitter', 'facebook']
    
    action_count = sum(1 for action in action_indicators if action in original_request)
    platform_count = sum(1 for platform in platform_indicators if platform in original_request)
    
    print(f"📊 Request Analysis:")
    print(f"   Action count: {action_count}")
    print(f"   Platform count: {platform_count}")
    print(f"   Actions found: {[action for action in action_indicators if action in original_request]}")
    print(f"   Platforms found: {[platform for platform in platform_indicators if platform in original_request]}")
    print()
    
    # Check complexity thresholds
    if action_count <= 3 and platform_count <= 2 and len(complete_steps) >= 2:
        print("✅ Simple request threshold met")
    elif action_count >= 6 or platform_count >= 4:
        # Use updated logic
        min_steps_needed = max(action_count - 1, min(platform_count - 1, 8), 4)
        print(f"🔍 Complex request detected - need at least {min_steps_needed} steps, have {len(complete_steps)}")
        if len(complete_steps) < min_steps_needed:
            print("❌ Not enough steps for complex request")
        else:
            print("✅ Sufficient steps for complex request")
    
    # Check pattern detection
    connector_names = [step['connector_name'] for step in complete_steps]
    print(f"🔧 Connector names: {connector_names}")
    print()
    
    # Test pattern detection (updated to match new logic)
    input_keywords = ['search', 'find', 'get', 'retrieve', 'perplexity']
    process_keywords = ['summarize', 'process', 'analyze', 'transform', 'text']
    output_keywords = ['save', 'store', 'send', 'create', 'upload']
    output_connectors = ['drive', 'sheets', 'gmail', 'email', 'notion', 'airtable', 'slack', 'discord']
    
    has_input = any(any(keyword in name.lower() for keyword in input_keywords) for name in connector_names)
    has_process = any(any(keyword in name.lower() for keyword in process_keywords) for name in connector_names)
    has_output = any(
        any(keyword in name.lower() for keyword in output_keywords) or
        any(output_conn in name.lower() for output_conn in output_connectors)
        for name in connector_names
    )
    
    print(f"🔍 Pattern Detection:")
    print(f"   Input keywords: {input_keywords}")
    print(f"   Process keywords: {process_keywords}")
    print(f"   Output keywords: {output_keywords}")
    print(f"   Output connectors: {output_connectors}")
    print()
    
    print(f"📊 Pattern Analysis:")
    print(f"   Has input: {has_input}")
    print(f"   Has process: {has_process}")
    print(f"   Has output: {has_output}")
    print()
    
    # Check each connector against patterns
    print("🔍 Detailed Pattern Matching:")
    for name in connector_names:
        input_match = any(keyword in name.lower() for keyword in input_keywords)
        process_match = any(keyword in name.lower() for keyword in process_keywords)
        output_match = (
            any(keyword in name.lower() for keyword in output_keywords) or
            any(output_conn in name.lower() for output_conn in output_connectors)
        )
        
        pattern_type = []
        if input_match:
            pattern_type.append("INPUT")
        if process_match:
            pattern_type.append("PROCESS")
        if output_match:
            pattern_type.append("OUTPUT")
        
        if not pattern_type:
            pattern_type.append("NONE")
        
        print(f"   {name}: {', '.join(pattern_type)}")
    
    print()
    
    # Final decision
    if has_input and has_process and has_output:
        print("✅ Complete workflow pattern detected - should be COMPLETE")
    else:
        print("❌ Incomplete workflow pattern - marked as INCOMPLETE")
        print(f"   Missing: {', '.join([p for p, has in [('INPUT', has_input), ('PROCESS', has_process), ('OUTPUT', has_output)] if not has])}")


if __name__ == "__main__":
    print("🚀 Starting Fallback Logic Debug Test")
    
    # Run the test
    test_fallback_logic()
    
    print("\\n✨ Debug completed!")