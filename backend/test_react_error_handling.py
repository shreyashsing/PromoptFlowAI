"""
Test comprehensive error handling for ReAct agent integration.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.react_error_formatter import ReactErrorFormatter, format_react_error
from app.services.connector_tool_adapter import ConnectorToolAdapter
from app.services.react_agent_service import ReactAgentService
from app.core.exceptions import (
    AgentExecutionError, ToolExecutionError, AuthenticationException,
    ValidationException, ConnectorException, ExternalAPIException,
    RateLimitException, TimeoutException
)
from app.models.react_agent import ReactError, ReasoningStep, ToolCall


class TestReactErrorFormatter:
    """Test the comprehensive error response formatter."""
    
    @pytest.fixture
    def error_formatter(self):
        return ReactErrorFormatter()
    
    @pytest.mark.asyncio
    async def test_format_agent_execution_error(self, error_formatter):
        """Test formatting of agent execution errors."""
        error = AgentExecutionError(
            "Agent execution failed due to timeout",
            details={"timeout_seconds": 300}
        )
        
        response = await error_formatter.format_error_response(
            error=error,
            session_id="test-session-123",
            context={"user_id": "user-123", "operation": "process_request"}
        )
        
        assert response["error"] is True
        assert response["error_type"] == "agent_execution_error"
        assert "timeout" in response["user_message"].lower()
        assert len(response["suggestions"]) > 0
        assert response["retryable"] is True
        assert response["session_id"] == "test-session-123"
    
    @pytest.mark.asyncio
    async def test_format_authentication_error(self, error_formatter):
        """Test formatting of authentication errors."""
        error = AuthenticationException(
            "Invalid credentials for Google Sheets",
            details={"connector_name": "google_sheets_connector"}
        )
        
        response = await error_formatter.format_error_response(
            error=error,
            session_id="test-session-123"
        )
        
        assert response["error_type"] == "authentication_error"
        assert response["category"] == "authentication"
        assert response["severity"] == "high"
        assert len(response["recovery_actions"]) > 0
        assert any("reauth" in action.get("action", "") for action in response["recovery_actions"])
    
    @pytest.mark.asyncio
    async def test_format_tool_execution_error(self, error_formatter):
        """Test formatting of tool execution errors."""
        error = ToolExecutionError(
            "Gmail connector failed to send email",
            tool_name="gmail_connector",
            details={"error_type": "rate_limit"}
        )
        
        response = await error_formatter.format_error_response(
            error=error,
            session_id="test-session-123"
        )
        
        assert response["error_type"] == "tool_execution_error"
        assert response["category"] == "tool"
        assert "gmail_connector" in response["details"]["tool_name"]
        assert len(response["suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_format_rate_limit_error(self, error_formatter):
        """Test formatting of rate limit errors."""
        error = RateLimitException(
            "Rate limit exceeded",
            retry_after=60,
            details={"retry_after": 60}
        )
        
        response = await error_formatter.format_error_response(
            error=error,
            session_id="test-session-123"
        )
        
        assert response["error_type"] == "rate_limit_error"
        assert response["retry_after"] == 60
        assert response["retryable"] is True
        assert len(response["recovery_actions"]) > 0
        assert any("wait" in action.get("action", "") for action in response["recovery_actions"])
    
    @pytest.mark.asyncio
    async def test_format_with_reasoning_trace(self, error_formatter):
        """Test formatting with reasoning trace included."""
        error = AgentExecutionError("Agent failed during reasoning")
        
        reasoning_trace = [
            ReasoningStep(
                step_number=1,
                step_type="thought",
                thought="I need to analyze the data",
                timestamp=datetime.utcnow()
            ),
            ReasoningStep(
                step_number=2,
                step_type="action",
                action="google_sheets_connector",
                action_input={"spreadsheet_id": "123"},
                timestamp=datetime.utcnow()
            )
        ]
        
        response = await error_formatter.format_error_response(
            error=error,
            session_id="test-session-123",
            reasoning_trace=reasoning_trace
        )
        
        assert len(response["reasoning_trace"]) == 2
        assert response["reasoning_trace"][0]["step_type"] == "thought"
        assert response["reasoning_trace"][1]["step_type"] == "action"
    
    @pytest.mark.asyncio
    async def test_format_with_failed_tool_calls(self, error_formatter):
        """Test formatting with failed tool calls included."""
        error = ToolExecutionError("Tool execution failed")
        
        failed_tool_calls = [
            ToolCall(
                id="call-123",
                tool_name="gmail_connector",
                parameters={"to": "test@example.com"},
                error="Authentication failed",
                status="failed",
                started_at=datetime.utcnow()
            )
        ]
        
        response = await error_formatter.format_error_response(
            error=error,
            session_id="test-session-123",
            failed_tool_calls=failed_tool_calls
        )
        
        assert len(response["failed_tool_calls"]) == 1
        assert response["failed_tool_calls"][0]["tool_name"] == "gmail_connector"
        assert response["failed_tool_calls"][0]["error"] == "Authentication failed"
    
    @pytest.mark.asyncio
    async def test_fallback_error_response(self, error_formatter):
        """Test fallback error response when formatting fails."""
        # Create an error that will cause formatting to fail
        error = Exception("Test error")
        
        # Mock the _create_react_error method to raise an exception
        with patch.object(error_formatter, '_create_react_error', side_effect=Exception("Formatting failed")):
            response = await error_formatter.format_error_response(
                error=error,
                session_id="test-session-123"
            )
        
        assert response["error"] is True
        assert response["error_type"] == "formatting_error"
        assert "Error formatting failed" in response["message"]
        assert response["retryable"] is True


class TestConnectorToolAdapterErrorHandling:
    """Test error handling in connector tool adapter."""
    
    @pytest.fixture
    def mock_connector_class(self):
        """Create a mock connector class."""
        class MockConnector:
            def __init__(self):
                self.schema = {
                    "properties": {
                        "text": {"type": "string", "description": "Text to process"}
                    },
                    "required": ["text"]
                }
                self.description = "Mock connector for testing"
            
            async def get_auth_requirements(self):
                from app.models.connector import AuthRequirements, AuthType
                return AuthRequirements(type=AuthType.NONE, fields={}, instructions="")
            
            def get_example_params(self):
                return {"text": "example text"}
            
            def get_parameter_hints(self):
                return {"text": "Enter the text to process"}
            
            async def execute(self, params, context):
                from app.models.connector import ConnectorResult
                return ConnectorResult(success=True, data="Mock result")
        
        return MockConnector
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_validation_error(self, mock_connector_class):
        """Test tool execution with parameter validation error."""
        adapter = ConnectorToolAdapter("test_connector", mock_connector_class)
        tool = await adapter.to_langchain_tool()
        
        # Test with invalid JSON
        result = await tool.func("invalid json {")
        
        assert "❌ Parameter validation failed" in result
        assert "test_connector" in result
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_timeout(self, mock_connector_class):
        """Test tool execution with timeout."""
        # Mock connector that takes too long
        class SlowConnector(mock_connector_class):
            async def execute(self, params, context):
                await asyncio.sleep(2)  # Longer than timeout
                from app.models.connector import ConnectorResult
                return ConnectorResult(success=True, data="Should not reach here")
        
        adapter = ConnectorToolAdapter("slow_connector", SlowConnector)
        
        # Mock the timeout to be very short for testing
        with patch.object(adapter, '_get_tool_timeout', return_value=0.1):
            tool = await adapter.to_langchain_tool()
            result = await tool.func('{"text": "test"}')
        
        assert "⏱️" in result
        assert "timed out" in result
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_connector_error(self, mock_connector_class):
        """Test tool execution with connector error."""
        # Mock connector that raises ConnectorException
        class FailingConnector(mock_connector_class):
            async def execute(self, params, context):
                raise ConnectorException(
                    "Connector failed",
                    connector_name="failing_connector",
                    retryable=False
                )
        
        adapter = ConnectorToolAdapter("failing_connector", FailingConnector)
        tool = await adapter.to_langchain_tool()
        
        result = await tool.func('{"text": "test"}')
        
        assert "❌" in result
        assert "failing_connector" in result
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_authentication_error(self, mock_connector_class):
        """Test tool execution with authentication error."""
        # Mock connector that raises AuthenticationException
        class AuthFailingConnector(mock_connector_class):
            async def execute(self, params, context):
                raise AuthenticationException("Authentication failed")
        
        adapter = ConnectorToolAdapter("auth_failing_connector", AuthFailingConnector)
        
        # Mock auth context manager
        with patch('app.services.connector_tool_adapter.get_auth_context_manager') as mock_auth:
            mock_auth_manager = AsyncMock()
            mock_auth_manager.create_secure_execution_context.side_effect = AuthenticationException("Auth failed")
            mock_auth_manager.handle_authentication_failure.return_value = {
                "message": "Authentication failed",
                "suggested_action": "Please re-authenticate",
                "requires_reauth": True,
                "error_type": "auth_expired"
            }
            mock_auth.return_value = mock_auth_manager
            
            tool = await adapter.to_langchain_tool()
            result = await tool.func('{"text": "test"}')
        
        assert "🔒" in result
        assert "Authentication failed" in result
        assert "re-authenticate" in result
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_rate_limit(self, mock_connector_class):
        """Test tool execution with rate limit error."""
        # Mock connector that raises RateLimitException
        class RateLimitedConnector(mock_connector_class):
            async def execute(self, params, context):
                raise RateLimitException(
                    "Rate limit exceeded",
                    retry_after=60
                )
        
        adapter = ConnectorToolAdapter("rate_limited_connector", RateLimitedConnector)
        tool = await adapter.to_langchain_tool()
        
        result = await tool.func('{"text": "test"}')
        
        assert "🚦" in result
        assert "Rate limit exceeded" in result
        assert "60" in result or "minute" in result


class TestReactAgentServiceErrorHandling:
    """Test error handling in ReAct agent service."""
    
    @pytest.fixture
    def mock_react_service(self):
        """Create a mock ReAct agent service."""
        service = ReactAgentService()
        service._initialized = True
        service.tool_registry = Mock()
        service.memory_manager = Mock()
        service.auth_context_manager = Mock()
        service.react_agent = Mock()
        service.llm = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_infinite_loop_detection(self, mock_react_service):
        """Test infinite loop detection in agent reasoning."""
        # Mock conversation with repetitive messages
        mock_messages = []
        for i in range(10):
            msg = Mock()
            msg.content = "I need to think about this" if i % 2 == 0 else "Let me analyze the data"
            mock_messages.append(msg)
        
        # Test repetitive pattern detection
        result = await mock_react_service._check_repetitive_patterns(mock_messages)
        assert result is True  # Should detect repetitive pattern
    
    @pytest.mark.asyncio
    async def test_excessive_tool_calls_detection(self, mock_react_service):
        """Test detection of excessive tool calls without progress."""
        # Mock messages with many tool calls
        mock_messages = []
        for i in range(5):
            msg = Mock()
            msg.additional_kwargs = {
                'tool_calls': [
                    {
                        'function': {'name': 'same_tool'},
                        'id': f'call_{i}'
                    }
                ] * 4  # 4 calls per message
            }
            mock_messages.append(msg)
        
        # Test excessive tool calls detection
        result = await mock_react_service._check_excessive_tool_calls(mock_messages)
        assert result is True  # Should detect excessive tool calls
    
    @pytest.mark.asyncio
    async def test_timeout_error_response_formatting(self, mock_react_service):
        """Test timeout error response formatting."""
        response = await mock_react_service._create_timeout_error_response(
            query="Test query",
            session_id="test-session",
            user_id="test-user",
            max_iterations=10,
            timeout_seconds=300
        )
        
        assert response["status"] == "failed"
        assert response["session_id"] == "test-session"
        assert "⏱️" in response["response"]
        assert response["processing_time_ms"] == 300000
        assert len(response["reasoning_trace"]) > 0
        assert response["error"]["type"] == "agent_timeout"
    
    @pytest.mark.asyncio
    async def test_agent_error_response_formatting(self, mock_react_service):
        """Test agent error response formatting."""
        agent_error = AgentExecutionError(
            "Infinite loop detected in agent reasoning",
            user_message="The agent got stuck in a loop"
        )
        
        response = await mock_react_service._create_agent_error_response(
            query="Test query",
            session_id="test-session",
            user_id="test-user",
            max_iterations=10,
            agent_error=agent_error
        )
        
        assert response["status"] == "failed"
        assert "❌" in response["response"]
        assert "loop" in response["response"].lower()
        assert response["error"]["category"] == "agent_reasoning"
    
    @pytest.mark.asyncio
    async def test_unexpected_error_response_formatting(self, mock_react_service):
        """Test unexpected error response formatting."""
        unexpected_error = ValueError("Unexpected value error")
        
        response = await mock_react_service._create_unexpected_agent_error_response(
            query="Test query",
            session_id="test-session",
            user_id="test-user",
            max_iterations=10,
            error=unexpected_error
        )
        
        assert response["status"] == "failed"
        assert "🚨" in response["response"]
        assert response["error"]["category"] == "validation"
        assert response["metadata"]["error_type"] == "ValueError"


@pytest.mark.asyncio
async def test_format_react_error_convenience_function():
    """Test the convenience function for formatting ReAct errors."""
    error = AgentExecutionError("Test error")
    
    response = await format_react_error(
        error=error,
        session_id="test-session",
        context={"user_id": "test-user"}
    )
    
    assert response["error"] is True
    assert response["session_id"] == "test-session"
    assert response["context"]["user_id"] == "test-user"
    assert len(response["suggestions"]) > 0


if __name__ == "__main__":
    # Run basic tests
    import asyncio
    
    async def run_basic_tests():
        print("Testing ReAct error handling...")
        
        # Test error formatter
        formatter = ReactErrorFormatter()
        
        # Test with different error types
        errors_to_test = [
            AgentExecutionError("Agent timeout"),
            ToolExecutionError("Tool failed", tool_name="test_tool"),
            AuthenticationException("Auth failed"),
            ValidationException("Invalid input", field="query"),
            RateLimitException("Rate limit", retry_after=60),
            TimeoutException("Timeout", timeout_duration=30.0)
        ]
        
        for error in errors_to_test:
            response = await formatter.format_error_response(
                error=error,
                session_id="test-session"
            )
            print(f"✓ {type(error).__name__}: {response['error_type']}")
        
        print("All basic tests passed!")
    
    asyncio.run(run_basic_tests())