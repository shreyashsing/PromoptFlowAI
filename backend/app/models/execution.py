"""
Workflow execution-related data models.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from .base import WorkflowStatus


class ExecutionStatus(str, Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeExecutionResult(BaseModel):
    """Result of executing a single workflow node."""
    node_id: str
    connector_name: str
    status: ExecutionStatus
    result: Any = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class ExecutionResult(BaseModel):
    """Complete workflow execution result."""
    execution_id: str
    workflow_id: str
    user_id: str
    status: ExecutionStatus
    node_results: List[NodeExecutionResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorHandlingResult(BaseModel):
    """Result of error handling for a failed node."""
    should_retry: bool
    retry_delay_seconds: int = 0
    max_retries: int = 3
    fallback_action: Optional[str] = None
    user_notification: Optional[str] = None