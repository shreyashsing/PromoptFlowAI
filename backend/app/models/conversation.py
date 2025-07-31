"""
Conversation and chat-related data models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import ConversationState, WorkflowPlan


class ChatMessage(BaseModel):
    """Individual chat message in a conversation."""
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    """Context for managing conversational workflow planning."""
    id: Optional[str] = None  # Database conversation ID
    session_id: str
    user_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    current_plan: Optional[WorkflowPlan] = None
    state: ConversationState = ConversationState.INITIAL
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlanModificationRequest(BaseModel):
    """Request to modify an existing workflow plan."""
    session_id: str
    modification: str
    current_plan: WorkflowPlan


class PlanConfirmationRequest(BaseModel):
    """Request to confirm a workflow plan."""
    session_id: str
    plan: WorkflowPlan
    approved: bool