"""
Tests for the comprehensive error handling and logging system.
"""
import pytest
import asyncio
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.core.exceptions import (
    PromptFlowException, ErrorCategory, ErrorSeverity,
    ConnectorException, AuthenticationException, ValidationException,
    ExternalAPIException, RateLimitException, TimeoutException
)
from app.core.error_handler import (
    ErrorHandler, RetryConfig, with_retry, with_error_handling,
    global_error_handler
)
from app.core.error_utils import (
    handle_connector_errors, handle_external_api_errors,
    handle_database_errors, ErrorBoundary
)
from app.core.monitoring import (
    AlertManager, ErrorMonitor, HealthChecker, AlertLevel
)


class TestPromptFlowException:
    """Test the enhanced PromptFlowException class."""
    
    def test_basic_exception_creation(self):
        """Test basic exception creation with defaults."""
        exc = PromptFlowException("Test error")
        
        assert exc.message == "Test error"
        assert exc.category == ErrorCategory.SYSTEM
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.error_code == "SYSTEM_PROMPTFLOWEXCEPTION"
        assert exc.user_message == "An error occurred while processing your request. Please try again."
        assert exc.retryable is False
        assert isinstance(exc.timestamp, datetime)
    
    def test_exception_with_custom_parameters(self):
        """Test exception creation with custom parameters."""
        details = {"key": "value"}
        recovery_suggestions = ["Try again", "Check configuration"]
        
        exc = ConnectorException(
            message="Connector failed",
            connector_name="test_connector",
            category=ErrorCategory.CONNECTOR,
            severity=ErrorSeverity.HIGH,
            details=details,
            recovery_suggestions=recovery_suggestions,
            retryable=True
        )
        
        assert exc.message == "Connector failed"
        assert exc.category == ErrorCategory.CONNECTOR
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.retryable is True
        assert exc.details["connector_name"] == "test_connector"
        assert exc.recovery_suggestions == recovery_suggestions
    
    def test_exception_to_dict(self):
        """Test exception serialization to dictionary."""
        exc = ValidationException(
            message="Invalid input",
            field="email",
            details={"field": "email", "value": "invalid"}
        )
        
        result = exc.to_dict()
        
        assert result["error_code"] == "VALIDATION_VALIDATIONEXCEPTION"
        assert result["message"] == "Invalid input"
        assert result["category"] == "validation"
        assert result["severity"] == "low"
        assert result["details"]["field"] == "email"
        assert "timestamp" in result


