"""
API endpoints for the conversational agent system.
Handles prompt submission, chat interactions, and workflow planning.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from app.services.conversational_agent import (
    get_conversational_agent,
    ConversationalAgent
)
from app.models.conversation import (
    ConversationContext,
    PlanModificationRequest,
    PlanConfirmationRequest
)
from app.models.base import WorkflowPlan
from app.core.auth import get_current_user
from app.core.exceptions import AgentError, PlanningError
from app.core.error_handler import handle_api_error
from app.core.error_utils import ErrorBoundary, create_error_context
from app.core.monitoring import record_request_time
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# Request/Response models

class PromptRequest(BaseModel):
    """Request model for initial prompt submission."""
    prompt: str = Field(..., min_length=1, max_length=2000, description="User's natural language prompt")
    session_id: Optional[str] = Field(None, description="Optional existing session ID")


class ChatRequest(BaseModel):
    """Request model for chat interactions."""
    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    session_id: str = Field(..., description="Session ID for the conversation")


class AgentResponse(BaseModel):
    """Response model for agent interactions."""
    message: str = Field(..., description="Agent's response message")
    session_id: str = Field(..., description="Session ID")
    conversation_state: str = Field(..., description="Current conversation state")
    current_plan: Optional[WorkflowPlan] = Field(None, description="Current workflow plan if available")


class PlanModificationResponse(BaseModel):
    """Response model for plan modifications."""
    modified_plan: WorkflowPlan = Field(..., description="Modified workflow plan")
    explanation: str = Field(..., description="Explanation of changes made")
    session_id: str = Field(..., description="Session ID")


# API Endpoints

@router.get("/conversations/{session_id}", response_model=Dict[str, Any])
async def get_conversation(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent: ConversationalAgent = Depends(get_conversational_agent)
):
    """
    Load conversation context by session ID.
    
    This endpoint retrieves the conversation history, current workflow plan,
    and conversation state for a given session.
    """
    try:
        logger.info(f"GET conversation request for session: {session_id}, user: {current_user.get('user_id', 'UNKNOWN')}")
        
        # Load conversation context from database
        context = await agent._load_conversation_context(session_id)
        
        if not context:
            logger.warning(f"Conversation not found in database: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {session_id} not found"
            )
        
        # Verify the conversation belongs to the current user
        if context.user_id != current_user["user_id"]:
            logger.warning(f"Access denied: conversation {session_id} belongs to {context.user_id}, not {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        logger.info(f"Successfully retrieved conversation: {session_id} for user {current_user['user_id']}")
        
        # Convert to response format
        return {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                } for msg in context.messages
            ],
            "current_plan": context.current_plan.dict() if context.current_plan else None,
            "state": context.state.value,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading conversation {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load conversation"
        )


@router.post("/run-agent", response_model=AgentResponse)
async def run_agent(
    request: PromptRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent: ConversationalAgent = Depends(get_conversational_agent)
):
    """
    Process initial user prompt and start conversational workflow planning.
    
    This endpoint handles the initial user request and begins the interactive
    workflow planning process. The agent will analyze the prompt, recognize
    intent, and either generate a workflow plan or ask for clarification.
    """
    start_time = time.time()
    user_id = current_user["user_id"]
    
    async with ErrorBoundary(
        operation="run_agent",
        user_id=user_id,
        context=create_error_context(
            user_id=user_id,
            operation="run_agent",
            prompt_length=len(request.prompt),
            session_id=request.session_id
        ),
        reraise=False
    ) as boundary:
        # Process the initial prompt
        context, response = await agent.process_initial_prompt(
            prompt=request.prompt,
            user_id=user_id,
            session_id=request.session_id
        )
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.info(f"Processed initial prompt for user {user_id}, session {context.session_id} in {duration:.3f}s")
        
        return AgentResponse(
            message=response,
            session_id=context.session_id,
            conversation_state=context.state.value,
            current_plan=context.current_plan
        )
    
    # If error occurred, return error response
    if boundary.error_occurred:
        duration = time.time() - start_time
        record_request_time(duration)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=boundary.error_response.get("user_message", "An error occurred processing your request")
        )


@router.post("/chat-agent", response_model=AgentResponse)
async def chat_agent(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent: ConversationalAgent = Depends(get_conversational_agent)
):
    """
    Handle conversational interactions for workflow planning.
    
    This endpoint manages multi-turn conversations where users can:
    - Provide additional information during planning
    - Request modifications to proposed workflow plans
    - Approve or reject workflow plans
    - Ask questions about the planning process
    """
    start_time = time.time()
    user_id = current_user["user_id"]
    
    async with ErrorBoundary(
        operation="chat_agent",
        user_id=user_id,
        context=create_error_context(
            user_id=user_id,
            operation="chat_agent",
            session_id=request.session_id,
            message_length=len(request.message)
        ),
        reraise=False
    ) as boundary:
        # Handle conversation turn
        context, response = await agent.handle_conversation_turn(
            message=request.message,
            session_id=request.session_id
        )
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.info(f"Handled conversation turn for session {request.session_id} in {duration:.3f}s")
        
        return AgentResponse(
            message=response,
            session_id=context.session_id,
            conversation_state=context.state.value,
            current_plan=context.current_plan
        )
    
    # If error occurred, return error response
    if boundary.error_occurred:
        duration = time.time() - start_time
        record_request_time(duration)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=boundary.error_response.get("user_message", "An error occurred during conversation")
        )


@router.post("/modify-plan", response_model=PlanModificationResponse)
async def modify_plan(
    request: PlanModificationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent: ConversationalAgent = Depends(get_conversational_agent)
):
    """
    Modify an existing workflow plan based on user feedback.
    
    This endpoint allows users to request specific changes to a workflow plan.
    The agent will analyze the modification request and update the plan accordingly.
    """
    try:
        # Modify the workflow plan
        modified_plan, explanation = await agent.modify_workflow_plan(request)
        
        logger.info(f"Modified workflow plan for session {request.session_id}")
        
        return PlanModificationResponse(
            modified_plan=modified_plan,
            explanation=explanation,
            session_id=request.session_id
        )
        
    except PlanningError as e:
        logger.error(f"Planning error in modify_plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan modification error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in modify_plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during plan modification"
        )


@router.post("/confirm-plan", response_model=AgentResponse)
async def confirm_plan(
    request: PlanConfirmationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent: ConversationalAgent = Depends(get_conversational_agent)
):
    """
    Confirm or reject a workflow plan.
    
    This endpoint handles user confirmation of workflow plans. If approved,
    the plan is saved and marked as active. If rejected, the conversation
    returns to the planning state for further modifications.
    """
    try:
        # Handle plan confirmation
        context, response = await agent.confirm_workflow_plan(request)
        
        logger.info(f"Handled plan confirmation for session {request.session_id}")
        
        return AgentResponse(
            message=response,
            session_id=context.session_id,
            conversation_state=context.state.value,
            current_plan=context.current_plan
        )
        
    except AgentError as e:
        logger.error(f"Agent error in confirm_plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan confirmation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in confirm_plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during plan confirmation"
        )


@router.get("/conversations", response_model=List[Dict[str, Any]])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent: ConversationalAgent = Depends(get_conversational_agent)
):
    """
    List user's conversations with full context.
    
    This endpoint returns a list of the user's conversation sessions,
    including messages, current state, and workflow plans.
    """
    try:
        from app.core.database import get_database
        
        db = await get_database()
        user_id = current_user["user_id"]
        
        # Get conversations for the user with full data
        result = db.table("conversations").select("*").eq(
            "user_id", user_id
        ).order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
        
        conversations = []
        for row in result.data:
            # Parse messages from JSON
            messages = []
            if row.get("messages"):
                import json
                try:
                    messages_data = json.loads(row["messages"]) if isinstance(row["messages"], str) else row["messages"]
                    for msg_data in messages_data:
                        messages.append({
                            "id": msg_data.get("id", ""),
                            "role": msg_data.get("role", ""),
                            "content": msg_data.get("content", ""),
                            "timestamp": msg_data.get("timestamp", ""),
                            "metadata": msg_data.get("metadata", {})
                        })
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse messages for conversation {row['session_id']}: {e}")
                    messages = []
            
            # Parse current plan from JSON
            current_plan = None
            if row.get("current_plan"):
                import json
                try:
                    current_plan = json.loads(row["current_plan"]) if isinstance(row["current_plan"], str) else row["current_plan"]
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse current_plan for conversation {row['session_id']}: {e}")
                    current_plan = None
            
            conversations.append({
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "messages": messages,
                "current_plan": current_plan,
                "state": row.get("state", "initial"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        
        logger.info(f"Listed {len(conversations)} conversations for user {user_id}")
        
        return conversations
        
    except Exception as e:
        logger.error(f"Unexpected error in list_conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error listing conversations"
        )


@router.delete("/conversations/{session_id}")
async def delete_conversation(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a conversation session.
    
    This endpoint allows users to delete their conversation sessions and
    associated data.
    """
    try:
        from app.core.database import get_database
        
        db = await get_database()
        user_id = current_user["user_id"]
        
        # Verify conversation exists and belongs to user
        result = db.table("conversations").select("user_id").eq("session_id", session_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {session_id} not found"
            )
        
        if result.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        # Delete the conversation
        db.table("conversations").delete().eq("session_id", session_id).execute()
        
        logger.info(f"Deleted conversation {session_id} for user {user_id}")
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error deleting conversation"
        )