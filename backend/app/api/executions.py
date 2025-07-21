"""
API endpoints for workflow execution management and monitoring.

This module provides REST endpoints for:
- Monitoring workflow execution status
- Retrieving execution history and logs
- Managing running executions (cancel, etc.)
- Getting execution statistics
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.auth import get_current_user
from app.models.execution import ExecutionResult, ExecutionStatus, NodeExecutionResult
from app.services.workflow_orchestrator import WorkflowOrchestrator


router = APIRouter(prefix="/executions", tags=["executions"])

# Global orchestrator instance
orchestrator = WorkflowOrchestrator()


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""
    execution_id: str
    workflow_id: str
    user_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_duration_ms: Optional[int]
    error: Optional[str]
    node_results: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionListResponse(BaseModel):
    """Response model for execution list."""
    executions: List[ExecutionStatusResponse]
    total_count: int
    has_more: bool


class ExecutionStatsResponse(BaseModel):
    """Response model for execution statistics."""
    total_executions: int
    completed: int
    failed: int
    running: int
    pending: int
    cancelled: int
    success_rate: float
    average_duration_ms: float


class NodeExecutionResponse(BaseModel):
    """Response model for node execution details."""
    node_id: str
    connector_name: str
    status: str
    result: Any = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


@router.get("/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a workflow execution.
    
    Args:
        execution_id: The execution ID to check
        current_user: Current authenticated user
        
    Returns:
        Execution status and details
    """
    try:
        execution_result = await orchestrator.get_execution_status(execution_id)
        
        if not execution_result:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Verify user authorization
        if execution_result.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert node results to response format
        node_results = []
        for node_result in execution_result.node_results:
            node_results.append({
                "node_id": node_result.node_id,
                "connector_name": node_result.connector_name,
                "status": node_result.status.value,
                "result": node_result.result,
                "error": node_result.error,
                "started_at": node_result.started_at.isoformat(),
                "completed_at": node_result.completed_at.isoformat() if node_result.completed_at else None,
                "duration_ms": node_result.duration_ms
            })
        
        return ExecutionStatusResponse(
            execution_id=execution_result.execution_id,
            workflow_id=execution_result.workflow_id,
            user_id=execution_result.user_id,
            status=execution_result.status.value,
            started_at=execution_result.started_at,
            completed_at=execution_result.completed_at,
            total_duration_ms=execution_result.total_duration_ms,
            error=execution_result.error,
            node_results=node_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get execution status")


@router.get("/workflow/{workflow_id}", response_model=ExecutionListResponse)
async def list_workflow_executions(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List executions for a specific workflow.
    
    Args:
        workflow_id: The workflow ID
        current_user: Current authenticated user
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        List of workflow executions
    """
    try:
        executions = await orchestrator.list_workflow_executions(
            workflow_id=workflow_id,
            user_id=current_user["id"],
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        execution_responses = []
        for execution in executions:
            execution_responses.append(ExecutionStatusResponse(
                execution_id=execution.execution_id,
                workflow_id=execution.workflow_id,
                user_id=execution.user_id,
                status=execution.status.value,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                total_duration_ms=execution.total_duration_ms,
                error=execution.error,
                node_results=[]  # Don't include detailed node results in list view
            ))
        
        return ExecutionListResponse(
            executions=execution_responses,
            total_count=len(execution_responses),
            has_more=len(execution_responses) == limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list executions")


@router.get("/workflow/{workflow_id}/stats", response_model=ExecutionStatsResponse)
async def get_workflow_execution_stats(
    workflow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get execution statistics for a workflow.
    
    Args:
        workflow_id: The workflow ID
        current_user: Current authenticated user
        
    Returns:
        Execution statistics
    """
    try:
        stats = await orchestrator.get_workflow_execution_stats(
            workflow_id=workflow_id,
            user_id=current_user["id"]
        )
        
        return ExecutionStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get execution stats")


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a running workflow execution.
    
    Args:
        execution_id: The execution ID to cancel
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        success = await orchestrator.cancel_execution(
            execution_id=execution_id,
            user_id=current_user["id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Execution cannot be cancelled (not found, not running, or access denied)"
            )
        
        return {"message": "Execution cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to cancel execution")


@router.get("/{execution_id}/nodes", response_model=List[NodeExecutionResponse])
async def get_execution_node_details(
    execution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed node execution information for an execution.
    
    Args:
        execution_id: The execution ID
        current_user: Current authenticated user
        
    Returns:
        List of node execution details
    """
    try:
        execution_result = await orchestrator.get_execution_status(execution_id)
        
        if not execution_result:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Verify user authorization
        if execution_result.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert node results to response format
        node_responses = []
        for node_result in execution_result.node_results:
            node_responses.append(NodeExecutionResponse(
                node_id=node_result.node_id,
                connector_name=node_result.connector_name,
                status=node_result.status.value,
                result=node_result.result,
                error=node_result.error,
                started_at=node_result.started_at,
                completed_at=node_result.completed_at,
                duration_ms=node_result.duration_ms
            ))
        
        return node_responses
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get node details")


@router.get("/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed execution logs for debugging.
    
    Args:
        execution_id: The execution ID
        current_user: Current authenticated user
        
    Returns:
        Detailed execution logs
    """
    try:
        execution_result = await orchestrator.get_execution_status(execution_id)
        
        if not execution_result:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Verify user authorization
        if execution_result.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build detailed log structure
        logs = {
            "execution_id": execution_id,
            "workflow_id": execution_result.workflow_id,
            "status": execution_result.status.value,
            "started_at": execution_result.started_at.isoformat(),
            "completed_at": execution_result.completed_at.isoformat() if execution_result.completed_at else None,
            "total_duration_ms": execution_result.total_duration_ms,
            "error": execution_result.error,
            "node_logs": []
        }
        
        # Add node-level logs
        for node_result in execution_result.node_results:
            node_log = {
                "node_id": node_result.node_id,
                "connector_name": node_result.connector_name,
                "status": node_result.status.value,
                "started_at": node_result.started_at.isoformat(),
                "completed_at": node_result.completed_at.isoformat() if node_result.completed_at else None,
                "duration_ms": node_result.duration_ms,
                "error": node_result.error,
                "result_summary": {
                    "success": node_result.status == ExecutionStatus.COMPLETED,
                    "data_type": type(node_result.result).__name__ if node_result.result else None,
                    "data_size": len(str(node_result.result)) if node_result.result else 0
                }
            }
            logs["node_logs"].append(node_log)
        
        return logs
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get execution logs")


@router.get("/user/recent")
async def get_recent_executions(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results")
):
    """
    Get recent executions for the current user across all workflows.
    
    Args:
        current_user: Current authenticated user
        limit: Maximum number of results
        
    Returns:
        List of recent executions
    """
    try:
        # This would typically query across all user's workflows
        # For now, return a placeholder response
        return {
            "executions": [],
            "message": "Recent executions endpoint - implementation pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get recent executions")


@router.get("/status/summary")
async def get_execution_status_summary(
    current_user: dict = Depends(get_current_user)
):
    """
    Get a summary of execution statuses across all user workflows.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Execution status summary
    """
    try:
        # This would typically aggregate across all user's workflows
        # For now, return a placeholder response
        return {
            "total_running": 0,
            "total_pending": 0,
            "total_completed_today": 0,
            "total_failed_today": 0,
            "message": "Status summary endpoint - implementation pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get status summary")