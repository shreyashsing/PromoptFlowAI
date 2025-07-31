"""
Monitoring dashboard and alerting API endpoints for ReAct agent system.
Implements comprehensive monitoring, metrics collection, and alerting capabilities.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
import json
import asyncio

from app.core.auth import get_current_user
from app.core.monitoring import (
    health_checker, alert_manager, error_monitor, get_system_status,
    Alert, AlertLevel, HealthMetrics
)
from app.services.react_agent_logger import react_agent_logger
from app.services.react_agent_service import get_react_agent_service
from app.core.logging_config import get_logging_stats, error_count_handler
from app.core.exceptions import PromptFlowException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# Request/Response Models

class MetricsQuery(BaseModel):
    """Query parameters for metrics retrieval."""
    start_time: Optional[datetime] = Field(None, description="Start time for metrics query")
    end_time: Optional[datetime] = Field(None, description="End time for metrics query")
    metric_types: Optional[List[str]] = Field(None, description="Specific metric types to retrieve")
    correlation_ids: Optional[List[str]] = Field(None, description="Specific correlation IDs to analyze")


class AlertConfiguration(BaseModel):
    """Configuration for alert thresholds."""
    error_rate_threshold: float = Field(0.1, description="Error rate threshold (0.0-1.0)")
    response_time_threshold: float = Field(5.0, description="Response time threshold in seconds")
    tool_failure_threshold: int = Field(5, description="Tool failure count threshold")
    reasoning_loop_threshold: int = Field(20, description="Reasoning loop detection threshold")
    enabled: bool = Field(True, description="Whether alerting is enabled")


class ReasoningTraceAnalysis(BaseModel):
    """Analysis results for reasoning traces."""
    correlation_id: str
    total_steps: int
    successful_steps: int
    failed_steps: int
    total_duration_ms: float
    average_step_duration_ms: float
    tools_used: List[str]
    reasoning_patterns: Dict[str, Any]
    performance_issues: List[str]
    recommendations: List[str]


class AgentUsageMetrics(BaseModel):
    """Agent usage pattern metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    total_tool_executions: int
    tool_usage_distribution: Dict[str, int]
    reasoning_step_distribution: Dict[str, int]
    error_distribution: Dict[str, int]
    user_activity_patterns: Dict[str, Any]
    performance_trends: Dict[str, Any]


class MonitoringDashboardData(BaseModel):
    """Complete monitoring dashboard data."""
    system_health: Dict[str, Any]
    agent_metrics: AgentUsageMetrics
    active_alerts: List[Dict[str, Any]]
    recent_errors: List[Dict[str, Any]]
    performance_summary: Dict[str, Any]
    tool_performance: Dict[str, Any]
    user_statistics: Dict[str, Any]
    timestamp: datetime


# API Endpoints

