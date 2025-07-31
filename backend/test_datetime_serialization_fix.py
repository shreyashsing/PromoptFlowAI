#!/usr/bin/env python3
"""
Test script to verify that datetime serialization issues are fixed.
This addresses the "'str' object has no attribute 'isoformat'" error.
"""

import sys
import os
import json
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.models.react_response_models import (
    ReactAgentResponse, create_success_response, create_error_response,
    create_reasoning_step, create_tool_call
)


def test_datetime_serialization():
    """Test that datetime objects are properly serialized."""
    print("🧪 Testing datetime serialization...")
    
    # Create a response with datetime objects
    response = create_success_response(
        response="Test response",
        session_id="test-session-123",
        reasoning_trace=[
            create_reasoning_step(1, "thought", "Test thought")
        ],
        tool_calls=[
            create_tool_call("test_tool", {"param": "value"})
        ]
    )
    
    # Ensure created_at is a datetime object
    assert isinstance(response.created_at, datetime), f"created_at should be datetime, got {type(response.created_at)}"
    print(f"✅ created_at is datetime: {response.created_at}")
    
    # Test to_dict conversion
    try:
        response_dict = response.to_dict()
        print("✅ to_dict() conversion successful")
        
        # Check that created_at is now a string
        created_at_str = response_dict.get('created_at')
        assert isinstance(created_at_str, str), f"created_at in dict should be string, got {type(created_at_str)}"
        print(f"✅ created_at serialized to string: {created_at_str}")
        
    except AttributeError as e:
        if "isoformat" in str(e):
            print(f"❌ isoformat error still occurs: {e}")
            return False
        else:
            raise
    
    # Test JSON serialization
    try:
        json_str = json.dumps(response_dict, default=str)
        print("✅ JSON serialization successful")
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False
    
    # Test from_dict conversion back
    try:
        restored_response = ReactAgentResponse.from_dict(response_dict)
        print("✅ from_dict() conversion successful")
        
        # Check that created_at is back to datetime
        assert isinstance(restored_response.created_at, datetime), f"Restored created_at should be datetime, got {type(restored_response.created_at)}"
        print(f"✅ Restored created_at is datetime: {restored_response.created_at}")
        
    except Exception as e:
        print(f"❌ from_dict() conversion failed: {e}")
        return False
    
    print("🎉 Datetime serialization test passed!")
    return True


def test_string_created_at_handling():
    """Test handling of created_at when it's already a string."""
    print("\n🧪 Testing string created_at handling...")
    
    # Create a response dict with string created_at
    response_dict = {
        'response': 'Test response',
        'session_id': 'test-session-456',
        'status': 'completed',
        'reasoning_trace': [],
        'tool_calls': [],
        'created_at': '2024-01-15T10:30:00Z',  # String datetime
        'processing_time_ms': 1000,
        'iterations_used': 1,
        'tools_used': 0,
        'metadata': {}
    }
    
    try:
        # Create response from dict with string created_at
        response = ReactAgentResponse.from_dict(response_dict)
        print("✅ Created response from dict with string created_at")
        
        # Check that created_at was converted to datetime
        assert isinstance(response.created_at, datetime), f"created_at should be datetime, got {type(response.created_at)}"
        print(f"✅ String created_at converted to datetime: {response.created_at}")
        
        # Test to_dict conversion
        new_dict = response.to_dict()
        print("✅ to_dict() conversion successful with string input")
        
        # Check that created_at is now a string again
        created_at_str = new_dict.get('created_at')
        assert isinstance(created_at_str, str), f"created_at in dict should be string, got {type(created_at_str)}"
        print(f"✅ created_at serialized back to string: {created_at_str}")
        
    except Exception as e:
        print(f"❌ String created_at handling failed: {e}")
        return False
    
    print("🎉 String created_at handling test passed!")
    return True


def test_error_response_datetime():
    """Test that error responses also handle datetime correctly."""
    print("\n🧪 Testing error response datetime handling...")
    
    try:
        error_response = create_error_response(
            error_message="Test error",
            session_id="error-test-session",
            error_type="test_error"
        )
        
        # Check that created_at is datetime
        assert isinstance(error_response.created_at, datetime), f"Error response created_at should be datetime, got {type(error_response.created_at)}"
        print(f"✅ Error response created_at is datetime: {error_response.created_at}")
        
        # Test to_dict conversion
        error_dict = error_response.to_dict()
        print("✅ Error response to_dict() conversion successful")
        
        # Check that created_at is string
        created_at_str = error_dict.get('created_at')
        assert isinstance(created_at_str, str), f"Error response created_at in dict should be string, got {type(created_at_str)}"
        print(f"✅ Error response created_at serialized to string: {created_at_str}")
        
        # Test JSON serialization
        json_str = json.dumps(error_dict, default=str)
        print("✅ Error response JSON serialization successful")
        
    except Exception as e:
        print(f"❌ Error response datetime handling failed: {e}")
        return False
    
    print("🎉 Error response datetime handling test passed!")
    return True


def test_edge_cases():
    """Test edge cases for datetime handling."""
    print("\n🧪 Testing datetime edge cases...")
    
    # Test with None created_at
    try:
        response_dict = {
            'response': 'Test response',
            'session_id': 'edge-case-session',
            'status': 'completed',
            'reasoning_trace': [],
            'tool_calls': [],
            'created_at': None,  # None value
            'processing_time_ms': 1000,
            'iterations_used': 1,
            'tools_used': 0,
            'metadata': {}
        }
        
        response = ReactAgentResponse.from_dict(response_dict)
        assert isinstance(response.created_at, datetime), "None created_at should be converted to datetime"
        print("✅ None created_at handled correctly")
        
    except Exception as e:
        print(f"❌ None created_at handling failed: {e}")
        return False
    
    # Test with invalid string format
    try:
        response_dict = {
            'response': 'Test response',
            'session_id': 'edge-case-session-2',
            'status': 'completed',
            'reasoning_trace': [],
            'tool_calls': [],
            'created_at': 'invalid-datetime-string',  # Invalid format
            'processing_time_ms': 1000,
            'iterations_used': 1,
            'tools_used': 0,
            'metadata': {}
        }
        
        response = ReactAgentResponse.from_dict(response_dict)
        assert isinstance(response.created_at, datetime), "Invalid created_at string should be converted to datetime"
        print("✅ Invalid created_at string handled correctly")
        
    except Exception as e:
        print(f"❌ Invalid created_at string handling failed: {e}")
        return False
    
    print("🎉 Edge cases test passed!")
    return True


if __name__ == "__main__":
    print("🚀 Starting datetime serialization fix tests...\n")
    
    success = True
    
    # Run all tests
    success &= test_datetime_serialization()
    success &= test_string_created_at_handling()
    success &= test_error_response_datetime()
    success &= test_edge_cases()
    
    if success:
        print("\n🎉 All datetime serialization tests passed! The isoformat error should be fixed.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)