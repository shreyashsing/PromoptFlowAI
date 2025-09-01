#!/usr/bin/env python3
"""
Test parameter validation fixes for Perplexity and Gmail connectors.
"""
import asyncio
import json
from app.connectors.core.perplexity_connector import PerplexityConnector
from app.connectors.core.gmail_connector import GmailConnector
from app.models.connector import ConnectorExecutionContext
from jsonschema import validate, ValidationError

async def test_perplexity_stream_parameter():
    """Test that Perplexity connector now accepts stream parameter."""
    print("🧪 Testing Perplexity connector with stream parameter...")
    
    connector = PerplexityConnector()
    schema = connector._define_schema()
    
    # Test parameters that previously failed
    test_params = {
        "action": "search",
        "query": "test query",
        "stream": False  # This was causing the validation error
    }
    
    try:
        validate(test_params, schema)
        print("✅ Perplexity: stream parameter validation passed")
        return True
    except ValidationError as e:
        print(f"❌ Perplexity: stream parameter validation failed: {e.message}")
        return False

async def test_gmail_empty_label_color():
    """Test that Gmail connector now accepts empty label_color."""
    print("🧪 Testing Gmail connector with empty label_color...")
    
    connector = GmailConnector()
    schema = connector._define_schema()
    
    # Test parameters that previously failed
    test_params = {
        "action": "create_label",
        "label_name": "Test Label",
        "label_color": ""  # This was causing the validation error
    }
    
    try:
        validate(test_params, schema)
        print("✅ Gmail: empty label_color validation passed")
        return True
    except ValidationError as e:
        print(f"❌ Gmail: empty label_color validation failed: {e.message}")
        return False

async def test_gmail_valid_label_colors():
    """Test that Gmail connector still accepts valid label colors."""
    print("🧪 Testing Gmail connector with valid label colors...")
    
    connector = GmailConnector()
    schema = connector._define_schema()
    
    valid_colors = ["red", "orange", "yellow", "green", "teal", "blue", "purple", "pink", "brown", "gray"]
    
    for color in valid_colors:
        test_params = {
            "action": "create_label",
            "label_name": "Test Label",
            "label_color": color
        }
        
        try:
            validate(test_params, schema)
        except ValidationError as e:
            print(f"❌ Gmail: valid color '{color}' validation failed: {e.message}")
            return False
    
    print("✅ Gmail: all valid label colors validation passed")
    return True

async def main():
    """Run all parameter validation tests."""
    print("🚀 Testing parameter validation fixes...\n")
    
    results = []
    
    # Test Perplexity stream parameter
    results.append(await test_perplexity_stream_parameter())
    print()
    
    # Test Gmail empty label_color
    results.append(await test_gmail_empty_label_color())
    print()
    
    # Test Gmail valid label colors
    results.append(await test_gmail_valid_label_colors())
    print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All parameter validation fixes are working correctly!")
        print("\n📝 Summary of fixes:")
        print("   • Perplexity connector now accepts 'stream' parameter (ignored but allowed)")
        print("   • Gmail connector now accepts empty string for 'label_color' parameter")
        print("\n✅ The workflow execution errors should now be resolved.")
    else:
        print("❌ Some parameter validation fixes are not working correctly.")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main())