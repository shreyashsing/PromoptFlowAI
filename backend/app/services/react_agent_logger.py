"""
Comprehensive logging system for ReAct agent operations.
Implements detailed logging of reasoning steps, tool executions, and performance metrics.
"""
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import time
from contextlib import asynccontextmanager

from app.core.logging_config import get_logger


class LogLevel(Enum):
    """Log levels for ReAct agent operations."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OperationType(Enum):
    """Types of ReAct agent operations."""
    REASONING_STEP = "reasoning_step"
    TOOL_EXECUTION = "tool_execution"
    AGENT_INITIALIZATION = "agent_initialization"
    SESSION_CREATION = "session_creation"
    REQUEST_PROCESSING = "request_processing"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE_METRIC = "performance_metric"
    AUTHENTICATION = "authentication"
    CONVERSATION_UPDATE = "conversation_update"


@dataclass
class CorrelationContext:
    """Context for correlating related log entries."""
    correlation_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ReasoningStep:
    """Represents a single reasoning step in the ReAct process."""
    step_id: str
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: datetime = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        return data


@dataclass
class ToolExecution:
    """Represents a tool execution event."""
    execution_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Optional[Any] = None
    start_time: datetime = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.utcnow()
    
    def complete(self, output: Any = None, error: Optional[str] = None):
        """Mark tool execution as complete."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        if error:
            self.success = False
            self.error_message = error
        else:
            self.tool_output = output
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat() if self.start_time else None
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        # Sanitize sensitive data in tool input/output
        data['tool_input'] = self._sanitize_data(self.tool_input)
        data['tool_output'] = self._sanitize_data(self.tool_output)
        return data
    
    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize sensitive data from tool input/output."""
        if isinstance(data, dict):
            sanitized = {}
            sensitive_keys = {'password', 'token', 'key', 'secret', 'auth', 'credential'}
            for key, value in data.items():
                if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    # Truncate long strings
                    sanitized[key] = str(value)[:200] if isinstance(value, str) and len(str(value)) > 200 else value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data[:10]]  # Limit list size
        else:
            return str(data)[:200] if isinstance(data, str) and len(str(data)) > 200 else data


@dataclass
class PerformanceMetrics:
    """Performance metrics for ReAct agent operations."""
    operation_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_count: int = 0
    retry_count: int = 0
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    def complete(self, success: bool = True, error_count: int = 0):
        """Mark performance measurement as complete."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.error_count = error_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data


