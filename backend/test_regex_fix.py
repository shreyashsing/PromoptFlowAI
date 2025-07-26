#!/usr/bin/env python3
"""
Test the regex patterns for parameter resolution.
"""
import re

def test_regex_patterns():
    """Test regex patterns for parameter resolution."""
    print("🧪 Testing Regex Patterns")
    print("=" * 30)
    
    # Test patterns
    patterns = [
        r'\$\{([^}]+)\}',      # ${...} format
        r'\{\{([^}]+)\}\}',    # {{...}} format (double braces)
        r'\{([^}]+)\}'         # {...} format (single braces)
    ]
    
    # Test cases
    test_cases = [
        "{{text_summarizer.result}}",
        "{text_summarizer.result}",
        "${text_summarizer.result}",
        "The summary is {{text_summarizer.result}} and done",
        "Mixed: {{conn1.result}} and {conn2.result}",
        "Email body: {{text_summarizer.result}}"
    ]
    
    for test_value in test_cases:
        print(f"\n📝 Testing: '{test_value}'")
        
        for i, pattern in enumerate(patterns, 1):
            matches = re.findall(pattern, test_value)
            pattern_name = ["${...}", "{{...}}", "{...}"][i-1]
            
            if matches:
                print(f"   ✅ Pattern {pattern_name}: Found {matches}")
                
                # Test replacement logic
                for reference in matches:
                    if pattern.startswith(r'\$'):
                        original_pattern = f"${{{reference}}}"
                    elif pattern.startswith(r'\{\{'):
                        original_pattern = f"{{{{{reference}}}}}"  # Double braces
                    else:
                        original_pattern = f"{{{reference}}}"       # Single braces
                    
                    print(f"      📋 Reference: '{reference}' → Replace: '{original_pattern}'")
            else:
                print(f"   ❌ Pattern {pattern_name}: No matches")
    
    print("\n✅ Regex testing complete!")

if __name__ == "__main__":
    test_regex_patterns() 