#!/usr/bin/env python3
"""
Test script to verify that error responses maintain consistent structure with success responses.
This addresses requirement 3.3: Implement consistent error response formatting.
"""

import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.models.react_response_models import (
    create_success_response, create_error_response, 
    create_reasoning_step, create_tool_call,
    ReactAgentResponse, ReasoningStep, ToolCall
)


def test_response_structure_consistency():
    """Test that success and error responses have consistent structure."""
    print("🧪 Testing response structure consistency...")
    
    # Create a success response
    success_response = create_success_response(
        response="Task completed successfully",
        session_id="test-session-123",
        reasoning_trace=[
            create_reasoning_step(1, "thought", "I need to process this request"),
            create_reasoning_step(2, "action", "Using test tool"),
            create_reasoning_step(3, "observation", "Tool executed successfully")
        ],
        tool_calls=[
            create_tool_call("test_tool", {"param": "value"}, {"result": "success"})
        ],
        processing_time_ms=1500,
        iterations_used=3
    )
    
    # Create an error response
    error_response = create_error_response(
        error_message="Test error occurred",
        session_id="test-session-123",
        error_type="test_error",
        user_message="A test error occurred while processing your request",
        reasoning_trace=[
            create_reasoning_step(1, "thought", "Starting to process request"),
            create_reasoning_step(2, "error", "Test error occurred")
        ],
        failed_tool_calls=[
            create_tool_call("test_tool", {"param": "value"}, error="Test error")
        ],
        processing_time_ms=500
    )
    
    # Convert to dictionaries for comparison
    success_dict = success_response.to_dict()
    error_dict = error_response.to_dict()
    
    print(f"✅ Success response structure: {list(success_dict.keys())}")
    print(f"✅ Error response structure: {list(error_dict.keys())}")
    
    # Check that both responses have the same top-level keys (except error-specific ones)
    common_keys = {
        'response', 'session_id', 'status', 'reasoning_trace', 'tool_calls',
        'processing_time_ms', 'iterations_used', 'tools_used', 'metadata'
    }
    
    success_keys = set(success_dict.keys())
    error_keys = set(error_dict.keys())
    
    missing_in_success = common_keys - success_keys
    missing_in_error = common_keys - error_keys
    
    if missing_in_success:
        print(f"❌ Missing keys in success response: {missing_in_success}")
        return False
    
    if missing_in_error:
        print(f"❌ Missing keys in error response: {missing_in_error}")
        return False
    
    print("✅ Both responses have all required common keys")
    
    # Check reasoning trace structure
    success_trace = success_dict['reasoning_trace']
    error_trace = error_dict['reasoning_trace']
    
    if not success_trace or not error_trace:
        print("❌ Reasoning traces are empty")
        return False
    
    # Check that reasoning steps have step_number attribute
    for i, step in enumerate(success_trace):
        if 'step_number' not in step:
            print(f"❌ Success reasoning step {i} missing step_number")
            return False
        if step['step_number'] != i + 1:
            print(f"❌ Success reasoning step {i} has incorrect step_number: {step['step_number']}")
            return False
    
    for i, step in enumerate(error_trace):
        if 'step_number' not in step:
            print(f"❌ Error reasoning step {i} missing step_number")
            return False
        if step['step_number'] != i + 1:
            print(f"❌ Error reasoning step {i} has incorrect step_number: {step['step_number']}")
            return False
    
    print("✅ All reasoning steps have correct step_number attributes")
    
    # Check tool calls structure
    success_tools = success_dict['tool_calls']
    error_tools = error_dict['tool_calls']
    
    if success_tools:
        for i, tool_call in enumerate(success_tools):
            required_fields = {'tool_name', 'parameters', 'execution_time', 'timestamp'}
            missing_fields = required_fields - set(tool_call.keys())
            if missing_fields:
                print(f"❌ Success tool call {i} missing fields: {missing_fields}")
                return False
    
    if error_tools:
        for i, tool_call in enumerate(error_tools):
            required_fields = {'tool_name', 'parameters', 'execution_time', 'timestamp'}
            missing_fields = required_fields - set(tool_call.keys())
            if missing_fields:
                print(f"❌ Error tool call {i} missing fields: {missing_fields}")
                return False
    
    print("✅ All tool calls have required fields")
    
    # Test JSON serialization
    try:
        success_json = json.dumps(success_dict, default=str)
        error_json = json.dumps(error_dict, default=str)
        print("✅ Both responses can be serialized to JSON")
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False
    
    print("🎉 All response structure consistency tests passed!")
    return True


