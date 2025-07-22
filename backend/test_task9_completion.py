"""
Comprehensive test to verify Task 9 - Error Handling and Logging implementation.
This test verifies all components of the error handling system are working together.
"""
import pytest
import asyncio
import logging
import time
from datetime import datetime
from unittest.mock import Mock, patch

from app.core.exceptions import (
    PromptFlowException, ErrorCategory, ErrorSeverity,
    ConnectorException, ExternalAPIException, ValidationException,
    AuthenticationException, RateLimitException, TimeoutException
)
from app.core.error_handler import (
    ErrorHandler, RetryConfig, with_retry, global_error_handler
)
from app.core.error_utils import (
    handle_connector_errors, handle_external_api_errors,
    handle_database_errors, ErrorBoundary, log_function_performance
)
from app.core.monitoring import (
    AlertManager, ErrorMonitor, HealthChecker, AlertLevel,
    error_monitor, alert_manager, health_checker,
    record_error_for_monitoring, get_system_status
)
from app.core.logging_config import init_logging, get_logger


class TestTask9Implementation:
    """Test comprehensive error handling and logging system implementation."""
    
    def test_categorized_error_types(self):
        """Test that all required error categories are implemented."""
        # Test all error categories exist
        categories = [
            ErrorCategory.USER_INPUT,
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.AUTHORIZATION,
            ErrorCategory.VALIDATION,
            ErrorCategory.CONNECTOR,
            ErrorCategory.WORKFLOW,
            ErrorCategory.SYSTEM,
            ErrorCategory.EXTERNAL_API,
            ErrorCategory.DATABASE,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.CONFIGURATION
        ]
        
        assert len(categories) == 12
        
        # Test error severity levels
        severities = [
            ErrorSeverity.LOW,
            ErrorSeverity.MEDIUM,
            ErrorSeverity.HIGH,
            ErrorSeverity.CRITICAL
        ]
        
        assert len(severities) == 4
        
        # Test specific exception types with proper categorization
        connector_exc = ConnectorException("Test", connector_name="test")
        assert connector_exc.category == ErrorCategory.CONNECTOR
        assert connector_exc.retryable is True
        
        auth_exc = AuthenticationException("Auth failed")
        assert auth_exc.category == ErrorCategory.AUTHENTICATION
        assert auth_exc.severity == ErrorSeverity.HIGH
        
        validation_exc = ValidationException("Invalid input", field="email")
        assert validation_exc.category == ErrorCategory.VALIDATION
        assert validation_exc.severity == ErrorSeverity.LOW
    
    def test_exponential_backoff_retry_logic(self):
        """Test automatic retry logic with exponential backoff."""
        config = RetryConfig(
            max_attempts=4,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        
        # Test delay calculation
        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 4.0
        assert config.calculate_delay(4) == 8.0
        
        # Test max delay cap
        config_with_cap = RetryConfig(
            base_delay=10.0,
            max_delay=15.0,
            jitter=False
        )
        assert config_with_cap.calculate_delay(3) == 15.0  # Capped
        
        # Test retry decision logic
        retryable_exc = ExternalAPIException("API error", retryable=True)
        non_retryable_exc = ValidationException("Bad input", retryable=False)
        
        assert config.should_retry(retryable_exc, 1) is True
        assert config.should_retry(retryable_exc, 4) is False  # Max attempts reached
        assert config.should_retry(non_retryable_exc, 1) is False
    
    @pytest.mark.asyncio
    async def test_retry_decorator_functionality(self):
        """Test retry decorator with different scenarios."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ExternalAPIException("Temporary failure", retryable=True)
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_comprehensive_error_logging(self, caplog):
        """Test comprehensive error logging with context."""
        with caplog.at_level(logging.WARNING):
            error = ConnectorException(
                "Database connection failed",
                connector_name="postgres",
                severity=ErrorSeverity.HIGH,
                details={"host": "localhost", "port": 5432}
            )
            
            context = {
                "user_id": "user_123",
                "operation": "fetch_data",
                "request_id": "req_456"
            }
            
            await global_error_handler.handle_error(error, context, "user_123")
        
        # Verify structured logging
        assert len(caplog.records) > 0
        log_record = caplog.records[0]
        assert "Database connection failed" in log_record.message
        assert log_record.levelno == logging.ERROR  # HIGH severity maps to ERROR
        
        # Check extra fields were added
        assert hasattr(log_record, 'error_code')
        assert hasattr(log_record, 'category')
        assert hasattr(log_record, 'severity')
    
    @pytest.mark.asyncio
    async def test_monitoring_and_alerting(self):
        """Test error monitoring and alerting system."""
        # Create a fresh alert manager for this test
        test_alert_manager = AlertManager()
        test_error_monitor = ErrorMonitor(test_alert_manager)
        
        # Generate multiple errors to trigger threshold
        for i in range(6):  # Above threshold of 5 for system errors
            error = PromptFlowException(
                f"System error {i}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM
            )
            await test_error_monitor.record_error(error)
        
        # Check that alert was created
        active_alerts = test_alert_manager.get_active_alerts()
        assert len(active_alerts) > 0
        
        # Find threshold alert
        threshold_alerts = [
            alert for alert in active_alerts
            if "Error Threshold Exceeded" in alert.title
        ]
        assert len(threshold_alerts) > 0
        
        threshold_alert = threshold_alerts[0]
        assert threshold_alert.level == AlertLevel.ERROR
        assert "system" in threshold_alert.message.lower()
    
    @pytest.mark.asyncio
    async def test_user_friendly_error_messages(self):
        """Test user-friendly error messages and recovery suggestions."""
        # Test authentication error
        auth_error = AuthenticationException("Invalid API key")
        response = await global_error_handler.handle_error(auth_error)
        
        assert response["user_message"] == "Authentication failed. Please check your credentials and try again."
        assert len(response["recovery_suggestions"]) > 0
        assert "credentials" in response["recovery_suggestions"][0].lower()
        
        # Test connector error
        connector_error = ConnectorException("Connection timeout", connector_name="Gmail")
        response = await global_error_handler.handle_error(connector_error)
        
        assert "Gmail" in response["user_message"]
        assert "configuration" in response["user_message"].lower()
        
        # Test rate limit error
        rate_limit_error = RateLimitException("Too many requests", retry_after=60)
        response = await global_error_handler.handle_error(rate_limit_error)
        
        assert "60 seconds" in response["user_message"]
        assert response["retryable"] is True
    
    @pytest.mark.asyncio
    async def test_error_boundary_context_manager(self):
        """Test ErrorBoundary for graceful error handling."""
        # Test with error suppression
        async with ErrorBoundary("test_operation", reraise=False) as boundary:
            raise ValueError("Test error")
        
        assert boundary.error_occurred is True
        assert boundary.error_response is not None
        assert boundary.error_response["error"] is True
        
        # Test with error re-raising
        with pytest.raises(ValueError):
            async with ErrorBoundary("test_operation", reraise=True) as boundary:
                raise ValueError("Test error with reraise")
    
    @pytest.mark.asyncio
    async def test_performance_logging(self):
        """Test performance logging decorator."""
        @log_function_performance("test_operation")
        async def test_function():
            await asyncio.sleep(0.1)  # Simulate work
            return "completed"
        
        with patch('app.core.error_utils.logger') as mock_logger:
            result = await test_function()
            
            assert result == "completed"
            
            # Verify performance was logged
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert "test_operation" in call_args[0][0]
            assert "completed successfully" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self):
        """Test system health monitoring."""
        # Record some request times
        health_checker.record_request_time(0.5)
        health_checker.record_request_time(1.2)
        health_checker.record_request_time(0.8)
        
        # Get health metrics
        metrics = await health_checker.get_health_metrics()
        
        assert metrics.response_time_avg == (0.5 + 1.2 + 0.8) / 3
        assert metrics.uptime > 0
        assert isinstance(metrics.timestamp, datetime)
        
        # Test health check
        health_status = await health_checker.check_health()
        
        assert "status" in health_status
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert "uptime" in health_status
        assert "metrics" in health_status
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker prevents cascading failures."""
        error_handler = ErrorHandler()
        
        # Generate many errors quickly to trigger circuit breaker
        for _ in range(15):
            error = ConnectorException("Repeated failure", connector_name="test")
            await error_handler.handle_error(error)
        
        # Next error should trigger circuit breaker
        error = ConnectorException("Another failure", connector_name="test")
        response = await error_handler.handle_error(error)
        
        assert response["error_code"] == "CIRCUIT_BREAKER_OPEN"
        assert "temporarily unavailable" in response["user_message"]
        assert response["retryable"] is True
        assert response["retry_after"] == 300
    
    @pytest.mark.asyncio
    async def test_system_status_endpoint(self):
        """Test comprehensive system status reporting."""
        # Generate some activity
        health_checker.record_request_time(1.0)
        
        error = PromptFlowException("Test error", category=ErrorCategory.SYSTEM)
        await record_error_for_monitoring(error)
        
        # Get system status
        status = await get_system_status()
        
        assert "health" in status
        assert "alerts" in status
        assert "logging" in status
        assert "timestamp" in status
        
        # Verify health section
        assert "status" in status["health"]
        assert "uptime" in status["health"]
        assert "metrics" in status["health"]
        
        # Verify alerts section
        assert "total_alerts" in status["alerts"]
        assert "active_alerts" in status["alerts"]
    
    def test_error_categorization_completeness(self):
        """Test that all error types are properly categorized."""
        # Test specific error types map to correct categories
        test_cases = [
            (ConnectorException("test"), ErrorCategory.CONNECTOR),
            (AuthenticationException("test"), ErrorCategory.AUTHENTICATION),
            (ValidationException("test"), ErrorCategory.VALIDATION),
            (ExternalAPIException("test"), ErrorCategory.EXTERNAL_API),
            (RateLimitException("test"), ErrorCategory.RATE_LIMIT),
            (TimeoutException("test"), ErrorCategory.TIMEOUT),
        ]
        
        for exception, expected_category in test_cases:
            assert exception.category == expected_category
    
    @pytest.mark.asyncio
    async def test_decorator_integration(self):
        """Test that error handling decorators work together properly."""
        call_count = 0
        
        @handle_external_api_errors("test_api", retryable=True)
        @log_function_performance("test_decorated_function")
        async def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return {"status": "success"}
        
        with patch('app.core.error_utils.logger') as mock_logger:
            result = await decorated_function()
            
            assert result["status"] == "success"
            assert call_count == 2  # Should have retried once
            
            # Verify performance logging occurred
            mock_logger.info.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])