#!/usr/bin/env python3
"""
Test the dynamic connector analysis system
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent

async def test_dynamic_connector_categorization():
    """Test that connectors are dynamically categorized based on their metadata"""
    
    print("🧪 Testing dynamic connector categorization...")
    
    agent = TrueReActAgent()
    
    # Mock tool metadata for different types of connectors
    mock_tool_metadata = {
        'perplexity_search': {
            'description': 'Search and find information using AI-powered search',
            'category': 'search'
        },
        'gmail_connector': {
            'description': 'Send emails and manage Gmail communications',
            'category': 'communication'
        },
        'text_summarizer': {
            'description': 'Summarize and analyze text content using AI',
            'category': 'ai_services'
        },
        'google_sheets': {
            'description': 'Manage data in Google Sheets spreadsheets',
            'category': 'data_sources'
        },
        'code': {
            'description': 'Execute custom code for data transformation',
            'category': 'processing'
        },
        'custom_api_connector': {
            'description': 'Connect to external APIs for data retrieval',
            'category': 'integration'
        },
        'slack_messenger': {
            'description': 'Send messages and notifications via Slack',
            'category': 'communication'
        }
    }
    
    available_tools = list(mock_tool_metadata.keys())
    base_prompt = "USER REQUEST: Test request\n\nDYNAMIC CONNECTOR ANALYSIS:\nOriginal analysis here"
    
    try:
        # Test the dynamic connector insights
        enhanced_prompt = await agent._add_dynamic_connector_insights(
            base_prompt, available_tools, mock_tool_metadata
        )
        
        print("✅ Enhanced prompt generated")
        
        # Check if different categories are identified
        categories_found = {
            'search': 'SEARCH CONNECTORS' in enhanced_prompt,
            'ai': 'AI PROCESSING CONNECTORS' in enhanced_prompt,
            'communication': 'COMMUNICATION CONNECTORS' in enhanced_prompt,
            'data': 'DATA CONNECTORS' in enhanced_prompt,
            'transformation': 'TRANSFORMATION CONNECTORS' in enhanced_prompt
        }
        
        print(f"📊 Categories identified: {sum(categories_found.values())}/5")
        
        for category, found in categories_found.items():
            status = "✅" if found else "❌"
            print(f"   {status} {category.title()} connectors")
        
        # Check specific connector categorization
        if 'perplexity_search' in enhanced_prompt and 'SEARCH CONNECTORS' in enhanced_prompt:
            print("✅ Search connectors correctly identified")
        else:
            print("❌ Search connectors not properly categorized")
            
        if 'gmail_connector, slack_messenger' in enhanced_prompt or 'slack_messenger, gmail_connector' in enhanced_prompt:
            print("✅ Multiple communication connectors grouped together")
        else:
            print("❌ Communication connectors not properly grouped")
        
        return sum(categories_found.values()) >= 4  # At least 4 out of 5 categories should be found
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def test_scalability_with_many_connectors():
    """Test that the system works with a large number of connectors"""
    
    print("\n🧪 Testing scalability with many connectors...")
    
    agent = TrueReActAgent()
    
    # Generate metadata for 50 mock connectors
    mock_tool_metadata = {}
    connector_types = [
        ('search', 'Search and find information'),
        ('ai', 'AI-powered analysis and processing'),
        ('communication', 'Send messages and notifications'),
        ('data', 'Manage and store data'),
        ('integration', 'Connect to external services')
    ]
    
    for i in range(50):
        connector_type, description = connector_types[i % len(connector_types)]
        mock_tool_metadata[f'{connector_type}_connector_{i}'] = {
            'description': f'{description} - connector {i}',
            'category': connector_type
        }
    
    # Add the code connector
    mock_tool_metadata['code'] = {
        'description': 'Execute custom code for data transformation',
        'category': 'processing'
    }
    
    available_tools = list(mock_tool_metadata.keys())
    base_prompt = "USER REQUEST: Test with many connectors\n\nDYNAMIC CONNECTOR ANALYSIS:\nOriginal analysis"
    
    try:
        # Test with many connectors
        enhanced_prompt = await agent._add_dynamic_connector_insights(
            base_prompt, available_tools, mock_tool_metadata
        )
        
        print(f"✅ Successfully processed {len(available_tools)} connectors")
        
        # Check that categories are still properly identified
        categories_in_prompt = enhanced_prompt.count('CONNECTORS:')
        print(f"📊 Found {categories_in_prompt} connector categories")
        
        # Check that the prompt isn't too long (should be manageable)
        prompt_length = len(enhanced_prompt)
        print(f"📏 Enhanced prompt length: {prompt_length} characters")
        
        if prompt_length < 10000:  # Reasonable limit
            print("✅ Prompt length is manageable")
            return True
        else:
            print("❌ Prompt is too long, may need optimization")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def main():
    """Run all tests"""
    test1 = await test_dynamic_connector_categorization()
    test2 = await test_scalability_with_many_connectors()
    
    success_count = sum([test1, test2])
    total_tests = 2
    
    print(f"\n📈 Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Dynamic connector analysis is working and scalable.")
        return True
    else:
        print("❌ Some tests failed. System needs improvement for scalability.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)