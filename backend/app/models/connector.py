"""
Connector-related data models.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import AuthType


class AuthRequirements(BaseModel):
    """Authentication requirements for a connector."""
    type: AuthType
    fields: Dict[str, str] = Field(default_factory=dict)  # field_name -> description
    oauth_scopes: List[str] = Field(default_factory=list)
    instructions: Optional[str] = None


class ConnectorResult(BaseModel):
    """Result from connector execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectorMetadata(BaseModel):
    """Metadata for connector registration and retrieval."""
    name: str
    description: str
    category: str
    parameter_schema: Dict[str, Any]
    auth_type: AuthType
    embedding: Optional[List[float]] = None
    usage_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectorExecutionContext(BaseModel):
    """Context for connector execution."""
    user_id: str
    auth_tokens: Dict[str, str] = Field(default_factory=dict)
    request_id: Optional[str] = None
    workflow_id: Optional[str] = None
    node_id: Optional[str] = None
    previous_results: Dict[str, Any] = Field(default_factory=dict)