"""
Test script for monitoring dashboard and alerting system.
Tests the comprehensive monitoring capabilities for ReAct agent system.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.services.monitoring_service import monitoring_service, MetricsCollector, AlertingEngine
from app.core.monitoring import alert_manager, health_checker, AlertLevel
from app.services.react_agent_logger import react_agent_logger


class TestMonitoringDashboard:
    """Test suite for monitoring dashboard functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        self.test_user_id = "test_user_123"
        self.test_session_id = "test_session_456"
        self.test_correlation_id = "test_correlation_789"
        
        # Mock authentication
        self.auth_token = "test_token"
        
    def test_monitoring_dashboard_endpoint(self):
        """Test the main monitoring dashboard endpoint."""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": self.test_user_id}
            
            response = self.client.get(
                "/api/v1/monitoring/dashboard",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify dashboard structure
            assert "system_health" in data
            assert "agent_metrics" in data
            assert "active_alerts" in data
            assert "recent_errors" in data
            assert "performance_summary" in data
            assert "tool_performance" in data
            assert "user_statistics" in data
            assert "timestamp" in data
            
            # Verify system health structure
            health = data["system_health"]
            assert "status" in health
            assert "metrics" in health
            
            # Verify agent metrics structure
            metrics = data["agent_metrics"]
            assert "total_requests" in metrics
            assert "successful_requests" in metrics
            assert "failed_requests" in metrics
            assert "average_response_time_ms" in metrics
            assert "tool_usage_distribution" in metrics
    
    def test_agent_usage_metrics_endpoint(self):
        """Test the agent usage metrics endpoint."""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": self.test_user_id}
            
            response = self.client.get(
                "/api/v1/monitoring/metrics/agent-usage?hours=24",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify metrics structure
            assert "total_requests" in data
            assert "successful_requests" in data
            assert "failed_requests" in data
            assert "average_response_time_ms" in data
            assert "total_tool_executions" in data
            assert "tool_usage_distribution" in data
            assert "reasoning_step_distribution" in data
            assert "error_distribution" in data
            assert "user_activity_patterns" in data
            assert "performance_trends" in data
    
    def test_alerts_endpoint(self):
        """Test the alerts management endpoint."""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": self.test_user_id}
            
            # Test getting alerts
            response = self.client.get(
                "/api/v1/monitoring/alerts",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            assert response.status_code == 200
            alerts = response.json()
            assert isinstance(alerts, list)
    
    @pytest.mark.asyncio
    async def test_alert_creation_and_resolution(self):
        """Test alert creation and resolution workflow."""
        # Create a test alert
        alert = await alert_manager.create_alert(
            level=AlertLevel.WARNING,
            title="Test Alert",
            message="This is a test alert",
            category="test_category",
            data={"test_key": "test_value"}
        )
        
        assert alert.id is not None
        assert alert.level == AlertLevel.WARNING
        assert alert.title == "Test Alert"
        assert not alert.resolved
        
        # Test alert resolution
        success = await alert_manager.resolve_alert(alert.id)
        assert success
        
        # Verify alert is resolved
        resolved_alert = alert_manager.alerts[alert.id]
        assert resolved_alert.resolved
        assert resolved_alert.resolved_at is not None
    
    def test_reasoning_trace_analysis_endpoint(self):
        """Test the reasoning trace analysis endpoint."""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": self.test_user_id}
            
            # Create mock reasoning trace data
            with patch.object(react_agent_logger, 'get_reasoning_trace') as mock_trace:
                mock_trace.return_value = [
                    {
                        "step_id": "step_1",
                        "step_number": 1,
                        "thought": "I need to analyze this query",
                        "action": "search",
                        "success": True,
                        "duration_ms": 1500
                    },
                    {
                        "step_id": "step_2", 
                        "step_number": 2,
                        "thought": "Now I'll process the results",
                        "action": "process",
                        "success": True,
                        "duration_ms": 800
                    }
                ]
                
                with patch.object(react_agent_logger, 'get_tool_execution_history') as mock_tools:
                    mock_tools.return_value = [
                        {
                            "execution_id": "exec_1",
                            "tool_name": "search_tool",
                            "success": True,
                            "duration_ms": 1200
                        }
                    ]
                    
                    with patch.object(react_agent_logger, 'get_performance_summary') as mock_perf:
                        mock_perf.return_value = {
                            "total_operations": 2,
                            "total_duration_ms": 2300,
                            "success_rate": 1.0
                        }
                        
                        response = self.client.get(
                            f"/api/v1/monitoring/reasoning-trace/{self.test_correlation_id}/analysis",
                            headers={"Authorization": f"Bearer {self.auth_token}"}
                        )
                        
                        assert response.status_code == 200
                        analysis = response.json()
                        
                        # Verify analysis structure
                        assert "correlation_id" in analysis
                        assert "total_steps" in analysis
                        assert "successful_steps" in analysis
                        assert "failed_steps" in analysis
                        assert "total_duration_ms" in analysis
                        assert "average_step_duration_ms" in analysis
                        assert "tools_used" in analysis
                        assert "reasoning_patterns" in analysis
                        assert "performance_issues" in analysis
                        assert "recommendations" in analysis
                        
                        assert analysis["correlation_id"] == self.test_correlation_id
                        assert analysis["total_steps"] == 2
                        assert analysis["successful_steps"] == 2
                        assert analysis["failed_steps"] == 0
    
    def test_tool_performance_metrics_endpoint(self):
        """Test the tool performance metrics endpoint."""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": self.test_user_id}
            
            response = self.client.get(
                "/api/v1/monitoring/performance/tools?hours=24",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify tool performance structure
            assert isinstance(data, dict)
            
            # Check for expected tool entries
            expected_tools = ["gmail_connector", "google_sheets_connector", "perplexity_connector", "text_summarizer_connector"]
            for tool in expected_tools:
                if tool in data:
                    tool_data = data[tool]
                    assert "total_executions" in tool_data
                    assert "successful_executions" in tool_data
                    assert "failed_executions" in tool_data
                    assert "average_duration_ms" in tool_data
                    assert "success_rate" in tool_data
                    assert "common_errors" in tool_data
    
    def test_alert_configuration_endpoint(self):
        """Test the alert configuration endpoint."""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": self.test_user_id}
            
            config_data = {
                "error_rate_threshold": 0.15,
                "response_time_threshold": 6.0,
                "tool_failure_threshold": 8,
                "reasoning_loop_threshold": 25,
                "enabled": True
            }
            
            response = self.client.post(
                "/api/v1/monitoring/alerts/configure",
                json=config_data,
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            assert response.status_code == 200
            result = response.json()
            
            assert "message" in result
            assert "configuration" in result
            assert result["configuration"]["error_rate_threshold"] == 0.15
            assert result["configuration"]["response_time_threshold"] == 6.0
    
    def test_detailed_health_check_endpoint(self):
        """Test the detailed health check endpoint."""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": self.test_user_id}
            
            with patch('app.services.react_agent_service.get_react_agent_service') as mock_service:
                mock_agent_service = Mock()
                mock_agent_service._initialized = True
                mock_agent_service.get_available_tools = AsyncMock(return_value=[])
                mock_agent_service.conversation_manager.active_sessions = {}
                mock_service.return_value = mock_agent_service
                
                response = self.client.get(
                    "/api/v1/monitoring/health/detailed",
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify detailed health structure
                assert "overall_status" in data
                assert "timestamp" in data
                assert "health_metrics" in data
                assert "system_status" in data
                assert "logging_stats" in data
                assert "react_agent_status" in data
                assert "alert_summary" in data
                
                # Verify health metrics
                health_metrics = data["health_metrics"]
                assert "error_rate" in health_metrics
                assert "warning_rate" in health_metrics
                assert "avg_response_time" in health_metrics
                assert "uptime_seconds" in health_metrics


class TestMetricsCollector:
    """Test suite for metrics collection functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.collector = MetricsCollector()
        self.test_user_id = "test_user_123"
        self.test_session_id = "test_session_456"
        self.test_correlation_id = "test_correlation_789"
    
    def test_request_tracking(self):
        """Test request start and completion tracking."""
        # Record request start
        self.collector.record_request_start(
            self.test_correlation_id,
            self.test_user_id,
            self.test_session_id
        )
        
        assert self.collector.current_metrics.request_count == 1
        assert self.collector.current_metrics.active_sessions == 1
        assert self.test_correlation_id in self.collector.active_correlation_ids
        
        # Record successful completion
        self.collector.record_request_completion(
            self.test_correlation_id,
            self.test_user_id,
            success=True,
            response_time=2.5,
            tools_used=["gmail_connector", "perplexity_connector"],
            reasoning_steps=5
        )
        
        assert self.collector.current_metrics.success_count == 1
        assert self.collector.current_metrics.error_count == 0
        assert self.collector.current_metrics.total_response_time == 2.5
        assert self.collector.current_metrics.tool_execution_count == 2
        assert self.collector.current_metrics.reasoning_step_count == 5
        assert self.test_correlation_id not in self.collector.active_correlation_ids
    
    def test_tool_execution_tracking(self):
        """Test tool execution tracking."""
        self.collector.record_tool_execution(
            "gmail_connector",
            success=True,
            duration=1.2
        )
        
        tool_metrics = self.collector.tool_metrics["gmail_connector"]
        assert tool_metrics.tool_execution_count == 1
        assert tool_metrics.success_count == 1
        assert tool_metrics.error_count == 0
        assert tool_metrics.total_response_time == 1.2
        
        # Record failed execution
        self.collector.record_tool_execution(
            "gmail_connector",
            success=False,
            duration=0.8,
            error_type="authentication_error"
        )
        
        assert tool_metrics.tool_execution_count == 2
        assert tool_metrics.success_count == 1
        assert tool_metrics.error_count == 1
        assert tool_metrics.total_response_time == 2.0
    
    def test_session_management(self):
        """Test session tracking."""
        # Start session
        self.collector.record_request_start(
            self.test_correlation_id,
            self.test_user_id,
            self.test_session_id
        )
        
        assert self.collector.current_metrics.active_sessions == 1
        assert self.test_session_id in self.collector.session_start_times
        
        # End session
        self.collector.record_session_end(self.test_session_id)
        
        assert self.collector.current_metrics.active_sessions == 0
        assert self.test_session_id not in self.collector.session_start_times
    
    def test_metrics_summary(self):
        """Test metrics summary generation."""
        # Add some test data
        self.collector.record_request_start(self.test_correlation_id, self.test_user_id, self.test_session_id)
        self.collector.record_request_completion(
            self.test_correlation_id, self.test_user_id, True, 2.0, ["gmail_connector"], 3
        )
        
        summary = self.collector.get_metrics_summary()
        
        assert "overall" in summary
        assert "tools" in summary
        assert "users" in summary
        
        overall = summary["overall"]
        assert overall["request_count"] == 1
        assert overall["success_rate"] == 1.0
        assert overall["error_rate"] == 0.0
        assert overall["average_response_time"] == 2.0


class TestAlertingEngine:
    """Test suite for alerting engine functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.collector = MetricsCollector()
        self.alerting_engine = AlertingEngine(self.collector)
    
    @pytest.mark.asyncio
    async def test_error_rate_alerting(self):
        """Test error rate alerting."""
        # Simulate high error rate
        for i in range(15):
            correlation_id = f"test_correlation_{i}"
            self.collector.record_request_start(correlation_id, "test_user", "test_session")
            success = i < 5  # 5 successes, 10 failures = 66% error rate
            self.collector.record_request_completion(
                correlation_id, "test_user", success, 1.0, [], 1
            )
        
        # Check alerts
        await self.alerting_engine.check_alerts()
        
        # Verify alert was created
        active_alerts = alert_manager.get_active_alerts()
        error_rate_alerts = [alert for alert in active_alerts if alert.category == "high_error_rate"]
        assert len(error_rate_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_response_time_alerting(self):
        """Test response time alerting."""
        # Simulate high response time
        correlation_id = "test_correlation_slow"
        self.collector.record_request_start(correlation_id, "test_user", "test_session")
        self.collector.record_request_completion(
            correlation_id, "test_user", True, 10.0, [], 1  # 10 second response time
        )
        
        # Check alerts
        await self.alerting_engine.check_alerts()
        
        # Verify alert was created
        active_alerts = alert_manager.get_active_alerts()
        response_time_alerts = [alert for alert in active_alerts if alert.category == "high_response_time"]
        assert len(response_time_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_tool_failure_alerting(self):
        """Test tool failure rate alerting."""
        # Simulate high tool failure rate
        for i in range(10):
            self.collector.record_tool_execution(
                "test_tool",
                success=i < 2,  # 2 successes, 8 failures = 80% failure rate
                duration=1.0,
                error_type="test_error" if i >= 2 else None
            )
        
        # Check alerts
        await self.alerting_engine.check_alerts()
        
        # Verify alert was created
        active_alerts = alert_manager.get_active_alerts()
        tool_failure_alerts = [alert for alert in active_alerts if "tool_failure" in alert.category]
        assert len(tool_failure_alerts) > 0
    
    def test_threshold_updates(self):
        """Test updating alert thresholds."""
        new_thresholds = {
            "error_rate": 0.2,
            "response_time": 8.0
        }
        
        self.alerting_engine.update_thresholds(new_thresholds)
        
        assert self.alerting_engine.alert_thresholds["error_rate"] == 0.2
        assert self.alerting_engine.alert_thresholds["response_time"] == 8.0


def run_monitoring_tests():
    """Run all monitoring tests."""
    print("🔍 Testing Monitoring Dashboard and Alerting System...")
    
    # Run the tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])


if __name__ == "__main__":
    run_monitoring_tests()