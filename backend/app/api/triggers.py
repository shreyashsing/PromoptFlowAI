"""
API endpoints for workflow trigger management.

This module provides REST endpoints for:
- Creating and managing workflow triggers
- Processing webhook requests
- Monitoring trigger status and execution history
"""
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.auth import get_current_user
from app.models.base import Trigger
from app.services.trigger_system import get_trigger_system, TriggerType
from app.core.exceptions import TriggerException


router = APIRouter(prefix="/api/triggers", tags=["triggers"])

class CreateTriggerRequest(BaseModel):
    """Request model for creating a trigger."""
    workflow_id: str
    trigger_type: str = Field(..., description="Type of trigger: 'schedule' or 'webhook'")
    config: Dict[str, Any] = Field(..., description="Trigger configuration")


class UpdateTriggerRequest(BaseModel):
    """Request model for updating a trigger."""
    config: Dict[str, Any] = Field(..., description="Updated trigger configuration")


class TriggerResponse(BaseModel):
    """Response model for trigger operations."""
    trigger_id: str
    workflow_id: str
    trigger_type: str
    config: Dict[str, Any]
    enabled: bool
    created_at: datetime


class TriggerStatusResponse(BaseModel):
    """Response model for trigger status."""
    trigger_id: str
    is_active: bool
    enabled: bool
    trigger_type: Optional[str]
    recent_executions: List[Dict[str, Any]]
    next_execution: Optional[str]


class WebhookResponse(BaseModel):
    """Response model for webhook processing."""
    status: str
    execution_id: str
    message: str


@router.post("/create", response_model=TriggerResponse)
async def create_trigger(
    request: CreateTriggerRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new workflow trigger.
    
    Args:
        request: Trigger creation request
        current_user: Current authenticated user
        
    Returns:
        Created trigger information
    """
    try:
        # Validate trigger type
        if request.trigger_type not in [TriggerType.SCHEDULE, TriggerType.WEBHOOK]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid trigger type: {request.trigger_type}"
            )
        
        # Get trigger system and create trigger
        trigger_system = await get_trigger_system()
        trigger = await trigger_system.create_trigger(
            workflow_id=request.workflow_id,
            user_id=current_user["id"],
            trigger_type=request.trigger_type,
            config=request.config
        )
        
        return TriggerResponse(
            trigger_id=trigger.id,
            workflow_id=request.workflow_id,
            trigger_type=trigger.type,
            config=trigger.config,
            enabled=trigger.enabled,
            created_at=datetime.utcnow()
        )
        
    except TriggerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create trigger")


@router.put("/{workflow_id}/{trigger_id}", response_model=TriggerResponse)
async def update_trigger(
    workflow_id: str,
    trigger_id: str,
    request: UpdateTriggerRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing trigger.
    
    Args:
        workflow_id: The workflow ID
        trigger_id: The trigger ID to update
        request: Trigger update request
        current_user: Current authenticated user
        
    Returns:
        Updated trigger information
    """
    try:
        # Get trigger system and update trigger
        trigger_system = await get_trigger_system()
        trigger = await trigger_system.update_trigger(
            workflow_id=workflow_id,
            trigger_id=trigger_id,
            config=request.config
        )
        
        return TriggerResponse(
            trigger_id=trigger.id,
            workflow_id=workflow_id,
            trigger_type=trigger.type,
            config=trigger.config,
            enabled=trigger.enabled,
            created_at=datetime.utcnow()
        )
        
    except TriggerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update trigger")


@router.delete("/{workflow_id}/{trigger_id}")
async def delete_trigger(
    workflow_id: str,
    trigger_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a trigger.
    
    Args:
        workflow_id: The workflow ID
        trigger_id: The trigger ID to delete
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        trigger_system = await get_trigger_system()
        await trigger_system.delete_trigger(workflow_id, trigger_id)
        return {"message": "Trigger deleted successfully"}
        
    except TriggerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete trigger")


@router.post("/{workflow_id}/{trigger_id}/enable")
async def enable_trigger(
    workflow_id: str,
    trigger_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Enable a disabled trigger.
    
    Args:
        workflow_id: The workflow ID
        trigger_id: The trigger ID to enable
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        trigger_system = await get_trigger_system()
        await trigger_system.enable_trigger(workflow_id, trigger_id)
        return {"message": "Trigger enabled successfully"}
        
    except TriggerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to enable trigger")


@router.post("/{workflow_id}/{trigger_id}/disable")
async def disable_trigger(
    workflow_id: str,
    trigger_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Disable an active trigger.
    
    Args:
        workflow_id: The workflow ID
        trigger_id: The trigger ID to disable
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        trigger_system = await get_trigger_system()
        await trigger_system.disable_trigger(workflow_id, trigger_id)
        return {"message": "Trigger disabled successfully"}
        
    except TriggerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to disable trigger")


@router.get("/{trigger_id}/status", response_model=TriggerStatusResponse)
async def get_trigger_status(
    trigger_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a trigger.
    
    Args:
        trigger_id: The trigger ID
        current_user: Current authenticated user
        
    Returns:
        Trigger status information
    """
    try:
        trigger_system = await get_trigger_system()
        status = await trigger_system.get_trigger_status(trigger_id)
        
        return TriggerStatusResponse(
            trigger_id=trigger_id,
            is_active=status["is_active"],
            enabled=status["enabled"],
            trigger_type=status["type"],
            recent_executions=status["recent_executions"],
            next_execution=status["next_execution"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get trigger status")


@router.post("/webhook/{webhook_id}", response_model=WebhookResponse)
async def process_webhook(
    webhook_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Process an incoming webhook request.
    
    Args:
        webhook_id: The webhook identifier
        request: The incoming HTTP request
        background_tasks: Background task manager
        
    Returns:
        Webhook processing result
    """
    try:
        # Get request payload and headers
        payload = await request.json() if request.headers.get("content-type") == "application/json" else {}
        headers = dict(request.headers)
        
        # Get trigger system and process webhook
        trigger_system = await get_trigger_system()
        result = await trigger_system.process_webhook(
            webhook_id=webhook_id,
            payload=payload,
            headers=headers
        )
        
        return WebhookResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/webhook/{webhook_id}/info")
async def get_webhook_info(
    webhook_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get information about a webhook trigger.
    
    Args:
        webhook_id: The webhook identifier
        current_user: Current authenticated user
        
    Returns:
        Webhook information
    """
    try:
        # This would typically return webhook configuration and recent activity
        # For now, return basic info
        return {
            "webhook_id": webhook_id,
            "url": f"/api/triggers/webhook/{webhook_id}",
            "status": "active",
            "message": "Webhook endpoint is ready to receive requests"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get webhook info")


# Example trigger configurations for documentation
@router.get("/examples/schedule")
async def get_schedule_trigger_example():
    """Get example configuration for schedule triggers."""
    return {
        "trigger_type": "schedule",
        "config": {
            "cron_expression": "0 9 * * 1-5",  # Every weekday at 9 AM
            "timezone": "UTC",
            "enabled": True,
            "max_executions": None
        },
        "description": "Runs every weekday at 9 AM UTC"
    }


@router.get("/examples/webhook")
async def get_webhook_trigger_example():
    """Get example configuration for webhook triggers."""
    return {
        "trigger_type": "webhook",
        "config": {
            "webhook_id": "my-webhook-123",
            "secret_token": "optional-secret-token",
            "enabled": True,
            "allowed_origins": ["https://example.com"],
            "headers_validation": {
                "x-api-key": "expected-api-key-value"
            }
        },
        "description": "Webhook endpoint with optional authentication and validation"
    }