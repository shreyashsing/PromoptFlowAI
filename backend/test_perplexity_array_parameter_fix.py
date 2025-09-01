#!/usr/bin/env python3
"""
Test Perplexity connector array parameter fix.
"""
import asyncio
import json
from app.connectors.core.perplexity_connector import PerplexityConnector
from jsonschema import validate, ValidationError

async def test_perplexity_array_parameters():
    """Test that Perplexity connector handles both string and array formats for search_domain_filter."""
    print("🧪 Testing Perplexity connector array parameter handling...")
    
    connector = PerplexityConnector()
    schema = connector._define_schema()
    
    # Test 1: Empty string (this was causing the error)
    test_params_1 = {
        "action": "search",
        "query": "test query",
        "search_domain_filter": ""  # Empty string - this was the issue
    }
    
    try:
        validate(test_params_1, schema)
        print("✅ Test 1: Empty string validation passed")
        
        # Test normalization
        normalized_1 = connector._normalize_array_parameters(test_params_1)
        expected_1 = []
        if normalized_1["search_domain_filter"] == expected_1:
            print("✅ Test 1: Empty string normalized to empty array correctly")
        else:
            print(f"❌ Test 1: Expected {expected_1}, got {normalized_1['search_domain_filter']}")
            return False
            
    except ValidationError as e:
        print(f"❌ Test 1: Empty string validation failed: {e.message}")
        return False
    
    # Test 2: Comma-separated string
    test_params_2 = {
        "action": "search",
        "query": "test query",
        "search_domain_filter": "example.com,news.com,blog.com"
    }
    
    try:
        validate(test_params_2, schema)
        print("✅ Test 2: Comma-separated string validation passed")
        
        # Test normalization
        normalized_2 = connector._normalize_array_parameters(test_params_2)
        expected_2 = ["example.com", "news.com", "blog.com"]
        if normalized_2["search_domain_filter"] == expected_2:
            print("✅ Test 2: Comma-separated string normalized to array correctly")
        else:
            print(f"❌ Test 2: Expected {expected_2}, got {normalized_2['search_domain_filter']}")
            return False
            
    except ValidationError as e:
        print(f"❌ Test 2: Comma-separated string validation failed: {e.message}")
        return False
    
    # Test 3: Array format (should work as before)
    test_params_3 = {
        "action": "search",
        "query": "test query",
        "search_domain_filter": ["example.com", "news.com"]
    }
    
    try:
        validate(test_params_3, schema)
        print("✅ Test 3: Array format validation passed")
        
        # Test normalization (should remain unchanged)
        normalized_3 = connector._normalize_array_parameters(test_params_3)
        expected_3 = ["example.com", "news.com"]
        if normalized_3["search_domain_filter"] == expected_3:
            print("✅ Test 3: Array format preserved correctly")
        else:
            print(f"❌ Test 3: Expected {expected_3}, got {normalized_3['search_domain_filter']}")
            return False
            
    except ValidationError as e:
        print(f"❌ Test 3: Array format validation failed: {e.message}")
        return False
    
    # Test 4: String with extra whitespace
    test_params_4 = {
        "action": "search",
        "query": "test query",
        "search_domain_filter": " example.com , news.com , "
    }
    
    try:
        validate(test_params_4, schema)
        print("✅ Test 4: String with whitespace validation passed")
        
        # Test normalization
        normalized_4 = connector._normalize_array_parameters(test_params_4)
        expected_4 = ["example.com", "news.com"]
        if normalized_4["search_domain_filter"] == expected_4:
            print("✅ Test 4: String with whitespace normalized correctly")
        else:
            print(f"❌ Test 4: Expected {expected_4}, got {normalized_4['search_domain_filter']}")
            return False
            
    except ValidationError as e:
        print(f"❌ Test 4: String with whitespace validation failed: {e.message}")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("🚀 Testing Perplexity array parameter fixes...\n")
    
    success = await test_perplexity_array_parameters()
    
    print()
    if success:
        print("🎉 All Perplexity array parameter tests passed!")
        print("\n📝 Summary of fix:")
        print("   • search_domain_filter now accepts both string and array formats")
        print("   • Empty strings are converted to empty arrays")
        print("   • Comma-separated strings are split into arrays")
        print("   • Whitespace is properly handled")
        print("\n✅ The Perplexity workflow execution error should now be resolved.")
    else:
        print("❌ Some Perplexity array parameter tests failed.")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main())