def test_step_number_attribute_fix():
    """Test that the step_number attribute error is fixed."""
    print("\n🧪 Testing step_number attribute fix...")
    
    # Create reasoning steps
    steps = [
        create_reasoning_step(1, "thought", "First thought"),
        create_reasoning_step(2, "action", "Take action"),
        create_reasoning_step(3, "observation", "Observe result")
    ]
    
    # Test that each step has step_number attribute
    for i, step in enumerate(steps):
        if not hasattr(step, 'step_number'):
            print(f"❌ Step {i} missing step_number attribute")
            return False
        
        if step.step_number != i + 1:
            print(f"❌ Step {i} has incorrect step_number: {step.step_number}")
            return False
        
        # Test dictionary conversion
        step_dict = step.to_dict()
        if 'step_number' not in step_dict:
            print(f"❌ Step {i} dictionary missing step_number")
            return False
    
    print("✅ All reasoning steps have correct step_number attributes")
    
    # Test response with these steps
    response = create_success_response(
        response="Test response",
        session_id="test-session",
        reasoning_trace=steps
    )
    
    response_dict = response.to_dict()
    trace = response_dict['reasoning_trace']
    
    for i, step_dict in enumerate(trace):
        if 'step_number' not in step_dict:
            print(f"❌ Response trace step {i} missing step_number")
            return False
        
        # This should not raise AttributeError
        try:
            step_number = step_dict['step_number']
            print(f"✅ Step {i} step_number: {step_number}")
        except KeyError:
            print(f"❌ Step {i} step_number access failed")
            return False
    
    print("🎉 step_number attribute fix test passed!")
    return True


def test_frontend_compatibility():
    """Test that responses are compatible with frontend expectations."""
    print("\n🧪 Testing frontend compatibility...")
    
    # Create a response similar to what the frontend expects
    response = create_success_response(
        response="I've completed your request successfully.",
        session_id="frontend-test-session",
        reasoning_trace=[
            create_reasoning_step(1, "thought", "I need to analyze the user's request"),
            create_reasoning_step(2, "action", "Using the appropriate tool"),
            create_reasoning_step(3, "observation", "Tool returned successful result"),
            create_reasoning_step(4, "final_answer", "Providing the final response")
        ],
        tool_calls=[
            create_tool_call(
                "example_tool", 
                {"query": "test query"}, 
                {"data": "example result", "status": "success"},
                execution_time=1200
            )
        ],
        processing_time_ms=2500,
        iterations_used=4
    )
    
    response_dict = response.to_dict()
    
    # Test that frontend can access reasoning trace without errors
    reasoning_trace = response_dict.get('reasoning_trace', [])
    if not reasoning_trace:
        print("❌ No reasoning trace in response")
        return False
    
    for step in reasoning_trace:
        # These are the fields the frontend expects to access
        try:
            step_number = step['step_number']  # This was causing the original error
            step_type = step.get('step_type', 'unknown')
            content = step.get('content', '')
            timestamp = step.get('timestamp', '')
            
            print(f"✅ Step {step_number}: {step_type} - {content[:50]}...")
            
        except KeyError as e:
            print(f"❌ Frontend compatibility error: {e}")
            return False
    
    # Test tool calls access
    tool_calls = response_dict.get('tool_calls', [])
    for tool_call in tool_calls:
        try:
            tool_name = tool_call['tool_name']
            parameters = tool_call.get('parameters', {})
            result = tool_call.get('result')
            execution_time = tool_call.get('execution_time', 0)
            
            print(f"✅ Tool: {tool_name} - {execution_time}ms")
            
        except KeyError as e:
            print(f"❌ Tool call compatibility error: {e}")
            return False
    
    print("🎉 Frontend compatibility test passed!")
    return True


if __name__ == "__main__":
    print("🚀 Starting response structure consistency tests...\n")
    
    success = True
    
    # Run all tests
    success &= test_response_structure_consistency()
    success &= test_step_number_attribute_fix()
    success &= test_frontend_compatibility()
    
    if success:
        print("\n🎉 All tests passed! Response structure is consistent and frontend-compatible.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)