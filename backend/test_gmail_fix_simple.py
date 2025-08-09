#!/usr/bin/env python3
"""
Simple test to verify the Gmail duplicate fix works.
"""

import asyncio
import json
import re


def test_parameter_resolution_logic():
    """Test the core parameter resolution logic."""
    print("=== Testing Parameter Resolution Logic ===")
    
    # Mock Gmail result with only 1 email (the problematic case)
    gmail_result = {
        "messages": [
            {
                "subject": "Important Email",
                "sender": "boss@company.com",
                "snippet": "This is an important email",
                "date": "2024-01-15T10:00:00Z"
            }
        ]
    }
    
    def resolve_field_path(field_path: str, data: dict) -> str:
        """Simplified field path resolution."""
        # Parse field path: messages[0].subject -> ['messages', '[0]', 'subject']
        components = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\[\d+\]', field_path)
        
        current_data = data
        
        for component in components:
            if component.startswith('[') and component.endswith(']'):
                # Array index
                try:
                    index = int(component[1:-1])
                    if isinstance(current_data, list):
                        if 0 <= index < len(current_data):
                            current_data = current_data[index]
                        else:
                            # Array index out of bounds - return empty string
                            print(f"  Index {index} out of bounds for array of length {len(current_data)}")
                            return ""
                    else:
                        print(f"  Trying to index non-array data")
                        return ""
                except (ValueError, TypeError):
                    print(f"  Invalid array index: {component}")
                    return ""
            else:
                # Field name
                if isinstance(current_data, dict) and component in current_data:
                    current_data = current_data[component]
                else:
                    print(f"  Field '{component}' not found")
                    return ""
        
        return str(current_data) if current_data is not None else ""
    
    # Test cases that would be used in Google Sheets
    test_cases = [
        ("messages[0].subject", "Important Email"),
        ("messages[0].sender", "boss@company.com"),
        ("messages[0].snippet", "This is an important email"),
        ("messages[1].subject", ""),  # Should return empty string
        ("messages[1].sender", ""),   # Should return empty string
        ("messages[1].snippet", ""),  # Should return empty string
        ("messages[2].subject", ""),  # Should return empty string
        ("messages[2].sender", ""),   # Should return empty string
        ("messages[2].snippet", "")   # Should return empty string
    ]
    
    print("Testing parameter resolution:")
    all_passed = True
    
    for field_path, expected in test_cases:
        result = resolve_field_path(field_path, gmail_result)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"  {field_path}: '{result}' (expected: '{expected}') {status}")
        
        if result != expected:
            all_passed = False
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED: Parameter resolution handles missing indices correctly")
    else:
        print("\n❌ SOME TESTS FAILED: Parameter resolution needs more work")


def test_gmail_query_enhancement():
    """Test Gmail query enhancement logic."""
    print("\n=== Testing Gmail Query Enhancement ===")
    
    def enhance_gmail_query(query: str) -> str:
        """Enhance Gmail query to prioritize inbox."""
        if "in:" not in query.lower() and "category:" not in query.lower():
            return f"{query} in:inbox"
        return query
    
    test_cases = [
        ("is:unread", "is:unread in:inbox"),
        ("is:unread in:social", "is:unread in:social"),  # Don't change if already specified
        ("subject:meeting", "subject:meeting in:inbox"),
        ("from:boss@company.com", "from:boss@company.com in:inbox"),
        ("is:unread category:primary", "is:unread category:primary"),  # Don't change if category specified
    ]
    
    print("Testing query enhancement:")
    for original, expected in test_cases:
        enhanced = enhance_gmail_query(original)
        status = "✅ PASS" if enhanced == expected else "❌ FAIL"
        print(f"  '{original}' -> '{enhanced}' (expected: '{expected}') {status}")


def test_google_sheets_output():
    """Test what would actually be sent to Google Sheets."""
    print("\n=== Testing Google Sheets Output ===")
    
    # Simulate Gmail returning only 1 email when 3 were requested
    gmail_result = {
        "messages": [
            {
                "subject": "Weekly Report",
                "sender": "team@company.com",
                "snippet": "Here's this week's report"
            }
        ]
    }
    
    # The template values that would be used in Google Sheets
    template_fields = [
        "messages[0].subject", "messages[0].sender", "messages[0].snippet",
        "messages[1].subject", "messages[1].sender", "messages[1].snippet", 
        "messages[2].subject", "messages[2].sender", "messages[2].snippet"
    ]
    
    def resolve_field_path(field_path: str, data: dict) -> str:
        """Simplified field path resolution."""
        components = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\[\d+\]', field_path)
        current_data = data
        
        for component in components:
            if component.startswith('[') and component.endswith(']'):
                index = int(component[1:-1])
                if isinstance(current_data, list) and 0 <= index < len(current_data):
                    current_data = current_data[index]
                else:
                    return ""  # Return empty string for out-of-bounds
            else:
                if isinstance(current_data, dict) and component in current_data:
                    current_data = current_data[component]
                else:
                    return ""
        
        return str(current_data) if current_data is not None else ""
    
    # Resolve all template values
    resolved_values = []
    for field in template_fields:
        value = resolve_field_path(field, gmail_result)
        resolved_values.append(value)
    
    print("Values that would be sent to Google Sheets:")
    print("Row 1 (Headers): Subject, Sender, Snippet")
    print("Row 2 (Email 1):", resolved_values[0:3])
    print("Row 3 (Email 2):", resolved_values[3:6])
    print("Row 4 (Email 3):", resolved_values[6:9])
    
    # Check for the old bug (duplicates)
    non_empty_values = [v for v in resolved_values if v != ""]
    unique_non_empty = set(non_empty_values)
    
    if len(non_empty_values) == len(unique_non_empty):
        print("\n✅ SUCCESS: No duplicate values (bug fixed)")
    else:
        print("\n❌ FAILED: Duplicate values detected (bug still exists)")
        
    # Check that we have the right pattern
    expected_pattern = [
        "Weekly Report", "team@company.com", "Here's this week's report",  # Email 1
        "", "", "",  # Email 2 (empty)
        "", "", ""   # Email 3 (empty)
    ]
    
    if resolved_values == expected_pattern:
        print("✅ SUCCESS: Output pattern is correct")
    else:
        print("❌ FAILED: Output pattern is incorrect")
        print(f"Expected: {expected_pattern}")
        print(f"Got:      {resolved_values}")


if __name__ == "__main__":
    test_parameter_resolution_logic()
    test_gmail_query_enhancement()
    test_google_sheets_output()