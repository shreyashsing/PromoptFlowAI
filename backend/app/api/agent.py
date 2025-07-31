"""
Clean API endpoints for the True ReAct Agent system.
Only includes working endpoints without old conversational agent dependencies.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import json
import time

from app.services.integrated_workflow_agent import IntegratedWorkflowAgent
from app.services.true_react_agent import TrueReActAgent
from app.services.react_ui_manager import ReActUIManager
from app.services.react_agent_service import get_react_agent_service
from app.models.conversation import ConversationContext
from app.models.base import WorkflowPlan, ConversationState
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.exceptions import AgentError, PlanningError
from app.core.error_handler import handle_api_error
from app.core.error_utils import ErrorBoundary, create_error_context
from app.core.monitoring import record_request_time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# Request/Response Models
class WorkflowBuildRequest(BaseModel):
    query: str = Field(..., description="User's workflow request")
    session_id: Optional[str] = Field(None, description="Session ID for continuation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class WorkflowBuildResponse(BaseModel):
    message: str
    session_id: str
    conversation_state: str
    workflow_plan: Optional[Dict[str, Any]] = None
    reasoning: Optional[Dict[str, Any]] = None
    next_steps: List[str] = []

class ContinueWorkflowRequest(BaseModel):
    message: str = Field(..., description="User's response or input")
    session_id: str = Field(..., description="Session ID to continue")

class TrueReActRequest(BaseModel):
    query: str = Field(..., description="User's workflow request")
    session_id: Optional[str] = Field(None, description="Session ID for continuation")

class TrueReActResponse(BaseModel):
    success: bool
    session_id: str
    message: str
    workflow: Optional[Dict[str, Any]] = None
    reasoning_trace: List[str] = []
    ui_updates: List[Dict[str, Any]] = []
    error: Optional[str] = None

# Working Endpoints

@router.post("/build-workflow", response_model=WorkflowBuildResponse)
async def build_workflow_with_react(
    request: WorkflowBuildRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Build workflow using ReAct methodology with integrated workflow agent.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting ReAct workflow building for user {current_user['user_id']}: {request.query}")
        
        # Initialize integrated workflow agent
        agent = IntegratedWorkflowAgent()
        await agent.initialize()
        
        # Create conversation context
        conversation_context = ConversationContext(
            session_id=request.session_id or f"session_{int(time.time())}",
            user_id=current_user['user_id'],
            messages=[request.query],
            state=ConversationState.PLANNING,
            context=request.context or {}
        )
        
        # Build workflow conversationally
        response_message, workflow_plan = await agent.create_workflow_conversationally(
            request.query, conversation_context
        )
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.info(f"Started ReAct workflow building for session {conversation_context.session_id} in {duration:.3f}s")
        
        return WorkflowBuildResponse(
            message=response_message,
            session_id=conversation_context.session_id,
            conversation_state=conversation_context.state.value,
            workflow_plan=workflow_plan.dict() if workflow_plan else None,
            reasoning={"processing_time_ms": int(duration * 1000)},
            next_steps=["Continue conversation", "Approve plan", "Request modifications"]
        )
        
    except Exception as e:
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.error(f"Error starting ReAct workflow building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow building: {str(e)}"
        )

@router.post("/continue-workflow-build", response_model=WorkflowBuildResponse)
async def continue_workflow_build(
    request: ContinueWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Continue building workflow with user input.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Continuing ReAct workflow building for session {request.session_id}")
        
        # Initialize integrated workflow agent
        agent = IntegratedWorkflowAgent()
        await agent.initialize()
        
        # Load conversation context (simplified for now)
        conversation_context = ConversationContext(
            session_id=request.session_id,
            user_id=current_user['user_id'],
            messages=[request.message],
            state=ConversationState.CONFIGURING,
            context={}
        )
        
        # Continue workflow building
        response_message, workflow_plan = await agent.continue_workflow_building(
            request.message, conversation_context
        )
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.info(f"Continued ReAct workflow building for session {request.session_id} in {duration:.3f}s")
        
        return WorkflowBuildResponse(
            message=response_message,
            session_id=conversation_context.session_id,
            conversation_state=conversation_context.state.value,
            workflow_plan=workflow_plan.dict() if workflow_plan else None,
            reasoning={"processing_time_ms": int(duration * 1000)},
            next_steps=["Continue", "Finalize", "Modify"]
        )
        
    except Exception as e:
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.error(f"Error continuing ReAct workflow building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to continue workflow building: {str(e)}"
        )

@router.post("/true-react/build-workflow", response_model=TrueReActResponse)
async def build_workflow_with_true_react(
    request: TrueReActRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Build workflow using True ReAct Agent with real-time UI updates.
    This is the new String Alpha-style workflow building.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting True ReAct workflow building for user {current_user['user_id']}: {request.query}")
        
        # Initialize True ReAct Agent
        react_agent = TrueReActAgent()
        await react_agent.initialize()
        
        # Initialize UI Manager for real-time updates
        ui_manager = ReActUIManager()
        session_id = request.session_id or f"react_{int(time.time())}"
        
        # Start UI session
        await ui_manager.start_session(session_id, request.query)
        
        # Process with True ReAct Agent
        result = await react_agent.process_user_request(request.query, current_user['user_id'])
        
        # Get UI updates from session
        session_trace = ui_manager.get_session_trace(session_id)
        ui_updates = ui_manager.reasoning_history.get(session_id, [])
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        if result["success"]:
            logger.info(f"True ReAct workflow completed for session {session_id} in {duration:.3f}s")
            
            return TrueReActResponse(
                success=True,
                session_id=session_id,
                message="Workflow created successfully using True ReAct Agent!",
                workflow=result["workflow"],
                reasoning_trace=result.get("reasoning_trace", []),
                ui_updates=ui_updates
            )
        else:
            # Handle different types of failures
            error_type = result.get("error", "Unknown error")
            is_conversational = result.get("is_conversational", False)
            
            if is_conversational:
                # For conversational/greeting messages, return a helpful response
                logger.info(f"Conversational request detected: {request.query}")
                message = result.get("message", "This appears to be a conversational message. How can I help you create a workflow?")
            else:
                # For actual errors
                logger.error(f"True ReAct workflow failed: {error_type}")
                message = result.get("message", "Failed to create workflow")
            
            return TrueReActResponse(
                success=False,
                session_id=session_id,
                message=message,
                error=error_type,
                reasoning_trace=result.get("reasoning_trace", []),
                ui_updates=ui_updates
            )
            
    except Exception as e:
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.error(f"Error in True ReAct workflow building: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build workflow with True ReAct Agent: {str(e)}"
        )

@router.get("/true-react/session/{session_id}/updates")
async def get_session_updates(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get real-time updates for a True ReAct session.
    Used for polling-based real-time updates.
    """
    try:
        ui_manager = ReActUIManager()
        session_trace = ui_manager.get_session_trace(session_id)
        ui_updates = ui_manager.reasoning_history.get(session_id, [])
        
        return {
            "session_id": session_id,
            "updates": ui_updates,
            "session_info": session_trace.get("session_info", {}),
            "reasoning_trace": session_trace.get("reasoning_trace", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting session updates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session updates: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "true-react-agent"}