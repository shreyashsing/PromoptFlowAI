"""
API endpoints for workflow management.

This module provides REST endpoints for:
- Creating, updating, and deleting workflows
- Listing user workflows
- Managing workflow status and configuration
- Executing workflows
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4
import time

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_supabase_client
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, Trigger, WorkflowStatus
from app.services.workflow_orchestrator import WorkflowOrchestrator
from app.models.execution import ExecutionResult
from app.core.error_handler import handle_api_error
from app.core.error_utils import ErrorBoundary, create_error_context, handle_database_errors
from app.core.monitoring import record_request_time
from app.core.exceptions import WorkflowException, ValidationException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Global orchestrator instance
orchestrator = WorkflowOrchestrator()


# Request/Response models

class CreateWorkflowRequest(BaseModel):
    """Request model for creating a new workflow."""
    name: str = Field(..., min_length=1, max_length=100, description="Workflow name")
    description: str = Field("", max_length=500, description="Workflow description")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    edges: List[WorkflowEdge] = Field(default_factory=list, description="Workflow edges")
    triggers: List[Trigger] = Field(default_factory=list, description="Workflow triggers")


class UpdateWorkflowRequest(BaseModel):
    """Request model for updating an existing workflow."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Workflow name")
    description: Optional[str] = Field(None, max_length=500, description="Workflow description")
    nodes: Optional[List[WorkflowNode]] = Field(None, description="Workflow nodes")
    edges: Optional[List[WorkflowEdge]] = Field(None, description="Workflow edges")
    triggers: Optional[List[Trigger]] = Field(None, description="Workflow triggers")
    status: Optional[WorkflowStatus] = Field(None, description="Workflow status")


class WorkflowResponse(BaseModel):
    """Response model for workflow data."""
    id: str
    user_id: str
    name: str
    description: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    triggers: List[Trigger]
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    """Response model for workflow list."""
    workflows: List[WorkflowResponse]
    total_count: int
    has_more: bool


class ExecuteWorkflowRequest(BaseModel):
    """Request model for executing a workflow."""
    trigger_type: str = Field("manual", description="Type of trigger (manual, schedule, webhook)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")


