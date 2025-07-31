"""
Background monitoring service for ReAct agent system.
Handles continuous metrics collection, alerting, and performance monitoring.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
import json
import time
from collections import defaultdict, deque

from app.core.monitoring import (
    alert_manager, error_monitor, health_checker, AlertLevel,
    record_error_for_monitoring
)
from app.services.react_agent_logger import react_agent_logger
from app.core.logging_config import error_count_handler
from app.core.exceptions import PromptFlowException, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for ReAct agent operations."""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_response_time: float = 0.0
    tool_execution_count: int = 0
    reasoning_step_count: int = 0
    active_sessions: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.success_count / self.request_count if self.request_count > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return self.error_count / self.request_count if self.request_count > 0 else 0.0
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        return self.total_response_time / self.request_count if self.request_count > 0 else 0.0


class MetricsCollector:
    """Collects and aggregates metrics from various sources."""
    
    def __init__(self):
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.current_metrics = AgentPerformanceMetrics()
        self.tool_metrics: Dict[str, AgentPerformanceMetrics] = defaultdict(AgentPerformanceMetrics)
        self.user_metrics: Dict[str, AgentPerformanceMetrics] = defaultdict(AgentPerformanceMetrics)
        self.session_start_times: Dict[str, datetime] = {}
        self.active_correlation_ids: Set[str] = set()
        
    def record_request_start(self, correlation_id: str, user_id: str, session_id: str):
        """Record the start of a request."""
        self.current_metrics.request_count += 1
        self.user_metrics[user_id].request_count += 1
        self.active_correlation_ids.add(correlation_id)
        
        if session_id not in self.session_start_times:
            self.session_start_times[session_id] = datetime.utcnow()
            self.current_metrics.active_sessions += 1
    
    def record_request_completion(
        self,
        correlation_id: str,
        user_id: str,
        success: bool,
        response_time: float,
        tools_used: List[str],
        reasoning_steps: int
    ):
        """Record the completion of a request."""
        if success:
            self.current_metrics.success_count += 1
            self.user_metrics[user_id].success_count += 1
        else:
            self.current_metrics.error_count += 1
            self.user_metrics[user_id].error_count += 1
        
        self.current_metrics.total_response_time += response_time
        self.current_metrics.reasoning_step_count += reasoning_steps
        self.user_metrics[user_id].total_response_time += response_time
        self.user_metrics[user_id].reasoning_step_count += reasoning_steps
        
        # Record tool usage
        for tool_name in tools_used:
            self.current_metrics.tool_execution_count += 1
            self.tool_metrics[tool_name].request_count += 1
            self.user_metrics[user_id].tool_execution_count += 1
            
            if success:
                self.tool_metrics[tool_name].success_count += 1
            else:
                self.tool_metrics[tool_name].error_count += 1
        
        self.active_correlation_ids.discard(correlation_id)
        
        # Store metric point
        self._store_metric_point("response_time", response_time, {
            "user_id": user_id,
            "success": success,
            "tools_used": tools_used,
            "reasoning_steps": reasoning_steps
        })
    
    def record_tool_execution(
        self,
        tool_name: str,
        success: bool,
        duration: float,
        error_type: Optional[str] = None
    ):
        """Record a tool execution."""
        tool_metric = self.tool_metrics[tool_name]
        tool_metric.tool_execution_count += 1
        tool_metric.total_response_time += duration
        
        if success:
            tool_metric.success_count += 1
        else:
            tool_metric.error_count += 1
        
        self._store_metric_point(f"tool_{tool_name}_duration", duration, {
            "success": success,
            "error_type": error_type
        })
    
    def record_session_end(self, session_id: str):
        """Record the end of a session."""
        if session_id in self.session_start_times:
            session_duration = (datetime.utcnow() - self.session_start_times[session_id]).total_seconds()
            del self.session_start_times[session_id]
            self.current_metrics.active_sessions = max(0, self.current_metrics.active_sessions - 1)
            
            self._store_metric_point("session_duration", session_duration, {
                "session_id": session_id
            })
    
    def _store_metric_point(self, metric_name: str, value: float, metadata: Dict[str, Any]):
        """Store a metric point in the history."""
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            metadata=metadata
        )
        self.metrics_history[metric_name].append(point)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        return {
            "overall": {
                "request_count": self.current_metrics.request_count,
                "success_rate": self.current_metrics.success_rate,
                "error_rate": self.current_metrics.error_rate,
                "average_response_time": self.current_metrics.average_response_time,
                "active_sessions": self.current_metrics.active_sessions,
                "tool_executions": self.current_metrics.tool_execution_count,
                "reasoning_steps": self.current_metrics.reasoning_step_count
            },
            "tools": {
                tool_name: {
                    "request_count": metrics.request_count,
                    "success_rate": metrics.success_rate,
                    "error_rate": metrics.error_rate,
                    "average_response_time": metrics.average_response_time
                }
                for tool_name, metrics in self.tool_metrics.items()
            },
            "users": {
                user_id: {
                    "request_count": metrics.request_count,
                    "success_rate": metrics.success_rate,
                    "average_response_time": metrics.average_response_time
                }
                for user_id, metrics in self.user_metrics.items()
            }
        }
    
    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        if metric_name not in self.metrics_history:
            return []
        
        return [
            {
                "timestamp": point.timestamp.isoformat(),
                "value": point.value,
                "metadata": point.metadata
            }
            for point in self.metrics_history[metric_name]
            if point.timestamp > cutoff_time
        ]
    
    def reset_metrics(self):
        """Reset current metrics (for testing or periodic resets)."""
        self.current_metrics = AgentPerformanceMetrics()
        self.tool_metrics.clear()
        self.user_metrics.clear()