class ReactAgentLogger:
    """
    Comprehensive logging system for ReAct agent operations.
    
    This class implements detailed logging of reasoning steps, tool executions,
    and performance metrics with correlation IDs for tracing.
    """
    
    def __init__(self, logger_name: str = "react_agent"):
        self.logger = get_logger(logger_name)
        self.active_contexts: Dict[str, CorrelationContext] = {}
        self.reasoning_traces: Dict[str, List[ReasoningStep]] = {}
        self.tool_executions: Dict[str, List[ToolExecution]] = {}
        self.performance_metrics: Dict[str, List[PerformanceMetrics]] = {}
        self._metrics_lock = asyncio.Lock()
    
    def create_correlation_context(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> CorrelationContext:
        """
        Create a new correlation context for tracking related operations.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            request_id: Request identifier
            conversation_id: Conversation identifier
            
        Returns:
            CorrelationContext instance
        """
        correlation_id = str(uuid.uuid4())
        context = CorrelationContext(
            correlation_id=correlation_id,
            session_id=session_id,
            user_id=user_id,
            request_id=request_id,
            conversation_id=conversation_id
        )
        
        self.active_contexts[correlation_id] = context
        
        # Initialize tracking structures
        self.reasoning_traces[correlation_id] = []
        self.tool_executions[correlation_id] = []
        self.performance_metrics[correlation_id] = []
        
        self.logger.info(
            "Created correlation context",
            extra={
                "operation_type": OperationType.AGENT_INITIALIZATION.value,
                **context.to_dict()
            }
        )
        
        return context
    
    def log_reasoning_step(
        self,
        context: CorrelationContext,
        step_number: int,
        thought: str,
        action: Optional[str] = None,
        action_input: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Log a reasoning step in the ReAct process.
        
        Args:
            context: Correlation context
            step_number: Step number in the reasoning sequence
            thought: The agent's thought process
            action: Action to be taken (if any)
            action_input: Input parameters for the action
            observation: Observation from the action
            duration_ms: Duration of the step in milliseconds
            success: Whether the step was successful
            error_message: Error message if step failed
            
        Returns:
            Step ID for reference
        """
        step_id = str(uuid.uuid4())
        
        reasoning_step = ReasoningStep(
            step_id=step_id,
            step_number=step_number,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message
        )
        
        # Store in trace
        if context.correlation_id in self.reasoning_traces:
            self.reasoning_traces[context.correlation_id].append(reasoning_step)
        
        # Log the reasoning step
        log_level = LogLevel.ERROR if not success else LogLevel.INFO
        self.logger.log(
            getattr(logging, log_level.value),
            f"Reasoning step {step_number}: {thought[:100]}...",
            extra={
                "operation_type": OperationType.REASONING_STEP.value,
                "reasoning_step": reasoning_step.to_dict(),
                **context.to_dict()
            }
        )
        
        return step_id
    
    def log_tool_execution_start(
        self,
        context: CorrelationContext,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        Log the start of a tool execution.
        
        Args:
            context: Correlation context
            tool_name: Name of the tool being executed
            tool_input: Input parameters for the tool
            
        Returns:
            Execution ID for reference
        """
        execution_id = str(uuid.uuid4())
        
        tool_execution = ToolExecution(
            execution_id=execution_id,
            tool_name=tool_name,
            tool_input=tool_input
        )
        
        # Store in executions
        if context.correlation_id in self.tool_executions:
            self.tool_executions[context.correlation_id].append(tool_execution)
        
        self.logger.info(
            f"Starting tool execution: {tool_name}",
            extra={
                "operation_type": OperationType.TOOL_EXECUTION.value,
                "tool_execution": tool_execution.to_dict(),
                **context.to_dict()
            }
        )
        
        return execution_id
    
    def log_tool_execution_complete(
        self,
        context: CorrelationContext,
        execution_id: str,
        output: Any = None,
        error: Optional[str] = None,
        retry_count: int = 0
    ):
        """
        Log the completion of a tool execution.
        
        Args:
            context: Correlation context
            execution_id: Execution ID from start log
            output: Tool output (if successful)
            error: Error message (if failed)
            retry_count: Number of retries attempted
        """
        # Find the tool execution
        tool_execution = None
        if context.correlation_id in self.tool_executions:
            for execution in self.tool_executions[context.correlation_id]:
                if execution.execution_id == execution_id:
                    tool_execution = execution
                    break
        
        if tool_execution:
            tool_execution.complete(output, error)
            tool_execution.retry_count = retry_count
            
            log_level = LogLevel.ERROR if error else LogLevel.INFO
            self.logger.log(
                getattr(logging, log_level.value),
                f"Tool execution {'failed' if error else 'completed'}: {tool_execution.tool_name} "
                f"({tool_execution.duration_ms:.2f}ms)" if tool_execution.duration_ms is not None else 
                f"Tool execution {'failed' if error else 'completed'}: {tool_execution.tool_name}",
                extra={
                    "operation_type": OperationType.TOOL_EXECUTION.value,
                    "tool_execution": tool_execution.to_dict(),
                    **context.to_dict()
                }
            )
    
    @asynccontextmanager
    async def log_performance_metrics(
        self,
        context: CorrelationContext,
        operation_type: str
    ):
        """
        Context manager for logging performance metrics.
        
        Args:
            context: Correlation context
            operation_type: Type of operation being measured
        """
        metrics = PerformanceMetrics(
            operation_type=operation_type,
            start_time=datetime.utcnow()
        )
        
        try:
            yield metrics
            metrics.complete(success=True)
        except Exception as e:
            metrics.complete(success=False, error_count=1)
            raise
        finally:
            # Store metrics
            async with self._metrics_lock:
                if context.correlation_id in self.performance_metrics:
                    self.performance_metrics[context.correlation_id].append(metrics)
            
            # Log performance metrics
            duration_str = f"{metrics.duration_ms:.2f}ms" if metrics.duration_ms is not None else "unknown duration"
            self.logger.info(
                f"Performance: {operation_type} completed in {duration_str}",
                extra={
                    "operation_type": OperationType.PERFORMANCE_METRIC.value,
                    "performance_metrics": metrics.to_dict(),
                    **context.to_dict()
                }
            )
    
    def log_authentication_event(
        self,
        context: CorrelationContext,
        event_type: str,
        user_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log authentication-related events.
        
        Args:
            context: Correlation context
            event_type: Type of authentication event
            user_id: User identifier
            success: Whether authentication was successful
            error_message: Error message if failed
            additional_data: Additional data to log
        """
        log_level = LogLevel.ERROR if not success else LogLevel.INFO
        
        auth_data = {
            "event_type": event_type,
            "user_id": user_id,
            "success": success,
            "error_message": error_message,
            **(additional_data or {})
        }
        
        self.logger.log(
            getattr(logging, log_level.value),
            f"Authentication event: {event_type} {'succeeded' if success else 'failed'}",
            extra={
                "operation_type": OperationType.AUTHENTICATION.value,
                "authentication": auth_data,
                **context.to_dict()
            }
        )
    
    def log_error(
        self,
        context: CorrelationContext,
        error: Exception,
        operation: str,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log error events with full context.
        
        Args:
            context: Correlation context
            error: Exception that occurred
            operation: Operation that failed
            additional_data: Additional data to log
        """
        error_data = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_details": getattr(error, 'details', None),
            **(additional_data or {})
        }
        
        self.logger.error(
            f"Error in {operation}: {str(error)}",
            extra={
                "operation_type": OperationType.ERROR_HANDLING.value,
                "error": error_data,
                **context.to_dict()
            },
            exc_info=True
        )
    
    def get_reasoning_trace(self, correlation_id: str) -> List[Dict[str, Any]]:
        """
        Get the complete reasoning trace for a correlation ID.
        
        Args:
            correlation_id: Correlation ID to get trace for
            
        Returns:
            List of reasoning steps as dictionaries
        """
        if correlation_id in self.reasoning_traces:
            return [step.to_dict() for step in self.reasoning_traces[correlation_id]]
        return []
    
    def get_tool_execution_history(self, correlation_id: str) -> List[Dict[str, Any]]:
        """
        Get the tool execution history for a correlation ID.
        
        Args:
            correlation_id: Correlation ID to get history for
            
        Returns:
            List of tool executions as dictionaries
        """
        if correlation_id in self.tool_executions:
            return [execution.to_dict() for execution in self.tool_executions[correlation_id]]
        return []
    
    def get_performance_summary(self, correlation_id: str) -> Dict[str, Any]:
        """
        Get performance summary for a correlation ID.
        
        Args:
            correlation_id: Correlation ID to get summary for
            
        Returns:
            Performance summary dictionary
        """
        if correlation_id not in self.performance_metrics:
            return {}
        
        metrics = self.performance_metrics[correlation_id]
        if not metrics:
            return {}
        
        total_duration = sum(m.duration_ms or 0 for m in metrics)
        success_count = sum(1 for m in metrics if m.success)
        error_count = sum(m.error_count for m in metrics)
        
        return {
            "total_operations": len(metrics),
            "total_duration_ms": total_duration,
            "average_duration_ms": total_duration / len(metrics) if metrics else 0,
            "success_rate": success_count / len(metrics) if metrics else 0,
            "total_errors": error_count,
            "operations_by_type": {
                op_type: len([m for m in metrics if m.operation_type == op_type])
                for op_type in set(m.operation_type for m in metrics)
            }
        }
    
    def cleanup_context(self, correlation_id: str):
        """
        Clean up tracking data for a correlation ID.
        
        Args:
            correlation_id: Correlation ID to clean up
        """
        self.active_contexts.pop(correlation_id, None)
        self.reasoning_traces.pop(correlation_id, None)
        self.tool_executions.pop(correlation_id, None)
        self.performance_metrics.pop(correlation_id, None)
        
        self.logger.debug(
            f"Cleaned up context {correlation_id}",
            extra={"correlation_id": correlation_id}
        )
    
    async def cleanup_old_contexts(self, max_age_hours: int = 24):
        """
        Clean up old correlation contexts to prevent memory leaks.
        
        Args:
            max_age_hours: Maximum age of contexts to keep in hours
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        contexts_to_remove = []
        
        for correlation_id, context in self.active_contexts.items():
            # Check if any recent activity exists
            has_recent_activity = False
            
            # Check reasoning traces
            if correlation_id in self.reasoning_traces:
                for step in self.reasoning_traces[correlation_id]:
                    if step.timestamp and step.timestamp > cutoff_time:
                        has_recent_activity = True
                        break
            
            # Check tool executions
            if not has_recent_activity and correlation_id in self.tool_executions:
                for execution in self.tool_executions[correlation_id]:
                    if execution.start_time > cutoff_time:
                        has_recent_activity = True
                        break
            
            if not has_recent_activity:
                contexts_to_remove.append(correlation_id)
        
        # Remove old contexts
        for correlation_id in contexts_to_remove:
            self.cleanup_context(correlation_id)
        
        if contexts_to_remove:
            self.logger.info(
                f"Cleaned up {len(contexts_to_remove)} old correlation contexts",
                extra={"cleaned_contexts": len(contexts_to_remove)}
            )


# Global logger instance
react_agent_logger = ReactAgentLogger()