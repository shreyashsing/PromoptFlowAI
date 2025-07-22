"""
Integration tests for the comprehensive error handling and logging system.
Tests the complete error handling flow across all components.
"""
import pytest
import asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.core.exceptions import (
    PromptFlowException, ErrorCategory, ErrorSeverity,
    ConnectorException, ExternalAPIException, TimeoutException
)
from app.core.error_handler import global_error_handler, RetryConfig, with_retry
from app.core.error_utils import (
    handle_connector_errors, handle_external_api_errors,
    ErrorBoundary, handle_and_log_error
)
from app.core.monitoring import (
    error_monitor, alert_manager, health_checker, 
    record_error_for_monitoring, get_system_status,
    AlertManager, ErrorMonitor, HealthChecker
)
from app.services.conversational_agent import ConversationalAgent
from app.services.rag import RAGRetriever
from app.connectors.core.http_connector import HttpConnector


class TestErrorHandlingIntegration:
    """Integration tests for complete error handling system."""
    
    @pytest.mark.asyncio
    async def test_connector_error_flow(self):
        """Test complete error handling flow for connector failures."""
        # Simulate a connector that fails with retries
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        @handle_connector_errors("test_integration")
        async def failing_connector():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary network failure")
            return {"status": "success", "data": "recovered"}
        
        # Execute and verify recovery
        result = await failing_connector()
        assert result["status"] == "success"
        assert call_count == 3
        
        # Verify error was recorded for monitoring
        assert len(error_monitor.recent_errors) > 0
    
    @pytest.mark.asyncio
    async def test_external_api_error_with_monitoring(self):
        """Test external API error handling with monitoring integration."""
        # Create a fresh alert manager and error monitor for this test
        test_alert_manager = AlertManager()
        test_error_monitor = ErrorMonitor(test_alert_manager)
        
        # Create multiple API failures to trigger monitoring
        for i in range(12):  # Above threshold
            try:
                @handle_external_api_errors("test_api", retryable=False)
                async def failing_api():
                    raise TimeoutException("API timeout", timeout_duration=30.0)
                
                await failing_api()
            except Exception as e:
                # Manually record the error for monitoring since the decorator catches it
                if isinstance(e, PromptFlowException):
                    await test_error_monitor.record_error(e)
        
        # Check that alerts were generated
        active_alerts = test_alert_manager.get_active_alerts()
        error_alerts = [alert for alert in active_alerts if "Error Threshold" in alert.title]
        assert len(error_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_error_boundary_context_manager(self):
        """Test ErrorBoundary context manager with different scenarios."""
        # Test with reraise=False (error suppression)
        async with ErrorBoundary("test_operation", reraise=False) as boundary:
            raise ValueError("Test error for boundary")
        
        assert boundary.error_occurred is True
        assert boundary.error_response is not None
        assert "Test error for boundary" in boundary.error_response["message"]
        
        # Test with reraise=True (default)
        with pytest.raises(ValueError):
            async with ErrorBoundary("test_operation") as boundary:
                raise ValueError("Test error with reraise")
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self):
        """Test health monitoring with error tracking."""
        # Record some request times
        health_checker.record_request_time(0.5)
        health_checker.record_request_time(1.2)
        health_checker.record_request_time(0.8)
        
        # Generate some errors
        for _ in range(3):
            error = ConnectorException("Test error for health check")
            await record_error_for_monitoring(error)
        
        # Get system status
        status = await get_system_status()
        
        assert "health" in status
        assert "alerts" in status
        assert "logging" in status
        assert status["health"]["uptime"] > 0
    
    @pytest.mark.asyncio
    async def test_logging_integration(self, caplog):
        """Test that errors are properly logged with context."""
        # Set logging level for the error handler logger specifically
        error_handler_logger = logging.getLogger("app.core.error_handler")
        
        with caplog.at_level(logging.DEBUG, logger="app.core.error_handler"):
            context = {
                "user_id": "test_user_123",
                "operation": "test_operation",
                "request_id": "req_456"
            }
            
            error = ExternalAPIException(
                "API service unavailable",
                api_name="test_service",
                status_code=503
            )
            
            result = await handle_and_log_error(
                error,
                context=context,
                user_id="test_user_123",
                operation="test_operation"
            )
        
        # Verify the error was handled properly
        assert result["error"] is True
        assert result["error_code"] == "EXTERNAL_API_EXTERNALAPIEXCEPTION"
        assert "API service unavailable" in result["message"]
        assert result["retryable"] is True
        
        # Verify logging occurred (may be at different levels)
        # The error handler logs at WARNING level for MEDIUM severity
        relevant_records = [r for r in caplog.records if "API service unavailable" in r.message]
        assert len(relevant_records) > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker triggers after multiple failures."""
        # Generate many errors of the same type quickly
        for _ in range(15):
            error = ConnectorException("Repeated failure", connector_name="test")
            await global_error_handler.handle_error(error)
        
        # Next error should trigger circuit breaker
        error = ConnectorException("Another failure", connector_name="test")
        response = await global_error_handler.handle_error(error)
        
        assert response["error_code"] == "CIRCUIT_BREAKER_OPEN"
        assert "temporarily unavailable" in response["user_message"]
    
    @pytest.mark.asyncio
    async def test_retry_with_different_exception_types(self):
        """Test retry behavior with different exception types."""
        # Test retryable exception
        call_count_retryable = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def retryable_function():
            nonlocal call_count_retryable
            call_count_retryable += 1
            if call_count_retryable < 3:
                raise ExternalAPIException("Retryable error", retryable=True)
            return "success"
        
        result = await retryable_function()
        assert result == "success"
        assert call_count_retryable == 3
        
        # Test non-retryable exception
        call_count_non_retryable = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def non_retryable_function():
            nonlocal call_count_non_retryable
            call_count_non_retryable += 1
            raise PromptFlowException("Non-retryable error", retryable=False)
        
        with pytest.raises(PromptFlowException):
            await non_retryable_function()
        
        assert call_count_non_retryable == 1  # Should not retry
    
    @pytest.mark.asyncio
    async def test_error_categorization_and_severity(self):
        """Test that errors are properly categorized and prioritized."""
        # Create errors of different severities
        errors = [
            PromptFlowException("Low severity", severity=ErrorSeverity.LOW),
            PromptFlowException("Medium severity", severity=ErrorSeverity.MEDIUM),
            PromptFlowException("High severity", severity=ErrorSeverity.HIGH),
            PromptFlowException("Critical severity", severity=ErrorSeverity.CRITICAL)
        ]
        
        responses = []
        for error in errors:
            response = await global_error_handler.handle_error(error)
            responses.append(response)
        
        # Verify all errors were handled
        assert len(responses) == 4
        
        # Verify severity is preserved
        severities = [resp["severity"] for resp in responses]
        assert "low" in severities
        assert "medium" in severities
        assert "high" in severities
        assert "critical" in severities
    
    @pytest.mark.asyncio
    async def test_error_recovery_suggestions(self):
        """Test that appropriate recovery suggestions are provided."""
        # Test authentication error
        auth_error = PromptFlowException(
            "Authentication failed",
            category=ErrorCategory.AUTHENTICATION,
            recovery_suggestions=[
                "Check your API credentials",
                "Verify your authentication token",
                "Try logging in again"
            ]
        )
        
        response = await global_error_handler.handle_error(auth_error)
        
        assert len(response["recovery_suggestions"]) == 3
        assert "API credentials" in response["recovery_suggestions"][0]
        assert response["retryable"] is False  # Auth errors typically not retryable
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring integration."""
        # Create a fresh health checker for this test
        test_health_checker = HealthChecker()
        
        # Simulate operations with different durations
        durations = [0.1, 0.5, 1.0, 2.5, 0.3]
        
        for duration in durations:
            test_health_checker.record_request_time(duration)
        
        # Get health metrics
        metrics = await test_health_checker.get_health_metrics()
        
        expected_avg = sum(durations) / len(durations)
        assert abs(metrics.response_time_avg - expected_avg) < 0.001  # Allow for small floating point differences
        assert metrics.uptime > 0
        
        # Test health check with elevated response times
        for _ in range(10):
            test_health_checker.record_request_time(3.0)  # High response time
        
        health_status = await test_health_checker.check_health()
        assert health_status["status"] in ["degraded", "unhealthy"]
        assert len(health_status["issues"]) > 0