class AlertingEngine:
    """Handles automated alerting based on metrics and thresholds."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "response_time": 5.0,  # 5 seconds
            "tool_failure_rate": 0.15,  # 15% tool failure rate
            "reasoning_loop_detection": 20,  # 20 reasoning steps
            "session_timeout": 1800,  # 30 minutes
        }
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.cooldown_period = timedelta(minutes=15)  # 15 minute cooldown
    
    async def check_alerts(self):
        """Check all alert conditions and trigger alerts if necessary."""
        try:
            await self._check_error_rate_alert()
            await self._check_response_time_alert()
            await self._check_tool_performance_alerts()
            await self._check_reasoning_loop_alerts()
            await self._check_session_timeout_alerts()
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _check_error_rate_alert(self):
        """Check for high error rate and trigger alert if necessary."""
        metrics = self.metrics_collector.current_metrics
        
        if metrics.request_count >= 10 and metrics.error_rate > self.alert_thresholds["error_rate"]:
            alert_key = "high_error_rate"
            
            if self._should_trigger_alert(alert_key):
                await alert_manager.create_alert(
                    level=AlertLevel.ERROR,
                    title="High Error Rate Detected",
                    message=f"Error rate is {metrics.error_rate:.2%} (threshold: {self.alert_thresholds['error_rate']:.2%})",
                    category=alert_key,
                    data={
                        "current_error_rate": metrics.error_rate,
                        "threshold": self.alert_thresholds["error_rate"],
                        "total_requests": metrics.request_count,
                        "failed_requests": metrics.error_count
                    }
                )
                self.alert_cooldowns[alert_key] = datetime.utcnow()
    
    async def _check_response_time_alert(self):
        """Check for high response time and trigger alert if necessary."""
        metrics = self.metrics_collector.current_metrics
        
        if metrics.request_count > 0 and metrics.average_response_time > self.alert_thresholds["response_time"]:
            alert_key = "high_response_time"
            
            if self._should_trigger_alert(alert_key):
                await alert_manager.create_alert(
                    level=AlertLevel.WARNING,
                    title="High Response Time Detected",
                    message=f"Average response time is {metrics.average_response_time:.2f}s (threshold: {self.alert_thresholds['response_time']}s)",
                    category=alert_key,
                    data={
                        "current_response_time": metrics.average_response_time,
                        "threshold": self.alert_thresholds["response_time"],
                        "total_requests": metrics.request_count
                    }
                )
                self.alert_cooldowns[alert_key] = datetime.utcnow()
    
    async def _check_tool_performance_alerts(self):
        """Check for tool performance issues and trigger alerts if necessary."""
        for tool_name, metrics in self.metrics_collector.tool_metrics.items():
            if metrics.request_count >= 5 and metrics.error_rate > self.alert_thresholds["tool_failure_rate"]:
                alert_key = f"tool_failure_{tool_name}"
                
                if self._should_trigger_alert(alert_key):
                    await alert_manager.create_alert(
                        level=AlertLevel.ERROR,
                        title=f"High Failure Rate for {tool_name}",
                        message=f"{tool_name} failure rate is {metrics.error_rate:.2%} (threshold: {self.alert_thresholds['tool_failure_rate']:.2%})",
                        category=alert_key,
                        data={
                            "tool_name": tool_name,
                            "failure_rate": metrics.error_rate,
                            "threshold": self.alert_thresholds["tool_failure_rate"],
                            "total_executions": metrics.request_count,
                            "failed_executions": metrics.error_count
                        }
                    )
                    self.alert_cooldowns[alert_key] = datetime.utcnow()
    
    async def _check_reasoning_loop_alerts(self):
        """Check for potential reasoning loops and trigger alerts if necessary."""
        # Check recent reasoning traces for excessive steps
        for correlation_id in list(self.metrics_collector.active_correlation_ids):
            reasoning_trace = react_agent_logger.get_reasoning_trace(correlation_id)
            
            if len(reasoning_trace) > self.alert_thresholds["reasoning_loop_detection"]:
                alert_key = f"reasoning_loop_{correlation_id}"
                
                if self._should_trigger_alert(alert_key):
                    await alert_manager.create_alert(
                        level=AlertLevel.WARNING,
                        title="Potential Reasoning Loop Detected",
                        message=f"Reasoning trace {correlation_id} has {len(reasoning_trace)} steps (threshold: {self.alert_thresholds['reasoning_loop_detection']})",
                        category=alert_key,
                        data={
                            "correlation_id": correlation_id,
                            "reasoning_steps": len(reasoning_trace),
                            "threshold": self.alert_thresholds["reasoning_loop_detection"]
                        }
                    )
                    self.alert_cooldowns[alert_key] = datetime.utcnow()
    
    async def _check_session_timeout_alerts(self):
        """Check for sessions that have been active too long."""
        current_time = datetime.utcnow()
        timeout_threshold = timedelta(seconds=self.alert_thresholds["session_timeout"])
        
        for session_id, start_time in self.metrics_collector.session_start_times.items():
            if current_time - start_time > timeout_threshold:
                alert_key = f"session_timeout_{session_id}"
                
                if self._should_trigger_alert(alert_key):
                    await alert_manager.create_alert(
                        level=AlertLevel.WARNING,
                        title="Long-Running Session Detected",
                        message=f"Session {session_id} has been active for {(current_time - start_time).total_seconds():.0f} seconds",
                        category=alert_key,
                        data={
                            "session_id": session_id,
                            "duration_seconds": (current_time - start_time).total_seconds(),
                            "threshold_seconds": self.alert_thresholds["session_timeout"]
                        }
                    )
                    self.alert_cooldowns[alert_key] = datetime.utcnow()
    
    def _should_trigger_alert(self, alert_key: str) -> bool:
        """Check if an alert should be triggered based on cooldown period."""
        if alert_key not in self.alert_cooldowns:
            return True
        
        return datetime.utcnow() - self.alert_cooldowns[alert_key] > self.cooldown_period
    
    def update_thresholds(self, thresholds: Dict[str, float]):
        """Update alert thresholds."""
        self.alert_thresholds.update(thresholds)
        logger.info(f"Updated alert thresholds: {thresholds}")


class MonitoringService:
    """Main monitoring service that coordinates metrics collection and alerting."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alerting_engine = AlertingEngine(self.metrics_collector)
        self.running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the monitoring service."""
        if self.running:
            logger.warning("Monitoring service is already running")
            return
        
        self.running = True
        logger.info("Starting monitoring service")
        
        # Start background tasks
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Monitoring service started successfully")
    
    async def stop(self):
        """Stop the monitoring service."""
        if not self.running:
            return
        
        logger.info("Stopping monitoring service")
        self.running = False
        
        # Cancel background tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that runs continuously."""
        while self.running:
            try:
                # Check alerts
                await self.alerting_engine.check_alerts()
                
                # Update health checker with current metrics
                metrics = self.metrics_collector.current_metrics
                if metrics.request_count > 0:
                    health_checker.record_request_time(metrics.average_response_time)
                
                # Sleep for monitoring interval
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_loop(self):
        """Cleanup loop for old data and contexts."""
        while self.running:
            try:
                # Clean up old correlation contexts
                await react_agent_logger.cleanup_old_contexts(max_age_hours=24)
                
                # Clean up old metric data (keep last 7 days)
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                for metric_name, history in self.metrics_collector.metrics_history.items():
                    # Remove old points
                    while history and history[0].timestamp < cutoff_time:
                        history.popleft()
                
                # Sleep for cleanup interval
                await asyncio.sleep(3600)  # Clean up every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)  # Wait longer on error
    
    def record_request_start(self, correlation_id: str, user_id: str, session_id: str):
        """Record the start of a request."""
        self.metrics_collector.record_request_start(correlation_id, user_id, session_id)
    
    def record_request_completion(
        self,
        correlation_id: str,
        user_id: str,
        success: bool,
        response_time: float,
        tools_used: List[str],
        reasoning_steps: int
    ):
        """Record the completion of a request."""
        self.metrics_collector.record_request_completion(
            correlation_id, user_id, success, response_time, tools_used, reasoning_steps
        )
    
    def record_tool_execution(
        self,
        tool_name: str,
        success: bool,
        duration: float,
        error_type: Optional[str] = None
    ):
        """Record a tool execution."""
        self.metrics_collector.record_tool_execution(tool_name, success, duration, error_type)
    
    def record_session_end(self, session_id: str):
        """Record the end of a session."""
        self.metrics_collector.record_session_end(session_id)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        return self.metrics_collector.get_metrics_summary()
    
    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric."""
        return self.metrics_collector.get_metric_history(metric_name, hours)
    
    def update_alert_thresholds(self, thresholds: Dict[str, float]):
        """Update alert thresholds."""
        self.alerting_engine.update_thresholds(thresholds)


# Global monitoring service instance
monitoring_service = MonitoringService()


async def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    return monitoring_service