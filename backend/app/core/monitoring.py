"""
Monitoring and alerting system for error tracking and system health.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from app.core.exceptions import PromptFlowException, ErrorCategory, ErrorSeverity
from app.core.logging_config import get_logging_stats, error_count_handler


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    level: AlertLevel
    title: str
    message: str
    category: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthMetrics:
    """System health metrics."""
    timestamp: datetime
    error_rate: float
    warning_rate: float
    response_time_avg: float
    active_connections: int
    memory_usage: float
    cpu_usage: float
    disk_usage: float
    uptime: float


class HealthChecker:
    """System health monitoring."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.request_times: List[float] = []
        self.max_request_times = 1000  # Keep last 1000 request times
    
    def record_request_time(self, duration: float):
        """Record a request processing time."""
        self.request_times.append(duration)
        if len(self.request_times) > self.max_request_times:
            self.request_times.pop(0)
    
    async def get_health_metrics(self) -> HealthMetrics:
        """Get current system health metrics."""
        now = datetime.utcnow()
        uptime = (now - self.start_time).total_seconds()
        
        # Get error statistics
        error_stats = error_count_handler.get_stats()
        total_requests = sum(error_stats["errors"].values()) + sum(error_stats["warnings"].values()) + 1000  # Estimate
        error_rate = error_stats["total_errors"] / total_requests if total_requests > 0 else 0
        warning_rate = error_stats["total_warnings"] / total_requests if total_requests > 0 else 0
        
        # Calculate average response time
        avg_response_time = sum(self.request_times) / len(self.request_times) if self.request_times else 0
        
        return HealthMetrics(
            timestamp=now,
            error_rate=error_rate,
            warning_rate=warning_rate,
            response_time_avg=avg_response_time,
            active_connections=0,  # Would need to implement connection tracking
            memory_usage=0.0,  # Would need psutil or similar
            cpu_usage=0.0,  # Would need psutil or similar
            disk_usage=0.0,  # Would need psutil or similar
            uptime=uptime
        )
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        metrics = await self.get_health_metrics()
        
        health_status = "healthy"
        issues = []
        
        # Check error rate
        if metrics.error_rate > 0.1:  # More than 10% error rate
            health_status = "unhealthy"
            issues.append(f"High error rate: {metrics.error_rate:.2%}")
        elif metrics.error_rate > 0.05:  # More than 5% error rate
            health_status = "degraded"
            issues.append(f"Elevated error rate: {metrics.error_rate:.2%}")
        
        # Check response time
        if metrics.response_time_avg > 5.0:  # More than 5 seconds
            health_status = "unhealthy"
            issues.append(f"High response time: {metrics.response_time_avg:.2f}s")
        elif metrics.response_time_avg > 2.0:  # More than 2 seconds
            if health_status == "healthy":
                health_status = "degraded"
            issues.append(f"Elevated response time: {metrics.response_time_avg:.2f}s")
        
        return {
            "status": health_status,
            "timestamp": metrics.timestamp.isoformat(),
            "uptime": metrics.uptime,
            "metrics": {
                "error_rate": metrics.error_rate,
                "warning_rate": metrics.warning_rate,
                "avg_response_time": metrics.response_time_avg,
                "active_connections": metrics.active_connections
            },
            "issues": issues
        }


class AlertManager:
    """Alert management system."""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.logger = logging.getLogger(__name__)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    async def create_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        category: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create and process a new alert."""
        alert_id = f"{category}_{datetime.utcnow().timestamp()}"
        
        alert = Alert(
            id=alert_id,
            level=level,
            title=title,
            message=message,
            category=category,
            timestamp=datetime.utcnow(),
            data=data or {}
        )
        
        self.alerts[alert_id] = alert
        
        # Log the alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }[level]
        
        self.logger.log(
            log_level,
            f"Alert: {title}",
            extra={
                "alert_id": alert_id,
                "alert_level": level.value,
                "alert_category": category,
                "alert_message": message,
                "alert_data": data
            }
        )
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                await asyncio.create_task(self._call_handler(handler, alert))
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
        
        return alert
    
    async def _call_handler(self, handler: Callable[[Alert], None], alert: Alert):
        """Call alert handler safely."""
        if asyncio.iscoroutinefunction(handler):
            await handler(alert)
        else:
            handler(alert)
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            self.logger.info(
                f"Alert resolved: {alert.title}",
                extra={
                    "alert_id": alert_id,
                    "resolution_time": alert.resolved_at.isoformat()
                }
            )
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alerts."""
        active_alerts = self.get_active_alerts()
        
        summary = {
            "total_alerts": len(self.alerts),
            "active_alerts": len(active_alerts),
            "resolved_alerts": len(self.alerts) - len(active_alerts),
            "alerts_by_level": {},
            "alerts_by_category": {}
        }
        
        for alert in active_alerts:
            # Count by level
            level_key = alert.level.value
            summary["alerts_by_level"][level_key] = summary["alerts_by_level"].get(level_key, 0) + 1
            
            # Count by category
            summary["alerts_by_category"][alert.category] = summary["alerts_by_category"].get(alert.category, 0) + 1
        
        return summary


