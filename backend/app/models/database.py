"""
Database models for PromptFlow AI platform.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from app.models.base import WorkflowStatus, ConversationState, AuthType


class UserProfile(BaseModel):
    """User profile model."""
    id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkflowDB(BaseModel):
    """Database model for workflows."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    triggers: List[Dict[str, Any]] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ConnectorDB(BaseModel):
    """Database model for connector metadata."""
    id: UUID
    name: str
    display_name: str
    description: str
    category: str
    schema: Dict[str, Any]
    auth_type: AuthType = AuthType.NONE
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    usage_count: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class AuthTokenDB(BaseModel):
    """Database model for encrypted authentication tokens."""
    id: UUID
    user_id: UUID
    connector_name: str
    token_type: AuthType
    encrypted_token: str
    token_metadata: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class WorkflowExecutionDB(BaseModel):
    """Database model for workflow executions."""
    id: UUID
    workflow_id: UUID
    user_id: UUID
    status: str = "pending"  # pending, running, completed, failed, cancelled
    trigger_type: Optional[str] = None  # manual, schedule, webhook
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    execution_log: List[Dict[str, Any]] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class ConversationDB(BaseModel):
    """Database model for conversation history."""
    id: UUID
    user_id: UUID
    session_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    current_plan: Optional[Dict[str, Any]] = None
    state: ConversationState = ConversationState.INITIAL
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# Request/Response models for API
class CreateWorkflowRequest(BaseModel):
    """Request model for creating a workflow."""
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    triggers: List[Dict[str, Any]] = Field(default_factory=list)
    status: Optional[WorkflowStatus] = WorkflowStatus.ACTIVE


class UpdateWorkflowRequest(BaseModel):
    """Request model for updating a workflow."""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    triggers: Optional[List[Dict[str, Any]]] = None
    status: Optional[WorkflowStatus] = None


class CreateAuthTokenRequest(BaseModel):
    """Request model for storing authentication tokens."""
    connector_name: str
    token_type: AuthType
    token_data: Dict[str, Any]  # Will be encrypted before storage
    expires_at: Optional[datetime] = None


class UpdateUserProfileRequest(BaseModel):
    """Request model for updating user profile."""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None