class TestRetryConfig:
    """Test retry configuration and logic."""
    
    def test_default_retry_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_delay_calculation(self):
        """Test delay calculation with exponential backoff."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 4.0
    
    def test_delay_with_max_limit(self):
        """Test delay calculation with maximum limit."""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, jitter=False)
        
        assert config.calculate_delay(1) == 10.0
        assert config.calculate_delay(2) == 15.0  # Capped at max_delay
        assert config.calculate_delay(3) == 15.0  # Still capped
    
    def test_should_retry_logic(self):
        """Test retry decision logic."""
        config = RetryConfig(max_attempts=3)
        
        retryable_exc = ConnectorException("Test", retryable=True)
        non_retryable_exc = ValidationException("Test", retryable=False)
        
        # Should retry retryable exceptions within attempt limit
        assert config.should_retry(retryable_exc, 1) is True
        assert config.should_retry(retryable_exc, 2) is True
        
        # Should not retry beyond max attempts
        assert config.should_retry(retryable_exc, 3) is False
        
        # Should not retry non-retryable exceptions
        assert config.should_retry(non_retryable_exc, 1) is False


class TestErrorHandler:
    """Test the ErrorHandler class."""
    
    @pytest.fixture
    def error_handler(self):
        """Create an ErrorHandler instance for testing."""
        return ErrorHandler()
    
    @pytest.mark.asyncio
    async def test_handle_promptflow_exception(self, error_handler):
        """Test handling of PromptFlowException."""
        exc = ConnectorException("Test connector error", connector_name="test")
        
        result = await error_handler.handle_error(exc)
        
        assert result["error"] is True
        assert result["error_code"] == exc.error_code
        assert result["message"] == exc.message
        assert result["user_message"] == exc.user_message
        assert result["retryable"] is True
    
    @pytest.mark.asyncio
    async def test_handle_generic_exception(self, error_handler):
        """Test handling of generic exceptions."""
        exc = ValueError("Generic error")
        
        result = await error_handler.handle_error(exc)
        
        assert result["error"] is True
        assert result["category"] == "validation"
        assert "Generic error" in result["message"]
    
    @pytest.mark.asyncio
    async def test_error_tracking(self, error_handler):
        """Test error tracking and counting."""
        exc = ConnectorException("Test error")
        
        # Handle the same error multiple times
        for _ in range(5):
            await error_handler.handle_error(exc)
        
        error_key = f"{exc.category.value}_{exc.__class__.__name__}"
        assert error_handler.error_counts[error_key] == 5
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self, error_handler):
        """Test circuit breaker functionality."""
        exc = ConnectorException("Test error")
        
        # Trigger many errors quickly
        for _ in range(15):
            await error_handler.handle_error(exc)
        
        # Next error should trigger circuit breaker
        result = await error_handler.handle_error(exc)
        assert result["error_code"] == "CIRCUIT_BREAKER_OPEN"


class TestRetryDecorator:
    """Test the retry decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_retry(self):
        """Test successful operation after retries."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectorException("Temporary failure", retryable=True)
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=2, base_delay=0.01))
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectorException("Always fails", retryable=True)
        
        with pytest.raises(ConnectorException):
            await always_failing_function()
        
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def non_retryable_function():
            nonlocal call_count
            call_count += 1
            raise ValidationException("Not retryable", retryable=False)
        
        with pytest.raises(ValidationException):
            await non_retryable_function()
        
        assert call_count == 1  # Should not retry


class TestErrorUtils:
    """Test error utility decorators and functions."""
    
    @pytest.mark.asyncio
    async def test_connector_error_decorator(self):
        """Test connector error handling decorator."""
        @handle_connector_errors("test_connector")
        async def failing_connector():
            raise ValueError("Connection failed")
        
        with pytest.raises(ConnectorException) as exc_info:
            await failing_connector()
        
        assert "test_connector" in str(exc_info.value)
        assert exc_info.value.connector_name == "test_connector"
    
    @pytest.mark.asyncio
    async def test_external_api_error_decorator(self):
        """Test external API error handling decorator."""
        call_count = 0
        
        @handle_external_api_errors("test_api", retryable=True)
        async def failing_api():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("API unavailable")
            return "success"
        
        result = await failing_api()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_error_boundary_context_manager(self):
        """Test ErrorBoundary context manager."""
        async with ErrorBoundary("test_operation", reraise=False) as boundary:
            raise ValueError("Test error")
        
        assert boundary.error_occurred is True
        assert boundary.error_response is not None
        assert boundary.error_response["error"] is True


class TestMonitoring:
    """Test monitoring and alerting functionality."""
    
    @pytest.fixture
    def alert_manager(self):
        """Create an AlertManager instance for testing."""
        return AlertManager()
    
    @pytest.fixture
    def health_checker(self):
        """Create a HealthChecker instance for testing."""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_alert_creation(self, alert_manager):
        """Test alert creation and handling."""
        alert = await alert_manager.create_alert(
            level=AlertLevel.ERROR,
            title="Test Alert",
            message="This is a test alert",
            category="test",
            data={"key": "value"}
        )
        
        assert alert.level == AlertLevel.ERROR
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.category == "test"
        assert alert.data["key"] == "value"
        assert not alert.resolved
    
    @pytest.mark.asyncio
    async def test_alert_resolution(self, alert_manager):
        """Test alert resolution."""
        alert = await alert_manager.create_alert(
            level=AlertLevel.WARNING,
            title="Test Alert",
            message="Test message",
            category="test"
        )
        
        resolved = await alert_manager.resolve_alert(alert.id)
        assert resolved is True
        assert alert.resolved is True
        assert alert.resolved_at is not None
    
    def test_health_checker_request_timing(self, health_checker):
        """Test request time recording."""
        health_checker.record_request_time(1.5)
        health_checker.record_request_time(2.0)
        health_checker.record_request_time(0.5)
        
        assert len(health_checker.request_times) == 3
        assert 1.5 in health_checker.request_times
    
    @pytest.mark.asyncio
    async def test_health_metrics(self, health_checker):
        """Test health metrics calculation."""
        # Record some request times
        health_checker.record_request_time(1.0)
        health_checker.record_request_time(2.0)
        
        metrics = await health_checker.get_health_metrics()
        
        assert metrics.response_time_avg == 1.5
        assert metrics.uptime > 0
        assert isinstance(metrics.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_error_monitor(self):
        """Test error monitoring and threshold detection."""
        alert_manager = AlertManager()
        error_monitor = ErrorMonitor(alert_manager)
        
        # Create multiple errors to trigger threshold
        for _ in range(6):  # Above threshold of 5 for system errors
            error = PromptFlowException(
                "System error",
                category=ErrorCategory.SYSTEM
            )
            await error_monitor.record_error(error)
        
        # Should have created an alert
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) > 0
        
        # Find the threshold alert
        threshold_alerts = [
            alert for alert in active_alerts
            if "Error Threshold Exceeded" in alert.title
        ]
        assert len(threshold_alerts) > 0


class TestIntegration:
    """Integration tests for the complete error handling system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_error_handling(self):
        """Test complete error handling flow."""
        # Simulate a connector operation that fails and gets retried
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        @handle_connector_errors("integration_test")
        async def integration_test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return {"status": "success", "data": "test_data"}
        
        result = await integration_test_function()
        
        assert result["status"] == "success"
        assert result["data"] == "test_data"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_logging_integration(self, caplog):
        """Test that errors are properly logged."""
        with caplog.at_level(logging.ERROR):
            error = ConnectorException(
                "Test logging error",
                connector_name="test_connector",
                severity=ErrorSeverity.HIGH
            )
            
            await global_error_handler.handle_error(error)
        
        # Check that error was logged
        assert len(caplog.records) > 0
        log_record = caplog.records[0]
        assert "Test logging error" in log_record.message
        assert log_record.levelno == logging.ERROR


if __name__ == "__main__":
    pytest.main([__file__])