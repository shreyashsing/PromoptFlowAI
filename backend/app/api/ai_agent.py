"""
AI Agent API endpoints for intelligent automation creation
"""
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import logging

from app.core.auth import get_current_user
from app.services.ai_workflow_agent import AIWorkflowAgent, AgentStep, MiniApp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai-agent", tags=["AI Agent"])

# Initialize the AI agent
ai_agent = AIWorkflowAgent()

class CreateAutomationRequest(BaseModel):
    """Request to create a new automation from natural language"""
    prompt: str = Field(..., description="Natural language description of the automation")
    session_id: Optional[str] = Field(None, description="Optional session ID for continuing")

class AuthenticationCompleteRequest(BaseModel):
    """Request to signal that authentication is complete"""
    session_id: str = Field(..., description="Session ID")
    connector_name: str = Field(..., description="Name of the authenticated connector")

class ExecuteMiniAppRequest(BaseModel):
    """Request to execute a mini-app"""
    mini_app_id: str = Field(..., description="ID of the mini-app to execute")
    inputs: Dict[str, Any] = Field(..., description="User inputs for the mini-app")

@router.post("/create-automation")
async def create_automation(
    request: CreateAutomationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create an automation from natural language description
    Returns a stream of AI agent steps
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    async def generate_steps():
        try:
            async for step in ai_agent.create_automation(
                user_id=user_id,
                user_prompt=request.prompt,
                session_id=request.session_id
            ):
                # Convert step to JSON and yield
                step_data = {
                    'id': step.id,
                    'type': step.type,
                    'title': step.title,
                    'description': step.description,
                    'connector_needed': step.connector_needed,
                    'auth_required': step.auth_required,
                    'data_generated': step.data_generated,
                    'timestamp': step.timestamp
                }
                yield f"data: {json.dumps(step_data)}\n\n"
                
        except Exception as e:
            logger.error(f"Error in create_automation stream: {e}")
            error_step = {
                'id': 'error',
                'type': 'error',
                'title': 'Error',
                'description': str(e),
                'timestamp': AgentStep(id='', type='', title='', description='').timestamp
            }
            yield f"data: {json.dumps(error_step)}\n\n"
    
    return StreamingResponse(
        generate_steps(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.post("/auth-complete")
async def authentication_complete(
    request: AuthenticationCompleteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Signal that user has completed authentication for a connector
    Returns a stream of remaining steps
    """
    async def generate_steps():
        try:
            async for step in ai_agent.resume_after_auth(
                session_id=request.session_id,
                connector_name=request.connector_name
            ):
                step_data = {
                    'id': step.id,
                    'type': step.type,
                    'title': step.title,
                    'description': step.description,
                    'connector_needed': step.connector_needed,
                    'auth_required': step.auth_required,
                    'data_generated': step.data_generated,
                    'timestamp': step.timestamp
                }
                yield f"data: {json.dumps(step_data)}\n\n"
                
        except Exception as e:
            logger.error(f"Error in auth_complete stream: {e}")
            error_step = {
                'id': 'error',
                'type': 'error',
                'title': 'Error',
                'description': str(e),
                'timestamp': AgentStep(id='', type='', title='', description='').timestamp
            }
            yield f"data: {json.dumps(error_step)}\n\n"
    
    return StreamingResponse(
        generate_steps(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.get("/mini-apps")
async def get_user_mini_apps(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all mini-apps created by the current user
    """
    try:
        from app.core.database import get_supabase_client
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        supabase = get_supabase_client()
        result = supabase.table('mini_apps').select('*').eq('user_id', user_id).execute()
        
        return {
            "success": True,
            "mini_apps": result.data or []
        }
        
    except Exception as e:
        logger.error(f"Error fetching mini-apps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch mini-apps: {str(e)}"
        )

@router.post("/execute-mini-app")
async def execute_mini_app(
    request: ExecuteMiniAppRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Execute a user's mini-app with provided inputs
    Returns a stream of execution steps
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    async def generate_steps():
        try:
            async for step in ai_agent.execute_mini_app(
                user_id=user_id,
                mini_app_id=request.mini_app_id,
                user_inputs=request.inputs
            ):
                step_data = {
                    'id': step.id,
                    'type': step.type,
                    'title': step.title,
                    'description': step.description,
                    'connector_needed': step.connector_needed,
                    'auth_required': step.auth_required,
                    'data_generated': step.data_generated,
                    'timestamp': step.timestamp
                }
                yield f"data: {json.dumps(step_data)}\n\n"
                
        except Exception as e:
            logger.error(f"Error in execute_mini_app stream: {e}")
            error_step = {
                'id': 'error',
                'type': 'error',
                'title': 'Error',
                'description': str(e),
                'timestamp': AgentStep(id='', type='', title='', description='').timestamp
            }
            yield f"data: {json.dumps(error_step)}\n\n"
    
    return StreamingResponse(
        generate_steps(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.delete("/mini-apps/{mini_app_id}")
async def delete_mini_app(
    mini_app_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a user's mini-app
    """
    try:
        from app.core.database import get_supabase_client
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        supabase = get_supabase_client()
        result = supabase.table('mini_apps').delete().eq('id', mini_app_id).eq('user_id', user_id).execute()
        
        return {
            "success": True,
            "message": "Mini-app deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting mini-app: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete mini-app: {str(e)}"
        )
