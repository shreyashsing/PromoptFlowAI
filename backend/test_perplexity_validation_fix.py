#!/usr/bin/env python3
"""
Test Perplexity connector validation fix.
"""
import asyncio
from app.connectors.core.perplexity_connector import PerplexityConnector
from app.core.exceptions import ValidationException

async def test_perplexity_validation_with_empty_string():
    """Test that Perplexity connector validation handles empty string for search_domain_filter."""
    print("🧪 Testing Perplexity connector validation with empty string...")
    
    connector = PerplexityConnector()
    
    # Test parameters that were causing the validation error
    test_params = {
        "action": "search",
        "query": "test query",
        "search_domain_filter": ""  # Empty string - this was the issue
    }
    
    try:
        # This should now pass validation
        result = await connector.validate_params(test_params)
        if result:
            print("✅ Validation passed with empty string")
            return True
        else:
            print("❌ Validation returned False")
            return False
    except ValidationException as e:
        print(f"❌ Validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_perplexity_validation_with_comma_string():
    """Test that Perplexity connector validation handles comma-separated string."""
    print("🧪 Testing Perplexity connector validation with comma-separated string...")
    
    connector = PerplexityConnector()
    
    # Test parameters with comma-separated domains
    test_params = {
        "action": "search",
        "query": "test query",
        "search_domain_filter": "example.com,news.com"
    }
    
    try:
        result = await connector.validate_params(test_params)
        if result:
            print("✅ Validation passed with comma-separated string")
            return True
        else:
            print("❌ Validation returned False")
            return False
    except ValidationException as e:
        print(f"❌ Validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_perplexity_validation_with_array():
    """Test that Perplexity connector validation still works with arrays."""
    print("🧪 Testing Perplexity connector validation with array...")
    
    connector = PerplexityConnector()
    
    # Test parameters with array format
    test_params = {
        "action": "search",
        "query": "test query",
        "search_domain_filter": ["example.com", "news.com"]
    }
    
    try:
        result = await connector.validate_params(test_params)
        if result:
            print("✅ Validation passed with array")
            return True
        else:
            print("❌ Validation returned False")
            return False
    except ValidationException as e:
        print(f"❌ Validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def main():
    """Run all validation tests."""
    print("🚀 Testing Perplexity validation fixes...\n")
    
    results = []
    
    # Test empty string (the main issue)
    results.append(await test_perplexity_validation_with_empty_string())
    print()
    
    # Test comma-separated string
    results.append(await test_perplexity_validation_with_comma_string())
    print()
    
    # Test array format
    results.append(await test_perplexity_validation_with_array())
    print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Perplexity validation fixes are working correctly!")
        print("\n📝 Summary of fix:")
        print("   • Overridden validate_params to normalize array parameters before validation")
        print("   • Empty strings are converted to empty arrays before schema validation")
        print("   • Comma-separated strings are split into arrays before schema validation")
        print("   • Array parameters are preserved as-is")
        print("\n✅ The Perplexity workflow execution error should now be resolved.")
    else:
        print("❌ Some Perplexity validation fixes are not working correctly.")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main())