class ErrorMonitor:
    """Monitor errors and trigger alerts."""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.error_thresholds = {
            ErrorCategory.SYSTEM: 5,    # 5 system errors in window
            ErrorCategory.EXTERNAL_API: 10,  # 10 API errors in window
            ErrorCategory.DATABASE: 3,  # 3 database errors in window
            ErrorCategory.CONNECTOR: 8,  # 8 connector errors in window
        }
        self.time_window = timedelta(minutes=5)
        self.recent_errors: List[PromptFlowException] = []
        self.logger = logging.getLogger(__name__)
    
    async def record_error(self, error: PromptFlowException):
        """Record an error and check if alerts should be triggered."""
        self.recent_errors.append(error)
        
        # Clean old errors outside time window
        cutoff_time = datetime.utcnow() - self.time_window
        self.recent_errors = [
            e for e in self.recent_errors
            if e.timestamp > cutoff_time
        ]
        
        # Check if we should trigger alerts
        await self._check_error_thresholds(error)
    
    async def _check_error_thresholds(self, latest_error: PromptFlowException):
        """Check if error thresholds are exceeded and trigger alerts."""
        # Count errors by category in recent window
        error_counts = {}
        for error in self.recent_errors:
            category = error.category
            error_counts[category] = error_counts.get(category, 0) + 1
        
        # Check thresholds
        for category, threshold in self.error_thresholds.items():
            count = error_counts.get(category, 0)
            if count >= threshold:
                # Check if we haven't already alerted for this category recently
                alert_key = f"error_threshold_{category.value}"
                existing_alerts = [
                    alert for alert in self.alert_manager.get_active_alerts()
                    if alert.category == alert_key
                ]
                
                if not existing_alerts:  # Only create alert if none exists
                    await self._create_error_alert(category, count, threshold)
        
        # Special handling for critical errors
        if latest_error.severity == ErrorSeverity.CRITICAL:
            await self._create_critical_error_alert(latest_error)
    
    async def _create_error_alert(self, category: ErrorCategory, count: int, threshold: int):
        """Create alert for error threshold exceeded."""
        await self.alert_manager.create_alert(
            level=AlertLevel.ERROR,
            title=f"Error Threshold Exceeded: {category.value}",
            message=f"{count} {category.value} errors in the last {self.time_window.total_seconds()/60:.0f} minutes (threshold: {threshold})",
            category=f"error_threshold_{category.value}",
            data={
                "error_category": category.value,
                "error_count": count,
                "threshold": threshold,
                "time_window_minutes": self.time_window.total_seconds() / 60
            }
        )
    
    async def _create_critical_error_alert(self, error: PromptFlowException):
        """Create alert for critical error."""
        await self.alert_manager.create_alert(
            level=AlertLevel.CRITICAL,
            title="Critical Error Occurred",
            message=f"Critical error: {error.message}",
            category="critical_error",
            data={
                "error_code": error.error_code,
                "error_message": error.message,
                "error_details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        )


# Global instances
health_checker = HealthChecker()
alert_manager = AlertManager()
error_monitor = ErrorMonitor(alert_manager)


async def log_alert_to_console(alert: Alert):
    """Default alert handler that logs to console."""
    logger = logging.getLogger("monitoring")
    logger.warning(f"ALERT [{alert.level.value.upper()}]: {alert.title} - {alert.message}")


# Add default alert handler
alert_manager.add_alert_handler(log_alert_to_console)


async def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status."""
    health_check = await health_checker.check_health()
    alert_summary = alert_manager.get_alert_summary()
    logging_stats = get_logging_stats()
    
    return {
        "health": health_check,
        "alerts": alert_summary,
        "logging": logging_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


async def record_error_for_monitoring(error: PromptFlowException):
    """Record error for monitoring and alerting."""
    await error_monitor.record_error(error)


def record_request_time(duration: float):
    """Record request processing time for monitoring."""
    health_checker.record_request_time(duration)