class TestRealWorldScenarios:
    """Test error handling in realistic scenarios."""
    
    @pytest.mark.asyncio
    async def test_workflow_execution_with_failures(self):
        """Test workflow execution with connector failures and recovery."""
        # This would test a complete workflow with some failing connectors
        # For now, we'll simulate the key error handling aspects
        
        errors_encountered = []
        
        # Simulate workflow with multiple connector calls
        connectors = ["http", "gmail", "sheets"]
        
        for connector_name in connectors:
            try:
                @handle_connector_errors(connector_name)
                async def connector_operation():
                    if connector_name == "gmail":  # Simulate gmail failure
                        raise ConnectionError("Gmail API unavailable")
                    return {"status": "success", "connector": connector_name}
                
                result = await connector_operation()
                
            except ConnectorException as e:
                errors_encountered.append(e)
                # In real workflow, this would trigger error handling
                error_response = await global_error_handler.handle_error(e)
                assert error_response["retryable"] is True
        
        # Verify that errors were properly handled
        assert len(errors_encountered) == 1
        assert errors_encountered[0].connector_name == "gmail"
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling under concurrent load."""
        async def concurrent_operation(operation_id: int):
            """Simulate concurrent operations with some failures."""
            if operation_id % 3 == 0:  # Every 3rd operation fails
                raise ExternalAPIException(f"Operation {operation_id} failed")
            return f"Success {operation_id}"
        
        # Run multiple concurrent operations
        tasks = []
        for i in range(20):
            task = asyncio.create_task(concurrent_operation(i))
            tasks.append(task)
        
        # Collect results and errors
        results = []
        errors = []
        
        for task in tasks:
            try:
                result = await task
                results.append(result)
            except Exception as e:
                error_response = await global_error_handler.handle_error(e)
                errors.append(error_response)
        
        # Verify handling
        assert len(results) > 0  # Some operations succeeded
        assert len(errors) > 0   # Some operations failed
        
        # Verify all errors were properly formatted
        for error in errors:
            assert "error" in error
            assert error["error"] is True
            assert "error_code" in error
            assert "user_message" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])