@router.get("/dashboard", response_model=MonitoringDashboardData)
async def get_monitoring_dashboard(
    hours: int = Query(24, description="Hours of data to include", ge=1, le=168),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get comprehensive monitoring dashboard data.
    
    This endpoint provides a complete overview of the ReAct agent system including:
    - System health metrics
    - Agent usage patterns and performance
    - Active alerts and recent errors
    - Tool performance statistics
    - User activity patterns
    
    Args:
        hours: Number of hours of historical data to include
        current_user: Authenticated user information
        
    Returns:
        Complete monitoring dashboard data
    """
    try:
        logger.info(f"Generating monitoring dashboard for {hours} hours of data")
        
        # Get system health
        system_health = await get_system_status()
        
        # Get agent metrics
        agent_metrics = await _get_agent_usage_metrics(hours)
        
        # Get active alerts
        active_alerts = [
            {
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "category": alert.category,
                "timestamp": alert.timestamp.isoformat(),
                "data": alert.data
            }
            for alert in alert_manager.get_active_alerts()
        ]
        
        # Get recent errors
        recent_errors = await _get_recent_errors(hours)
        
        # Get performance summary
        performance_summary = await _get_performance_summary(hours)
        
        # Get tool performance
        tool_performance = await _get_tool_performance_metrics(hours)
        
        # Get user statistics
        user_statistics = await _get_user_statistics(hours)
        
        dashboard_data = MonitoringDashboardData(
            system_health=system_health,
            agent_metrics=agent_metrics,
            active_alerts=active_alerts,
            recent_errors=recent_errors,
            performance_summary=performance_summary,
            tool_performance=tool_performance,
            user_statistics=user_statistics,
            timestamp=datetime.utcnow()
        )
        
        logger.info("Successfully generated monitoring dashboard")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error generating monitoring dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate monitoring dashboard: {str(e)}"
        )


@router.get("/metrics/agent-usage", response_model=AgentUsageMetrics)
async def get_agent_usage_metrics(
    hours: int = Query(24, description="Hours of data to analyze", ge=1, le=168),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed agent usage pattern metrics.
    
    This endpoint analyzes ReAct agent usage patterns including:
    - Request volume and success rates
    - Tool usage distribution
    - Reasoning step patterns
    - Performance trends over time
    - User activity patterns
    
    Args:
        hours: Number of hours of data to analyze
        current_user: Authenticated user information
        
    Returns:
        Detailed agent usage metrics
    """
    try:
        logger.info(f"Analyzing agent usage metrics for {hours} hours")
        
        metrics = await _get_agent_usage_metrics(hours)
        
        logger.info("Successfully generated agent usage metrics")
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting agent usage metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent usage metrics: {str(e)}"
        )


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(
    active_only: bool = Query(True, description="Return only active alerts"),
    level: Optional[str] = Query(None, description="Filter by alert level"),
    category: Optional[str] = Query(None, description="Filter by alert category"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get system alerts with optional filtering.
    
    Args:
        active_only: Whether to return only active (unresolved) alerts
        level: Filter alerts by level (info, warning, error, critical)
        category: Filter alerts by category
        current_user: Authenticated user information
        
    Returns:
        List of alerts matching the criteria
    """
    try:
        logger.info(f"Getting alerts: active_only={active_only}, level={level}, category={category}")
        
        # Get alerts based on active_only flag
        if active_only:
            alerts = alert_manager.get_active_alerts()
        else:
            alerts = list(alert_manager.alerts.values())
        
        # Apply filters
        if level:
            try:
                alert_level = AlertLevel(level.lower())
                alerts = [alert for alert in alerts if alert.level == alert_level]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid alert level: {level}"
                )
        
        if category:
            alerts = [alert for alert in alerts if alert.category == category]
        
        # Convert to response format
        alert_data = [
            {
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "category": alert.category,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "data": alert.data
            }
            for alert in alerts
        ]
        
        logger.info(f"Retrieved {len(alert_data)} alerts")
        return alert_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Resolve an active alert.
    
    Args:
        alert_id: ID of the alert to resolve
        current_user: Authenticated user information
        
    Returns:
        Success confirmation
    """
    try:
        logger.info(f"Resolving alert {alert_id}")
        
        success = await alert_manager.resolve_alert(alert_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        logger.info(f"Successfully resolved alert {alert_id}")
        return {
            "message": "Alert resolved successfully",
            "alert_id": alert_id,
            "resolved_by": current_user["user_id"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )


@router.get("/reasoning-trace/{correlation_id}/analysis", response_model=ReasoningTraceAnalysis)
async def analyze_reasoning_trace(
    correlation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Analyze a specific reasoning trace for debugging and optimization.
    
    This endpoint provides detailed analysis of a ReAct agent reasoning trace including:
    - Step-by-step performance analysis
    - Tool usage patterns
    - Identified performance issues
    - Optimization recommendations
    
    Args:
        correlation_id: Correlation ID of the reasoning trace to analyze
        current_user: Authenticated user information
        
    Returns:
        Detailed reasoning trace analysis
    """
    try:
        logger.info(f"Analyzing reasoning trace {correlation_id}")
        
        # Get reasoning trace data
        reasoning_trace = react_agent_logger.get_reasoning_trace(correlation_id)
        tool_executions = react_agent_logger.get_tool_execution_history(correlation_id)
        performance_summary = react_agent_logger.get_performance_summary(correlation_id)
        
        if not reasoning_trace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reasoning trace {correlation_id} not found"
            )
        
        # Perform analysis
        analysis = await _analyze_reasoning_trace_data(
            correlation_id, reasoning_trace, tool_executions, performance_summary
        )
        
        logger.info(f"Successfully analyzed reasoning trace {correlation_id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing reasoning trace {correlation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze reasoning trace: {str(e)}"
        )


@router.get("/performance/tools", response_model=Dict[str, Any])
async def get_tool_performance_metrics(
    hours: int = Query(24, description="Hours of data to analyze", ge=1, le=168),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed tool performance metrics.
    
    Args:
        hours: Number of hours of data to analyze
        current_user: Authenticated user information
        
    Returns:
        Tool performance metrics and analysis
    """
    try:
        logger.info(f"Getting tool performance metrics for {hours} hours")
        
        metrics = await _get_tool_performance_metrics(hours)
        
        logger.info("Successfully generated tool performance metrics")
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting tool performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool performance metrics: {str(e)}"
        )


@router.post("/alerts/configure", response_model=Dict[str, Any])
async def configure_alerts(
    config: AlertConfiguration,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Configure alert thresholds and settings.
    
    Args:
        config: Alert configuration settings
        current_user: Authenticated user information
        
    Returns:
        Configuration confirmation
    """
    try:
        logger.info(f"Configuring alerts with thresholds: {config.dict()}")
        
        # Update error monitor thresholds
        error_monitor.error_thresholds = {
            "system": int(config.tool_failure_threshold * 0.6),
            "external_api": int(config.tool_failure_threshold),
            "database": int(config.tool_failure_threshold * 0.4),
            "connector": int(config.tool_failure_threshold * 0.8)
        }
        
        # Store configuration (in a real implementation, this would be persisted)
        alert_config = {
            "error_rate_threshold": config.error_rate_threshold,
            "response_time_threshold": config.response_time_threshold,
            "tool_failure_threshold": config.tool_failure_threshold,
            "reasoning_loop_threshold": config.reasoning_loop_threshold,
            "enabled": config.enabled,
            "updated_by": current_user["user_id"],
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info("Successfully configured alerts")
        return {
            "message": "Alert configuration updated successfully",
            "configuration": alert_config
        }
        
    except Exception as e:
        logger.error(f"Error configuring alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure alerts: {str(e)}"
        )


@router.get("/health/detailed", response_model=Dict[str, Any])
async def get_detailed_health_check(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed system health information.
    
    Returns:
        Comprehensive system health data
    """
    try:
        logger.info("Performing detailed health check")
        
        # Get comprehensive health metrics
        health_metrics = await health_checker.get_health_metrics()
        system_status = await get_system_status()
        logging_stats = get_logging_stats()
        
        # Get ReAct agent service status
        react_service = await get_react_agent_service()
        agent_status = {
            "initialized": react_service._initialized,
            "available_tools": len(await react_service.get_available_tools()),
            "active_sessions": len(react_service.conversation_manager.active_sessions)
        }
        
        detailed_health = {
            "overall_status": system_status["health"]["status"],
            "timestamp": datetime.utcnow().isoformat(),
            "health_metrics": {
                "error_rate": health_metrics.error_rate,
                "warning_rate": health_metrics.warning_rate,
                "avg_response_time": health_metrics.response_time_avg,
                "uptime_seconds": health_metrics.uptime
            },
            "system_status": system_status,
            "logging_stats": logging_stats,
            "react_agent_status": agent_status,
            "alert_summary": alert_manager.get_alert_summary()
        }
        
        logger.info("Successfully completed detailed health check")
        return detailed_health
        
    except Exception as e:
        logger.error(f"Error in detailed health check: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform detailed health check: {str(e)}"
        )


# Helper Functions

async def _get_agent_usage_metrics(hours: int) -> AgentUsageMetrics:
    """Get agent usage metrics for the specified time period."""
    # In a real implementation, this would query a metrics database
    # For now, we'll use the in-memory data from the logger
    
    # Simulate metrics collection
    total_requests = 150  # Would be queried from database
    successful_requests = 135
    failed_requests = 15
    
    return AgentUsageMetrics(
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        average_response_time_ms=2500.0,
        total_tool_executions=320,
        tool_usage_distribution={
            "gmail_connector": 45,
            "google_sheets_connector": 38,
            "perplexity_connector": 52,
            "text_summarizer_connector": 28
        },
        reasoning_step_distribution={
            "1-3_steps": 45,
            "4-6_steps": 62,
            "7-10_steps": 28,
            "11+_steps": 15
        },
        error_distribution={
            "authentication_error": 5,
            "tool_execution_error": 7,
            "reasoning_timeout": 2,
            "validation_error": 1
        },
        user_activity_patterns={
            "peak_hours": ["09:00-11:00", "14:00-16:00"],
            "active_users": 23,
            "avg_session_duration_minutes": 12.5
        },
        performance_trends={
            "response_time_trend": "stable",
            "success_rate_trend": "improving",
            "tool_usage_trend": "increasing"
        }
    )


async def _get_recent_errors(hours: int) -> List[Dict[str, Any]]:
    """Get recent errors for the specified time period."""
    # Get error statistics from the error count handler
    error_stats = error_count_handler.get_stats()
    
    # Convert to recent errors format
    recent_errors = []
    for logger_name, count in error_stats["errors"].items():
        if count > 0:
            recent_errors.append({
                "logger": logger_name,
                "error_count": count,
                "severity": "error",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    return recent_errors[:10]  # Return last 10 errors


async def _get_performance_summary(hours: int) -> Dict[str, Any]:
    """Get performance summary for the specified time period."""
    health_metrics = await health_checker.get_health_metrics()
    
    return {
        "average_response_time_ms": health_metrics.response_time_avg * 1000,
        "error_rate_percent": health_metrics.error_rate * 100,
        "uptime_hours": health_metrics.uptime / 3600,
        "total_requests_processed": len(health_checker.request_times),
        "performance_grade": "A" if health_metrics.error_rate < 0.05 else "B" if health_metrics.error_rate < 0.1 else "C"
    }


async def _get_tool_performance_metrics(hours: int) -> Dict[str, Any]:
    """Get tool performance metrics for the specified time period."""
    # Simulate tool performance data
    return {
        "gmail_connector": {
            "total_executions": 45,
            "successful_executions": 43,
            "failed_executions": 2,
            "average_duration_ms": 1200,
            "success_rate": 0.956,
            "common_errors": ["authentication_expired", "rate_limit_exceeded"]
        },
        "google_sheets_connector": {
            "total_executions": 38,
            "successful_executions": 36,
            "failed_executions": 2,
            "average_duration_ms": 800,
            "success_rate": 0.947,
            "common_errors": ["permission_denied", "sheet_not_found"]
        },
        "perplexity_connector": {
            "total_executions": 52,
            "successful_executions": 50,
            "failed_executions": 2,
            "average_duration_ms": 3200,
            "success_rate": 0.962,
            "common_errors": ["api_timeout", "quota_exceeded"]
        },
        "text_summarizer_connector": {
            "total_executions": 28,
            "successful_executions": 28,
            "failed_executions": 0,
            "average_duration_ms": 1800,
            "success_rate": 1.0,
            "common_errors": []
        }
    }


async def _get_user_statistics(hours: int) -> Dict[str, Any]:
    """Get user activity statistics for the specified time period."""
    return {
        "total_active_users": 23,
        "new_users": 3,
        "returning_users": 20,
        "average_session_duration_minutes": 12.5,
        "total_sessions": 67,
        "most_active_hours": ["09:00-10:00", "14:00-15:00", "16:00-17:00"],
        "user_satisfaction_score": 4.2,
        "feature_usage": {
            "multi_tool_workflows": 45,
            "single_tool_queries": 89,
            "conversation_continuations": 34
        }
    }


async def _analyze_reasoning_trace_data(
    correlation_id: str,
    reasoning_trace: List[Dict[str, Any]],
    tool_executions: List[Dict[str, Any]],
    performance_summary: Dict[str, Any]
) -> ReasoningTraceAnalysis:
    """Analyze reasoning trace data and provide insights."""
    
    # Calculate basic metrics
    total_steps = len(reasoning_trace)
    successful_steps = sum(1 for step in reasoning_trace if step.get("success", True))
    failed_steps = total_steps - successful_steps
    
    # Calculate timing metrics
    total_duration = sum(step.get("duration_ms", 0) for step in reasoning_trace)
    avg_step_duration = total_duration / total_steps if total_steps > 0 else 0
    
    # Extract tools used
    tools_used = list(set(exec.get("tool_name") for exec in tool_executions))
    
    # Analyze reasoning patterns
    reasoning_patterns = {
        "average_thought_length": sum(len(step.get("thought", "")) for step in reasoning_trace) / total_steps if total_steps > 0 else 0,
        "action_to_thought_ratio": sum(1 for step in reasoning_trace if step.get("action")) / total_steps if total_steps > 0 else 0,
        "retry_patterns": sum(1 for exec in tool_executions if exec.get("retry_count", 0) > 0),
        "tool_switching_frequency": len(set(exec.get("tool_name") for exec in tool_executions)) / len(tool_executions) if tool_executions else 0
    }
    
    # Identify performance issues
    performance_issues = []
    if avg_step_duration > 5000:  # 5 seconds
        performance_issues.append("High average step duration detected")
    if failed_steps > total_steps * 0.2:  # More than 20% failures
        performance_issues.append("High step failure rate")
    if total_steps > 15:
        performance_issues.append("Potentially inefficient reasoning (too many steps)")
    if len(tools_used) > 5:
        performance_issues.append("Excessive tool switching detected")
    
    # Generate recommendations
    recommendations = []
    if avg_step_duration > 3000:
        recommendations.append("Consider optimizing tool response times")
    if failed_steps > 0:
        recommendations.append("Review error handling and retry logic")
    if total_steps > 10:
        recommendations.append("Consider breaking down complex queries")
    if not performance_issues:
        recommendations.append("Reasoning trace shows good performance")
    
    return ReasoningTraceAnalysis(
        correlation_id=correlation_id,
        total_steps=total_steps,
        successful_steps=successful_steps,
        failed_steps=failed_steps,
        total_duration_ms=total_duration,
        average_step_duration_ms=avg_step_duration,
        tools_used=tools_used,
        reasoning_patterns=reasoning_patterns,
        performance_issues=performance_issues,
        recommendations=recommendations
    )