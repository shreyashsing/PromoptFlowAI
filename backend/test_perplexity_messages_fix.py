#!/usr/bin/env python3
"""
Test Perplexity connector messages parameter fix.
"""
import asyncio
from app.connectors.core.perplexity_connector import PerplexityConnector
from app.core.exceptions import ValidationException

async def test_perplexity_empty_messages():
    """Test that Perplexity connector handles empty string for messages."""
    print("🧪 Testing Perplexity connector with empty messages string...")
    
    connector = PerplexityConnector()
    
    # Test parameters that were causing the validation error
    test_params = {
        "action": "chat",
        "messages": ""  # Empty string - this was likely the issue
    }
    
    try:
        result = await connector.validate_params(test_params)
        if result:
            print("✅ Validation passed with empty messages string")
            
            # Test normalization
            normalized = connector._normalize_array_parameters(test_params)
            expected = []
            if normalized["messages"] == expected:
                print("✅ Empty messages string normalized to empty array correctly")
                return True
            else:
                print(f"❌ Expected {expected}, got {normalized['messages']}")
                return False
        else:
            print("❌ Validation returned False")
            return False
    except ValidationException as e:
        print(f"❌ Validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_perplexity_json_messages():
    """Test that Perplexity connector handles JSON string for messages."""
    print("🧪 Testing Perplexity connector with JSON messages string...")
    
    connector = PerplexityConnector()
    
    # Test parameters with JSON string
    test_params = {
        "action": "chat",
        "messages": '[{"role": "user", "content": "Hello"}]'
    }
    
    try:
        result = await connector.validate_params(test_params)
        if result:
            print("✅ Validation passed with JSON messages string")
            
            # Test normalization
            normalized = connector._normalize_array_parameters(test_params)
            expected = [{"role": "user", "content": "Hello"}]
            if normalized["messages"] == expected:
                print("✅ JSON messages string normalized to array correctly")
                return True
            else:
                print(f"❌ Expected {expected}, got {normalized['messages']}")
                return False
        else:
            print("❌ Validation returned False")
            return False
    except ValidationException as e:
        print(f"❌ Validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_perplexity_plain_text_messages():
    """Test that Perplexity connector handles plain text for messages."""
    print("🧪 Testing Perplexity connector with plain text messages...")
    
    connector = PerplexityConnector()
    
    # Test parameters with plain text
    test_params = {
        "action": "chat",
        "messages": "What is AI?"
    }
    
    try:
        result = await connector.validate_params(test_params)
        if result:
            print("✅ Validation passed with plain text messages")
            
            # Test normalization
            normalized = connector._normalize_array_parameters(test_params)
            expected = [{"role": "user", "content": "What is AI?"}]
            if normalized["messages"] == expected:
                print("✅ Plain text messages normalized to array correctly")
                return True
            else:
                print(f"❌ Expected {expected}, got {normalized['messages']}")
                return False
        else:
            print("❌ Validation returned False")
            return False
    except ValidationException as e:
        print(f"❌ Validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_perplexity_array_messages():
    """Test that Perplexity connector still works with array messages."""
    print("🧪 Testing Perplexity connector with array messages...")
    
    connector = PerplexityConnector()
    
    # Test parameters with array format
    test_params = {
        "action": "chat",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    
    try:
        result = await connector.validate_params(test_params)
        if result:
            print("✅ Validation passed with array messages")
            
            # Test normalization (should remain unchanged)
            normalized = connector._normalize_array_parameters(test_params)
            expected = [{"role": "user", "content": "Hello"}]
            if normalized["messages"] == expected:
                print("✅ Array messages preserved correctly")
                return True
            else:
                print(f"❌ Expected {expected}, got {normalized['messages']}")
                return False
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
    """Run all tests."""
    print("🚀 Testing Perplexity messages parameter fixes...\n")
    
    results = []
    
    # Test empty messages string (the main issue)
    results.append(await test_perplexity_empty_messages())
    print()
    
    # Test JSON messages string
    results.append(await test_perplexity_json_messages())
    print()
    
    # Test plain text messages
    results.append(await test_perplexity_plain_text_messages())
    print()
    
    # Test array messages
    results.append(await test_perplexity_array_messages())
    print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Perplexity messages parameter fixes are working correctly!")
        print("\n📝 Summary of fix:")
        print("   • messages parameter now accepts both string and array formats")
        print("   • Empty strings are converted to empty arrays")
        print("   • JSON strings are parsed into arrays")
        print("   • Plain text is converted to user message objects")
        print("   • Array parameters are preserved as-is")
        print("\n✅ The Perplexity workflow execution error should now be resolved.")
    else:
        print("❌ Some Perplexity messages parameter fixes are not working correctly.")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main())