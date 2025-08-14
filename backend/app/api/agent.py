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

# Simple in-memory session store for conversational planning
# In production, this should be Redis or database-backed
_session_store: Dict[str, Dict[str, Any]] = {}

async def get_session_context(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session context for conversational planning."""
    return _session_store.get(session_id)

async def store_session_context(session_id: str, context: Dict[str, Any]) -> None:
    """Store session context for conversational planning."""
    _session_store[session_id] = context
    logger.info(f"📝 Stored session context for {session_id}")

async def clear_session_context(session_id: str) -> None:
    """Clear session context."""
    if session_id in _session_store:
        del _session_store[session_id]
        logger.info(f"🗑️ Cleared session context for {session_id}")

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

class PlanResponseRequest(BaseModel):
    response: str = Field(..., description="User response to plan (approve/modify)")
    session_id: str = Field(..., description="Session ID from planning phase")
    current_plan: Dict[str, Any] = Field(..., description="Current plan being responded to")

class TrueReActResponse(BaseModel):
    success: bool
    session_id: str
    message: str
    workflow: Optional[Dict[str, Any]] = None
    reasoning_trace: List[str] = []
    ui_updates: List[Dict[str, Any]] = []
    error: Optional[str] = None
    # New conversational planning fields
    phase: Optional[str] = None  # "planning", "completed", etc.
    plan: Optional[Dict[str, Any]] = None  # Workflow plan for user review
    awaiting_approval: Optional[bool] = None  # Whether waiting for user approval

# Working Endpoints

@router.post("/build-workflow", response_model=WorkflowBuildResponse)
async def build_workflow_with_react(
    request: WorkflowBuildRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Build workflow using ReAct methodology with intelligent conversation handling.
    Now supports conversational interactions, not just workflow creation.
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
        
        # Session context management for conversational planning
        # For now, we'll use a simple in-memory store (in production, use Redis/database)
        session_context = await get_session_context(session_id)
        logger.info(f"🔍 Session context for {session_id}: {session_context is not None}")
        
        # Initialize ui_updates early to avoid variable access errors
        ui_updates = []
        
        # Check if this looks like an approval response WITHOUT session context
        approval_keywords = ['approve', 'approved', 'looks good', 'proceed', 'yes', 'ok', 'correct']
        if request.query.lower().strip() in approval_keywords and not session_context:
            # This is an approval response but no session context exists
            logger.info(f"Detected approval keyword without session context: {request.query}")
            
            return TrueReActResponse(
                success=False,
                session_id=session_id,
                message="It looks like you're trying to approve a workflow plan. However, I don't see a current plan to approve. Please either:\n\n1. Start by describing a new workflow you'd like me to create, or\n2. If you have a plan from a previous conversation, please use the plan approval interface.\n\nWhat workflow would you like me to help you create?",
                error="no_plan_context",
                reasoning_trace=["Approval keyword detected without plan context"],
                ui_updates=ui_updates
            )
        
        # Process with True ReAct Agent (now includes intelligent conversation handling)
        result = await react_agent.process_user_request(request.query, current_user['user_id'], session_context)
        
        # Get UI updates from session
        session_trace = ui_manager.get_session_trace(session_id)
        ui_updates = ui_manager.reasoning_history.get(session_id, [])
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        if result.get("success", False):
            # Handle different phases of the conversational planning system
            phase = result.get("phase", "completed")
            
            if phase == "planning":
                # Planning phase - present plan to user for approval
                logger.info(f"True ReAct planning phase completed for session {session_id} in {duration:.3f}s")
                
                # Store session context for plan approval
                await store_session_context(session_id, {
                    "awaiting_approval": True,
                    "current_plan": result.get("plan"),
                    "original_request": request.query,
                    "user_id": current_user['user_id'],
                    "created_at": time.time()
                })
                
                return TrueReActResponse(
                    success=True,
                    session_id=session_id,
                    message=result.get("message", "Please review the workflow plan"),
                    workflow=None,  # No workflow yet, still in planning
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    # Add planning-specific fields
                    phase=phase,
                    plan=result.get("plan"),
                    awaiting_approval=result.get("awaiting_approval", True)
                )
                
            elif phase == "conversational":
                # Conversational response - return the message directly
                logger.info(f"True ReAct conversational response for session {session_id} in {duration:.3f}s")
                
                return TrueReActResponse(
                    success=True,
                    session_id=session_id,
                    message=result.get("message", "I'm here to help!"),
                    workflow=None,
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase=phase
                )
                
            elif phase == "completed":
                # Execution completed - return final workflow
                logger.info(f"True ReAct workflow completed for session {session_id} in {duration:.3f}s")
                
                # Store executed workflow in session context for future modifications
                await store_session_context(session_id, {
                    "executed_workflow": result.get("workflow"),
                    "original_plan": result.get("plan", {}),
                    "user_id": current_user['user_id'],
                    "completed_at": time.time(),
                    "awaiting_approval": False  # No longer awaiting approval
                })
                
                return TrueReActResponse(
                    success=True,
                    session_id=session_id,
                    message="Workflow created successfully! You can now request modifications if needed.",
                    workflow=result.get("workflow"),
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase=phase
                )
            elif phase == "modified":
                # Workflow was modified post-execution - persist the latest workflow in session
                logger.info(f"True ReAct phase 'modified' completed for session {session_id} in {duration:.3f}s")

                # Persist modified workflow so subsequent modification requests maintain context
                await store_session_context(session_id, {
                    "executed_workflow": result.get("workflow"),
                    "original_plan": result.get("plan", {}),
                    "user_id": current_user['user_id'],
                    "updated_at": time.time(),
                    "awaiting_approval": False
                })

                return TrueReActResponse(
                    success=True,
                    session_id=session_id,
                    message=result.get("message", "Workflow modified successfully."),
                    workflow=result.get("workflow"),
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase=phase,
                    plan=result.get("plan")
                )

            else:
                # Unknown phase, return what we have
                logger.info(f"True ReAct phase '{phase}' completed for session {session_id} in {duration:.3f}s")
                
                return TrueReActResponse(
                    success=True,
                    session_id=session_id,
                    message=result.get("message", "Workflow processing in progress"),
                    workflow=result.get("workflow"),
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase=phase
                )
        else:
            # Handle different types of failures
            error_type = result.get("error", "Unknown error")
            is_conversational = result.get("is_conversational", False)
            
            if error_type == "no_plan_context":
                # Special handling for approval without context
                logger.info(f"Approval without plan context detected: {request.query}")
                message = result.get("message", "Please start by describing what workflow you'd like me to create.")
            elif is_conversational:
                # For conversational/greeting messages, return the intelligent response
                logger.info(f"Conversational request detected: {request.query}")
                message = result.get("message", "This appears to be a conversational message. How can I help you create a workflow?")
                
                # For conversational responses, we actually want to return success=True
                # since this is the intended behavior, not an error
                return TrueReActResponse(
                    success=True,
                    session_id=session_id,
                    message=message,
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase="conversational"
                )
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


@router.post("/true-react/plan-response", response_model=TrueReActResponse)
async def handle_plan_response(
    request: PlanResponseRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Handle user response to workflow plan (approve/modify).
    """
    start_time = time.time()
    
    try:
        logger.info(f"Handling plan response for user {current_user['user_id']}: {request.response}")
        
        # Initialize True ReAct Agent
        react_agent = TrueReActAgent()
        await react_agent.initialize()
        
        # Initialize UI Manager for real-time updates
        ui_manager = ReActUIManager()
        
        # Handle user response
        result = await react_agent.handle_user_response(
            request.response, 
            current_user['user_id'], 
            request.current_plan
        )
        
        # Get UI updates from session
        ui_updates = ui_manager.reasoning_history.get(request.session_id, [])
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        if result["success"]:
            phase = result.get("phase", "completed")
            
            if phase == "planning":
                # Still in planning phase - plan was modified
                logger.info(f"Plan modified for session {request.session_id} in {duration:.3f}s")
                
                return TrueReActResponse(
                    success=True,
                    session_id=request.session_id,
                    message=result.get("message", "Plan updated based on your feedback"),
                    workflow=None,
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase=phase,
                    plan=result.get("plan"),
                    awaiting_approval=result.get("awaiting_approval", True)
                )
                
            elif phase == "completed":
                # Plan was approved and executed
                logger.info(f"Plan approved and executed for session {request.session_id} in {duration:.3f}s")
                
                # Store executed workflow in session context for future modifications
                await store_session_context(request.session_id, {
                    "executed_workflow": result.get("workflow"),
                    "original_plan": request.current_plan,
                    "user_id": current_user['user_id'],
                    "completed_at": time.time(),
                    "awaiting_approval": False  # No longer awaiting approval
                })
                
                return TrueReActResponse(
                    success=True,
                    session_id=request.session_id,
                    message="Workflow created successfully! You can now request modifications if needed.",
                    workflow=result.get("workflow"),
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase=phase
                )
            
            else:
                # Other phase
                return TrueReActResponse(
                    success=True,
                    session_id=request.session_id,
                    message=result.get("message", "Processing your response"),
                    workflow=result.get("workflow"),
                    reasoning_trace=result.get("reasoning_trace", []),
                    ui_updates=ui_updates,
                    phase=phase
                )
        
        else:
            # Handle error
            logger.error(f"Plan response handling failed: {result.get('error', 'Unknown error')}")
            
            return TrueReActResponse(
                success=False,
                session_id=request.session_id,
                message=result.get("message", "Failed to process your response"),
                error=result.get("error"),
                reasoning_trace=result.get("reasoning_trace", []),
                ui_updates=ui_updates
            )
            
    except Exception as e:
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.error(f"Error handling plan response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle plan response: {str(e)}"
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