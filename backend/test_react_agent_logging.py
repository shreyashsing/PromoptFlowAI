#!/usr/bin/env python3
"""
Test script for ReAct agent logging system.
Tests the comprehensive logging of reasoning steps, tool executions, and performance metrics.
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.react_agent_logger import (
    ReactAgentLogger, 
    react_agent_logger,
    CorrelationContext,
    ReasoningStep,
    ToolExecution,
    PerformanceMetrics
)


async def test_correlation_context():
    """Test correlation context creation and management."""
    print("Testing correlation context creation...")
    
    # Create correlation context
    context = react_agent_logger.create_correlation_context(
        session_id="test_session_123",
        user_id="test_user_456",
        request_id="test_request_789"
    )
    
    print(f"Created correlation context: {context.correlation_id}")
    print(f"Context data: {context.to_dict()}")
    
    # Verify context is stored
    assert context.correlation_id in react_agent_logger.active_contexts
    assert context.correlation_id in react_agent_logger.reasoning_traces
    assert context.correlation_id in react_agent_logger.tool_executions
    assert context.correlation_id in react_agent_logger.performance_metrics
    
    print("✓ Correlation context creation test passed")
    return context


async def test_reasoning_step_logging(context):
    """Test reasoning step logging."""
    print("\nTesting reasoning step logging...")
    
    # Log a reasoning step
    step_id = react_agent_logger.log_reasoning_step(
        context,
        step_number=1,
        thought="I need to analyze the user's request and determine what tools to use",
        action="analyze_request",
        action_input={"query": "test query", "context": "test context"},
        observation="Request analysis complete",
        duration_ms=150.5,
        success=True
    )
    
    print(f"Logged reasoning step: {step_id}")
    
    # Log a failed reasoning step
    error_step_id = react_agent_logger.log_reasoning_step(
        context,
        step_number=2,
        thought="Attempting to execute action but encountered an error",
        action="execute_action",
        action_input={"action": "test_action"},
        success=False,
        error_message="Test error for demonstration"
    )
    
    print(f"Logged error reasoning step: {error_step_id}")
    
    # Verify reasoning trace
    trace = react_agent_logger.get_reasoning_trace(context.correlation_id)
    assert len(trace) == 2
    assert trace[0]["step_number"] == 1
    assert trace[0]["success"] == True
    assert trace[1]["step_number"] == 2
    assert trace[1]["success"] == False
    
    print("✓ Reasoning step logging test passed")


async def test_tool_execution_logging(context):
    """Test tool execution logging."""
    print("\nTesting tool execution logging...")
    
    # Start tool execution
    execution_id = react_agent_logger.log_tool_execution_start(
        context,
        tool_name="http_connector",
        tool_input={
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": {"Authorization": "Bearer secret_token"},
            "params": {"limit": 10}
        }
    )
    
    print(f"Started tool execution: {execution_id}")
    
    # Simulate some processing time
    await asyncio.sleep(0.1)
    
    # Complete tool execution successfully
    react_agent_logger.log_tool_execution_complete(
        context,
        execution_id,
        output={"status": "success", "data": [{"id": 1, "name": "test"}]},
        retry_count=0
    )
    
    print(f"Completed tool execution: {execution_id}")
    
    # Start another tool execution that fails
    failed_execution_id = react_agent_logger.log_tool_execution_start(
        context,
        tool_name="database_connector",
        tool_input={"query": "SELECT * FROM users", "password": "secret123"}
    )
    
    # Complete with error
    react_agent_logger.log_tool_execution_complete(
        context,
        failed_execution_id,
        error="Connection timeout",
        retry_count=2
    )
    
    # Verify tool execution history
    history = react_agent_logger.get_tool_execution_history(context.correlation_id)
    assert len(history) == 2
    assert history[0]["tool_name"] == "http_connector"
    assert history[0]["success"] == True
    assert "REDACTED" in str(history[0]["tool_input"])  # Sensitive data should be redacted
    assert history[1]["tool_name"] == "database_connector"
    assert history[1]["success"] == False
    assert history[1]["retry_count"] == 2
    
    print("✓ Tool execution logging test passed")


async def test_performance_metrics(context):
    """Test performance metrics logging."""
    print("\nTesting performance metrics logging...")
    
    # Test successful operation
    async with react_agent_logger.log_performance_metrics(context, "test_operation"):
        await asyncio.sleep(0.05)  # Simulate work
        print("Performing test operation...")
    
    # Test failed operation
    try:
        async with react_agent_logger.log_performance_metrics(context, "failing_operation"):
            await asyncio.sleep(0.02)
            raise ValueError("Test error")
    except ValueError:
        pass  # Expected
    
    # Verify performance summary
    summary = react_agent_logger.get_performance_summary(context.correlation_id)
    assert summary["total_operations"] == 2
    assert summary["success_rate"] == 0.5  # 1 success, 1 failure
    assert summary["total_errors"] == 1
    assert "test_operation" in summary["operations_by_type"]
    assert "failing_operation" in summary["operations_by_type"]
    
    print(f"Performance summary: {json.dumps(summary, indent=2)}")
    print("✓ Performance metrics test passed")


async def test_authentication_logging(context):
    """Test authentication event logging."""
    print("\nTesting authentication event logging...")
    
    # Log successful authentication
    react_agent_logger.log_authentication_event(
        context,
        "user_login",
        user_id="test_user_456",
        success=True,
        additional_data={"login_method": "oauth", "provider": "google"}
    )
    
    # Log failed authentication
    react_agent_logger.log_authentication_event(
        context,
        "token_refresh",
        user_id="test_user_456",
        success=False,
        error_message="Refresh token expired",
        additional_data={"token_age_hours": 24}
    )
    
    print("✓ Authentication logging test passed")


async def test_error_logging(context):
    """Test error logging."""
    print("\nTesting error logging...")
    
    # Create test exception
    test_error = ValueError("Test error for logging demonstration")
    test_error.details = {"error_code": "TEST_001", "context": "unit_test"}
    
    # Log the error
    react_agent_logger.log_error(
        context,
        test_error,
        "test_operation",
        additional_data={"operation_id": "op_123", "retry_count": 1}
    )
    
    print("✓ Error logging test passed")


async def test_data_sanitization():
    """Test sensitive data sanitization."""
    print("\nTesting data sanitization...")
    
    # Create tool execution with sensitive data
    tool_execution = ToolExecution(
        execution_id="test_exec",
        tool_name="test_tool",
        tool_input={
            "username": "testuser",
            "password": "secret123",
            "api_key": "sk-1234567890abcdef",
            "auth_token": "bearer_token_xyz",
            "normal_data": "this should not be redacted",
            "nested": {
                "secret": "hidden_value",
                "public": "visible_value"
            }
        }
    )
    
    # Convert to dict and check sanitization
    sanitized = tool_execution.to_dict()
    
    assert sanitized["tool_input"]["password"] == "[REDACTED]"
    assert sanitized["tool_input"]["api_key"] == "[REDACTED]"
    assert sanitized["tool_input"]["auth_token"] == "[REDACTED]"
    assert sanitized["tool_input"]["normal_data"] == "this should not be redacted"
    assert sanitized["tool_input"]["nested"]["secret"] == "[REDACTED]"
    assert sanitized["tool_input"]["nested"]["public"] == "visible_value"
    
    print("✓ Data sanitization test passed")


async def test_context_cleanup():
    """Test correlation context cleanup."""
    print("\nTesting context cleanup...")
    
    # Create a context
    context = react_agent_logger.create_correlation_context(
        session_id="cleanup_test_session"
    )
    
    correlation_id = context.correlation_id
    
    # Add some data
    react_agent_logger.log_reasoning_step(
        context, 1, "Test thought", success=True
    )
    
    # Verify data exists
    assert correlation_id in react_agent_logger.active_contexts
    assert len(react_agent_logger.get_reasoning_trace(correlation_id)) == 1
    
    # Clean up context
    react_agent_logger.cleanup_context(correlation_id)
    
    # Verify data is removed
    assert correlation_id not in react_agent_logger.active_contexts
    assert len(react_agent_logger.get_reasoning_trace(correlation_id)) == 0
    
    print("✓ Context cleanup test passed")


async def main():
    """Run all logging tests."""
    print("Starting ReAct Agent Logging System Tests")
    print("=" * 50)
    
    try:
        # Test correlation context
        context = await test_correlation_context()
        
        # Test reasoning step logging
        await test_reasoning_step_logging(context)
        
        # Test tool execution logging
        await test_tool_execution_logging(context)
        
        # Test performance metrics
        await test_performance_metrics(context)
        
        # Test authentication logging
        await test_authentication_logging(context)
        
        # Test error logging
        await test_error_logging(context)
        
        # Test data sanitization
        await test_data_sanitization()
        
        # Test context cleanup
        await test_context_cleanup()
        
        # Clean up main test context
        react_agent_logger.cleanup_context(context.correlation_id)
        
        print("\n" + "=" * 50)
        print("✅ All ReAct Agent Logging Tests Passed!")
        print("\nLogging system features verified:")
        print("- Correlation context management")
        print("- Reasoning step logging with structured data")
        print("- Tool execution logging with timing")
        print("- Performance metrics collection")
        print("- Authentication event logging")
        print("- Error logging with context")
        print("- Sensitive data sanitization")
        print("- Context cleanup and memory management")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)