# API Endpoints

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
@handle_database_errors("create_workflow")
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new workflow.
    
    This endpoint allows users to create new workflow definitions with nodes,
    edges, and triggers. The workflow is initially created in DRAFT status.
    """
    start_time = time.time()
    user_id = current_user["user_id"]
    
    async with ErrorBoundary(
        operation="create_workflow",
        user_id=user_id,
        context=create_error_context(
            user_id=user_id,
            operation="create_workflow",
            workflow_name=request.name,
            nodes_count=len(request.nodes),
            edges_count=len(request.edges)
        ),
        reraise=False
    ) as boundary:
        # Validate workflow structure
        if request.nodes and request.edges:
            node_ids = {node.id for node in request.nodes}
            for edge in request.edges:
                if edge.source not in node_ids or edge.target not in node_ids:
                    raise ValidationException(
                        f"Edge references non-existent node: {edge.source} -> {edge.target}",
                        field="edges"
                    )
        
        workflow_id = str(uuid4())
        now = datetime.utcnow()
        
        # Create workflow plan
        workflow = WorkflowPlan(
            id=workflow_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
            triggers=request.triggers,
            status=getattr(request, 'status', WorkflowStatus.ACTIVE),  # Use request status or default to ACTIVE
            created_at=now,
            updated_at=now
        )
        
        # Store in database
        supabase = get_supabase_client()
        workflow_data = {
            "id": workflow.id,
            "user_id": workflow.user_id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": [node.dict() for node in workflow.nodes],
            "edges": [edge.dict() for edge in workflow.edges],
            "triggers": [trigger.dict() for trigger in workflow.triggers],
            "status": workflow.status.value,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat()
        }
        
        response = supabase.table("workflows").insert(workflow_data).execute()
        
        if not response.data:
            raise WorkflowException(
                f"Failed to create workflow '{request.name}'",
                details={"workflow_name": request.name}
            )
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.info(f"Created workflow {workflow_id} for user {user_id} in {duration:.3f}s")
        
        return WorkflowResponse(**workflow.dict())
    
    # If error occurred, return error response
    if boundary.error_occurred:
        duration = time.time() - start_time
        record_request_time(duration)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=boundary.error_response.get("user_message", "Failed to create workflow")
        )


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    status_filter: Optional[WorkflowStatus] = Query(None, description="Filter by workflow status")
):
    """
    List user's workflows.
    
    This endpoint returns a paginated list of workflows owned by the current user,
    with optional filtering by status.
    """
    try:
        supabase = get_supabase_client()
        user_id = current_user["user_id"]
        
        # Build query
        query = supabase.table("workflows").select("*").eq("user_id", user_id)
        
        if status_filter:
            query = query.eq("status", status_filter.value)
        
        # Execute query with pagination
        response = query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
        
        workflows = []
        if response.data:
            for workflow_data in response.data:
                # Convert database record to WorkflowResponse
                workflow = WorkflowResponse(
                    id=workflow_data["id"],
                    user_id=workflow_data["user_id"],
                    name=workflow_data["name"],
                    description=workflow_data["description"],
                    nodes=[WorkflowNode(**node) for node in workflow_data["nodes"]],
                    edges=[WorkflowEdge(**edge) for edge in workflow_data["edges"]],
                    triggers=[Trigger(**trigger) for trigger in workflow_data["triggers"]],
                    status=WorkflowStatus(workflow_data["status"]),
                    created_at=datetime.fromisoformat(workflow_data["created_at"]),
                    updated_at=datetime.fromisoformat(workflow_data["updated_at"])
                )
                workflows.append(workflow)
        
        logger.info(f"Listed {len(workflows)} workflows for user {user_id}")
        
        return WorkflowListResponse(
            workflows=workflows,
            total_count=len(workflows),
            has_more=len(workflows) == limit
        )
        
    except Exception as e:
        logger.error(f"Error listing workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error listing workflows"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific workflow by ID.
    
    This endpoint returns the complete workflow definition including nodes,
    edges, and triggers.
    """
    try:
        supabase = get_supabase_client()
        user_id = current_user["user_id"]
        
        # Get workflow from database
        response = supabase.table("workflows").select("*").eq("id", workflow_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        workflow_data = response.data[0]
        
        # Convert to WorkflowResponse
        workflow = WorkflowResponse(
            id=workflow_data["id"],
            user_id=workflow_data["user_id"],
            name=workflow_data["name"],
            description=workflow_data["description"],
            nodes=[WorkflowNode(**node) for node in workflow_data["nodes"]],
            edges=[WorkflowEdge(**edge) for edge in workflow_data["edges"]],
            triggers=[Trigger(**trigger) for trigger in workflow_data["triggers"]],
            status=WorkflowStatus(workflow_data["status"]),
            created_at=datetime.fromisoformat(workflow_data["created_at"]),
            updated_at=datetime.fromisoformat(workflow_data["updated_at"])
        )
        
        logger.info(f"Retrieved workflow {workflow_id} for user {user_id}")
        
        return workflow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving workflow"
        )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an existing workflow.
    
    This endpoint allows users to update workflow properties including name,
    description, nodes, edges, triggers, and status.
    """
    try:
        supabase = get_supabase_client()
        user_id = current_user["user_id"]
        
        # Get existing workflow
        response = supabase.table("workflows").select("*").eq("id", workflow_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        existing_data = response.data[0]
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.nodes is not None:
            update_data["nodes"] = [node.dict() for node in request.nodes]
        if request.edges is not None:
            update_data["edges"] = [edge.dict() for edge in request.edges]
        if request.triggers is not None:
            update_data["triggers"] = [trigger.dict() for trigger in request.triggers]
        if request.status is not None:
            update_data["status"] = request.status.value
        
        # Update in database
        response = supabase.table("workflows").update(update_data).eq("id", workflow_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update workflow"
            )
        
        updated_data = response.data[0]
        
        # Convert to WorkflowResponse
        workflow = WorkflowResponse(
            id=updated_data["id"],
            user_id=updated_data["user_id"],
            name=updated_data["name"],
            description=updated_data["description"],
            nodes=[WorkflowNode(**node) for node in updated_data["nodes"]],
            edges=[WorkflowEdge(**edge) for edge in updated_data["edges"]],
            triggers=[Trigger(**trigger) for trigger in updated_data["triggers"]],
            status=WorkflowStatus(updated_data["status"]),
            created_at=datetime.fromisoformat(updated_data["created_at"]),
            updated_at=datetime.fromisoformat(updated_data["updated_at"])
        )
        
        logger.info(f"Updated workflow {workflow_id} for user {user_id}")
        
        return workflow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error updating workflow"
        )


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a workflow.
    
    This endpoint allows users to delete their workflows. The workflow and
    all associated execution history will be removed.
    """
    try:
        supabase = get_supabase_client()
        user_id = current_user["user_id"]
        
        # Verify workflow exists and belongs to user
        response = supabase.table("workflows").select("id").eq("id", workflow_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Delete workflow executions first (foreign key constraint)
        supabase.table("workflow_executions").delete().eq("workflow_id", workflow_id).execute()
        
        # Delete the workflow
        response = supabase.table("workflows").delete().eq("id", workflow_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete workflow"
            )
        
        logger.info(f"Deleted workflow {workflow_id} for user {user_id}")
        
        return {"message": "Workflow deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error deleting workflow"
        )


@router.post("/{workflow_id}/execute", response_model=Dict[str, Any])
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Execute a workflow.
    
    This endpoint starts execution of a workflow. The workflow must be in
    ACTIVE status to be executed.
    """
    try:
        supabase = get_supabase_client()
        user_id = current_user["user_id"]
        
        # Get workflow from database
        response = supabase.table("workflows").select("*").eq("id", workflow_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        workflow_data = response.data[0]
        
        # Check workflow status
        if workflow_data["status"] != WorkflowStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow must be ACTIVE to execute (current status: {workflow_data['status']})"
            )
        
        # Convert to WorkflowPlan
        workflow = WorkflowPlan(
            id=workflow_data["id"],
            user_id=workflow_data["user_id"],
            name=workflow_data["name"],
            description=workflow_data["description"],
            nodes=[WorkflowNode(**node) for node in workflow_data["nodes"]],
            edges=[WorkflowEdge(**edge) for edge in workflow_data["edges"]],
            triggers=[Trigger(**trigger) for trigger in workflow_data["triggers"]],
            status=WorkflowStatus(workflow_data["status"]),
            created_at=datetime.fromisoformat(workflow_data["created_at"]),
            updated_at=datetime.fromisoformat(workflow_data["updated_at"])
        )
        
        # Execute the workflow
        execution_result = await orchestrator.execute_workflow(workflow)
        
        logger.info(f"Started execution {execution_result.execution_id} for workflow {workflow_id}")
        
        return {
            "execution_id": execution_result.execution_id,
            "status": execution_result.status.value,
            "started_at": execution_result.started_at.isoformat(),
            "message": "Workflow execution started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error executing workflow"
        )


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List executions for a specific workflow.
    
    This endpoint returns execution history for a workflow with pagination.
    """
    try:
        user_id = current_user["user_id"]
        
        # Verify workflow exists and belongs to user
        supabase = get_supabase_client()
        response = supabase.table("workflows").select("id").eq("id", workflow_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Get executions using orchestrator
        executions = await orchestrator.list_workflow_executions(
            workflow_id=workflow_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        execution_list = []
        for execution in executions:
            execution_list.append({
                "execution_id": execution.execution_id,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "duration_ms": execution.total_duration_ms,
                "error": execution.error
            })
        
        logger.info(f"Listed {len(execution_list)} executions for workflow {workflow_id}")
        
        return {
            "executions": execution_list,
            "total_count": len(execution_list),
            "has_more": len(execution_list) == limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing workflow executions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error listing executions"
        )


@router.get("/{workflow_id}/stats")
async def get_workflow_stats(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get execution statistics for a workflow.
    
    This endpoint returns execution statistics including success rate,
    average duration, and status counts.
    """
    try:
        user_id = current_user["user_id"]
        
        # Verify workflow exists and belongs to user
        supabase = get_supabase_client()
        response = supabase.table("workflows").select("id").eq("id", workflow_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Get stats using orchestrator
        stats = await orchestrator.get_workflow_execution_stats(
            workflow_id=workflow_id,
            user_id=user_id
        )
        
        logger.info(f"Retrieved stats for workflow {workflow_id}")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting workflow stats"
        )