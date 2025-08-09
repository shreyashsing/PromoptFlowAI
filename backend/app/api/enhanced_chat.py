"""
Enhanced Chat API with event-driven execution and context preservation
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import json
import uuid
import asyncio
from datetime import datetime

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.base import User
from ..models.conversation import Conversation, Message
from ..services.true_react_agent import TrueReactAgent
from ..services.context_manager import EnhancedContextManager
from ..services.event_driven_executor import EventDrivenExecutor

router = APIRouter()

class EnhancedChatRequest:
    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        preserve_context: bool = True,
        enable_reasoning: bool = True,
        mode: str = "react"
    ):
        self.message = message
        self.context = context
        self.preserve_context = preserve_context
        self.enable_reasoning = enable_reasoning
        self.mode = mode

class EnhancedChatResponse:
    def __init__(
        self,
        response: str,
        reasoning_trace: List[Dict[str, Any]] = None,
        tool_calls: List[Dict[str, Any]] = None,
        waiting_for_user: bool = False,
        user_input_required: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        execution_time_ms: int = 0,
        session_id: Optional[str] = None
    ):
        self.response = response
        self.reasoning_trace = reasoning_trace or []
        self.tool_calls = tool_calls or []
        self.waiting_for_user = waiting_for_user
        self.user_input_required = user_input_required
        self.context = context
        self.execution_time_ms = execution_time_ms
        self.session_id = session_id

# Global context manager for maintaining long-term context
context_manager = EnhancedContextManager()
event_executor = EventDrivenExecutor()

@router.post("/api/v1/react/enhanced-chat")
async def enhanced_react_chat(
    request_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enhanced ReAct chat with event-driven execution and context preservation
    """
    try:
        start_time = datetime.now()
        
        # Parse request
        message = request_data.get("message", "")
        context = request_data.get("context")
        preserve_context = request_data.get("preserve_context", True)
        enable_reasoning = request_data.get("enable_reasoning", True)
        mode = request_data.get("mode", "react")
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Get or create conversation context
        session_id = None
        if context and context.get("id"):
            session_id = context["id"]
        else:
            session_id = str(uuid.uuid4())
        
        # Initialize or retrieve context
        conversation_context = context_manager.get_or_create_context(
            session_id=session_id,
            user_id=current_user.id,
            preserve_context=preserve_context
        )
        
        # Initialize ReAct agent with enhanced capabilities
        agent = TrueReactAgent(
            user_id=current_user.id,
            session_id=session_id,
            enable_reasoning=enable_reasoning,
            context_manager=context_manager
        )
        
        # Check if this is a continuation of a paused execution
        if conversation_context.get("paused_execution"):
            # Resume from paused state
            result = await event_executor.resume_execution(
                session_id=session_id,
                user_input=message,
                context=conversation_context
            )
        else:
            # Start new execution
            result = await event_executor.execute_with_pause_capability(
                agent=agent,
                query=message,
                context=conversation_context
            )
        
        # Update context
        if preserve_context:
            context_manager.update_context(
                session_id=session_id,
                new_data={
                    "last_message": message,
                    "last_response": result.get("response", ""),
                    "reasoning_trace": result.get("reasoning_trace", []),
                    "tool_calls": result.get("tool_calls", []),
                    "paused_execution": result.get("waiting_for_user", False),
                    "pause_reason": result.get("user_input_required"),
                    "updated_at": datetime.now().isoformat()
                }
            )
        
        # Save to database
        conversation = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            conversation = Conversation(
                session_id=session_id,
                user_id=current_user.id,
                title=message[:50] + "..." if len(message) > 50 else message,
                mode=mode
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            content=message,
            role="user",
            metadata={}
        )
        db.add(user_message)
        
        # Save assistant response
        assistant_message = Message(
            conversation_id=conversation.id,
            content=result.get("response", ""),
            role="assistant",
            metadata={
                "reasoning_trace": result.get("reasoning_trace", []),
                "tool_calls": result.get("tool_calls", []),
                "waiting_for_user": result.get("waiting_for_user", False),
                "user_input_required": result.get("user_input_required"),
                "execution_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
        )
        db.add(assistant_message)
        db.commit()
        
        # Prepare response
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        response = {
            "response": result.get("response", ""),
            "reasoning_trace": result.get("reasoning_trace", []),
            "tool_calls": result.get("tool_calls", []),
            "waiting_for_user": result.get("waiting_for_user", False),
            "user_input_required": result.get("user_input_required"),
            "context": context_manager.get_context_summary(session_id),
            "execution_time_ms": execution_time,
            "session_id": session_id
        }
        
        return response
        
    except Exception as e:
        print(f"Enhanced chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enhanced chat failed: {str(e)}")

@router.post("/api/v1/react/continue-execution")
async def continue_execution(
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Continue execution after user provides required input
    """
    try:
        start_time = datetime.now()
        
        user_response = request_data.get("user_response", "")
        context = request_data.get("context", {})
        waiting_message_id = request_data.get("waiting_message_id")
        
        session_id = context.get("id") if context else None
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required for continuation")
        
        # Get conversation context
        conversation_context = context_manager.get_context(session_id)
        if not conversation_context:
            raise HTTPException(status_code=404, detail="Conversation context not found")
        
        # Resume execution with user input
        result = await event_executor.resume_execution(
            session_id=session_id,
            user_input=user_response,
            context=conversation_context
        )
        
        # Update context
        context_manager.update_context(
            session_id=session_id,
            new_data={
                "user_response": user_response,
                "continued_response": result.get("response", ""),
                "reasoning_trace": result.get("reasoning_trace", []),
                "tool_calls": result.get("tool_calls", []),
                "paused_execution": result.get("waiting_for_user", False),
                "pause_reason": result.get("user_input_required"),
                "updated_at": datetime.now().isoformat()
            }
        )
        
        # Save continuation to database
        conversation = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if conversation:
            # Save user response
            user_message = Message(
                conversation_id=conversation.id,
                content=user_response,
                role="user",
                metadata={"continuation": True, "waiting_message_id": waiting_message_id}
            )
            db.add(user_message)
            
            # Save continued assistant response
            assistant_message = Message(
                conversation_id=conversation.id,
                content=result.get("response", ""),
                role="assistant",
                metadata={
                    "reasoning_trace": result.get("reasoning_trace", []),
                    "tool_calls": result.get("tool_calls", []),
                    "waiting_for_user": result.get("waiting_for_user", False),
                    "user_input_required": result.get("user_input_required"),
                    "continuation": True,
                    "execution_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
                }
            )
            db.add(assistant_message)
            db.commit()
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        response = {
            "response": result.get("response", ""),
            "reasoning_trace": result.get("reasoning_trace", []),
            "tool_calls": result.get("tool_calls", []),
            "waiting_for_user": result.get("waiting_for_user", False),
            "user_input_required": result.get("user_input_required"),
            "context": context_manager.get_context_summary(session_id),
            "execution_time_ms": execution_time
        }
        
        return response
        
    except Exception as e:
        print(f"Continue execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Continue execution failed: {str(e)}")

@router.get("/api/v1/react/context/{session_id}")
async def get_conversation_context(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get conversation context for a session
    """
    try:
        context = context_manager.get_context(session_id)
        if not context:
            raise HTTPException(status_code=404, detail="Context not found")
        
        # Verify user has access to this context
        if context.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {"context": context}
        
    except Exception as e:
        print(f"Get context error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")

@router.delete("/api/v1/react/context/{session_id}")
async def clear_conversation_context(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Clear conversation context for a session
    """
    try:
        context = context_manager.get_context(session_id)
        if context and context.get("user_id") == current_user.id:
            context_manager.clear_context(session_id)
            return {"message": "Context cleared successfully"}
        else:
            raise HTTPException(status_code=404, detail="Context not found or access denied")
        
    except Exception as e:
        print(f"Clear context error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear context: {str(e)}")

@router.post("/api/v1/agent/enhanced-chat")
async def enhanced_conversational_chat(
    request_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enhanced conversational chat with reasoning and context preservation
    """
    try:
        start_time = datetime.now()
        
        # Parse request
        message = request_data.get("message", "")
        context = request_data.get("context")
        preserve_context = request_data.get("preserve_context", True)
        enable_reasoning = request_data.get("enable_reasoning", True)
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Get or create conversation context
        session_id = None
        if context and context.get("id"):
            session_id = context["id"]
        else:
            session_id = str(uuid.uuid4())
        
        # Initialize or retrieve context
        conversation_context = context_manager.get_or_create_context(
            session_id=session_id,
            user_id=current_user.id,
            preserve_context=preserve_context
        )
        
        # For conversational mode, we use a simpler approach but still with reasoning
        from ..services.conversational_agent import EnhancedConversationalAgent
        
        agent = EnhancedConversationalAgent(
            user_id=current_user.id,
            session_id=session_id,
            enable_reasoning=enable_reasoning,
            context_manager=context_manager
        )
        
        result = await agent.process_message(
            message=message,
            context=conversation_context
        )
        
        # Update context
        if preserve_context:
            context_manager.update_context(
                session_id=session_id,
                new_data={
                    "last_message": message,
                    "last_response": result.get("response", ""),
                    "reasoning_trace": result.get("reasoning_trace", []),
                    "updated_at": datetime.now().isoformat()
                }
            )
        
        # Save to database
        conversation = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            conversation = Conversation(
                session_id=session_id,
                user_id=current_user.id,
                title=message[:50] + "..." if len(message) > 50 else message,
                mode="conversational"
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        # Save messages
        user_message = Message(
            conversation_id=conversation.id,
            content=message,
            role="user",
            metadata={}
        )
        db.add(user_message)
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        assistant_message = Message(
            conversation_id=conversation.id,
            content=result.get("response", ""),
            role="assistant",
            metadata={
                "reasoning_trace": result.get("reasoning_trace", []),
                "execution_time_ms": execution_time
            }
        )
        db.add(assistant_message)
        db.commit()
        
        response = {
            "response": result.get("response", ""),
            "reasoning_trace": result.get("reasoning_trace", []),
            "tool_calls": [],
            "waiting_for_user": False,
            "user_input_required": None,
            "context": context_manager.get_context_summary(session_id),
            "execution_time_ms": execution_time,
            "session_id": session_id
        }
        
        return response
        
    except Exception as e:
        print(f"Enhanced conversational chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enhanced conversational chat failed: {str(e)}")