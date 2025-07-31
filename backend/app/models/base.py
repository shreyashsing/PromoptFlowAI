"""
Base models and common data structures.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class AuthType(str, Enum):
    """Authentication types for connectors."""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationState(str, Enum):
    """Conversation state for planning."""
    INITIAL = "initial"
    PLANNING = "planning"
    CONFIGURING = "configuring"  # Added for ReAct workflow building
    CONFIRMING = "confirming"
    APPROVED = "approved"
    EXECUTING = "executing"


class NodePosition(BaseModel):
    """Position coordinates for workflow visualization."""
    x: float
    y: float


class WorkflowNode(BaseModel):
    """Individual node in a workflow graph."""
    id: str
    connector_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    position: NodePosition
    dependencies: List[str] = Field(default_factory=list)


class WorkflowEdge(BaseModel):
    """Edge connecting workflow nodes."""
    id: str
    source: str
    target: str
    condition: Optional[str] = None


class Trigger(BaseModel):
    """Workflow trigger configuration."""
    id: str
    type: str  # "schedule" or "webhook"
    config: Dict[str, Any]
    enabled: bool = True


class WorkflowPlan(BaseModel):
    """Complete workflow definition."""
    id: str
    user_id: str
    name: str
    description: str
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    triggers: List[Trigger] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)