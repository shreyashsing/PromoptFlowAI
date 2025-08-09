#!/usr/bin/env python3
"""
Test that the AI agent correctly configures text summarizer parameters
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.true_react_agent import TrueReActAgent

async def test_text_summarizer_parameter_configuration():
    """Test that text summarizer gets the correct parameter reference"""
    
    print("🧪 Testing text summarizer parameter configuration...")
    
    # Create the agent
    agent = TrueReActAgent()
    
    # Simulate a workflow with: Perplexity → Code → Text Summarizer
    current_steps = [
        {
            "step_number": 1,
            "connector_name": "perplexity_search",
            "purpose": "Search for blog posts"
        },
        {
            "step_number": 2,
            "connector_name": "code",
            "purpose": "Process search results and extract content"
        }
    ]
    
    # Test parameter resolution for text summarizer
    user_request = "summarize the blog posts"
    
    # Mock the parameter resolution
    try:
        # This simulates how the agent would resolve the 'text' parameter for text_summarizer
        # We need to call the internal method that resolves parameters
        
        # Create a mock parameter schema for text summarizer
        param_name = "text"
        param_schema = {"type": "string", "description": "The text content to summarize"}
        connector_name = "text_summarizer"
        
        # Call the parameter resolution method
        properties = {"text": param_schema}
        resolved_params = await agent._pattern_based_parameter_extraction(
            connector_name, properties, user_request, current_steps
        )
        resolved_value = resolved_params.get("text", "")
        
        print(f"✅ Resolved 'text' parameter: {resolved_value}")
        
        # Check if it correctly references the code node's combinedText field
        expected_reference = "{{code.combinedText}}"
        
        if resolved_value == expected_reference:
            print("🎉 SUCCESS: Text summarizer correctly references code.combinedText!")
            return True
        else:
            print(f"❌ FAILED: Expected '{expected_reference}', got '{resolved_value}'")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def test_other_connectors_still_work():
    """Test that other connectors still get correct references"""
    
    print("\n🧪 Testing other connector parameter resolution...")
    
    agent = TrueReActAgent()
    
    # Test Gmail connector after text summarizer
    current_steps = [
        {
            "step_number": 1,
            "connector_name": "perplexity_search",
            "purpose": "Search for blog posts"
        },
        {
            "step_number": 2,
            "connector_name": "code",
            "purpose": "Process search results"
        },
        {
            "step_number": 3,
            "connector_name": "text_summarizer",
            "purpose": "Summarize content"
        }
    ]
    
    try:
        # Test Gmail body parameter - should reference text_summarizer.result
        properties = {"body": {"type": "string"}}
        resolved_params = await agent._pattern_based_parameter_extraction(
            "gmail_connector", properties, "send email with summary", current_steps
        )
        resolved_value = resolved_params.get("body", "")
        
        print(f"✅ Gmail body parameter: {resolved_value}")
        
        # Should reference the text summarizer result
        if "text_summarizer.result" in resolved_value:
            print("🎉 SUCCESS: Gmail correctly references text_summarizer.result!")
            return True
        else:
            print(f"❌ FAILED: Gmail should reference text_summarizer, got '{resolved_value}'")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def main():
    """Run all tests"""
    test1 = await test_text_summarizer_parameter_configuration()
    test2 = await test_other_connectors_still_work()
    
    if test1 and test2:
        print("\n🎉 All tests passed! Text summarizer will get correct parameters.")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)