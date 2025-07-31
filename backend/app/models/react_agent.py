"""
Data models for ReAct agent operations.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

from .base import ConversationState


class ReactRequestType(str, Enum):
    """Types of ReAct agent requests."""
    CHAT = "chat"
    TASK = "task"
    WORKFLOW = "workflow"


class ReactStatus(str, Enum):
    """Status of ReAct agent processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ToolCallStatus(str, Enum):
    """Status of individual tool calls."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReasoningStepType(str, Enum):
    """Types of reasoning steps."""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL_ANSWER = "final_answer"


class ReactRequest(BaseModel):
    """Request model for ReAct agent interactions."""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=5000, 
        description="User's natural language query",
        example="Help me analyze the sales data in my Google Sheets and send a summary via email"
    )
    session_id: Optional[str] = Field(
        None, 
        description="Conversation session ID",
        pattern=r'^[a-fA-F0-9-]{36}$',
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    user_id: str = Field(
        ..., 
        description="User identifier",
        example="user_123"
    )
    request_type: ReactRequestType = Field(
        ReactRequestType.CHAT, 
        description="Type of request"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional context for the request",
        example={"include_tool_context": True, "priority": "high"}
    )
    max_iterations: int = Field(
        10, 
        ge=1, 
        le=20, 
        description="Maximum reasoning iterations",
        example=10
    )
    tools: Optional[List[str]] = Field(
        None, 
        description="Restrict to specific tools",
        example=["gmail_connector", "google_sheets_connector"]
    )
    timeout: int = Field(
        300, 
        ge=30, 
        le=600, 
        description="Request timeout in seconds",
        example=300
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "query": "Read the latest sales data from my Google Sheets, analyze trends, and email a summary to my team",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user_123",
                "request_type": "chat",
                "context": {"include_tool_context": True},
                "max_iterations": 10,
                "tools": ["google_sheets_connector", "gmail_connector"],
                "timeout": 300
            }
        }


class ToolCall(BaseModel):
    """Model for individual tool calls within ReAct agent execution."""
    id: str = Field(
        ..., 
        description="Unique tool call identifier",
        example="call_123e4567-e89b-12d3-a456-426614174000"
    )
    tool_name: str = Field(
        ..., 
        min_length=1,
        max_length=100,
        description="Name of the tool being called",
        example="google_sheets_connector"
    )
    parameters: Dict[str, Any] = Field(
        ..., 
        description="Parameters passed to the tool",
        example={"spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "range": "A1:E10"}
    )
    result: Optional[Dict[str, Any]] = Field(
        None, 
        description="Tool execution result",
        example={"data": [["Name", "Sales"], ["John", "1000"], ["Jane", "1500"]], "rows": 3}
    )
    error: Optional[str] = Field(
        None, 
        max_length=1000,
        description="Error message if tool failed",
        example="Authentication failed: Invalid credentials"
    )
    status: ToolCallStatus = Field(
        ToolCallStatus.PENDING, 
        description="Tool call status"
    )
    execution_time_ms: Optional[int] = Field(
        None, 
        ge=0,
        description="Execution time in milliseconds",
        example=1500
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, 
        description="Completion timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata",
        example={"retry_count": 0, "auth_method": "oauth2"}
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "call_123e4567-e89b-12d3-a456-426614174000",
                "tool_name": "google_sheets_connector",
                "parameters": {
                    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    "range": "A1:E10"
                },
                "result": {
                    "data": [["Name", "Sales"], ["John", "1000"], ["Jane", "1500"]],
                    "rows": 3
                },
                "error": None,
                "status": "completed",
                "execution_time_ms": 1500,
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:01.5Z",
                "metadata": {"retry_count": 0}
            }
        }


class ReasoningStep(BaseModel):
    """Model for individual reasoning steps in ReAct agent processing."""
    step_number: int = Field(
        ..., 
        ge=1,
        description="Sequential step number",
        example=1
    )
    step_type: ReasoningStepType = Field(
        ..., 
        description="Type of reasoning step"
    )
    thought: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Agent's reasoning thought",
        example="I need to access the Google Sheets data to analyze the sales trends"
    )
    action: Optional[str] = Field(
        None, 
        max_length=500,
        description="Action to be taken",
        example="google_sheets_connector"
    )
    action_input: Optional[Dict[str, Any]] = Field(
        None, 
        description="Input parameters for action",
        example={"spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "range": "A1:E10"}
    )
    observation: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Observation from action result",
        example="Successfully retrieved 10 rows of sales data from the spreadsheet"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Step timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional step metadata",
        example={"confidence": 0.95, "processing_time_ms": 250}
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "step_number": 1,
                "step_type": "thought",
                "thought": "I need to access the Google Sheets data to analyze the sales trends",
                "action": None,
                "action_input": None,
                "observation": None,
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {"confidence": 0.95}
            }
        }


class ReactResponse(BaseModel):
    """Response model for ReAct agent interactions."""
    response: str = Field(
        ..., 
        description="Final response to user",
        example="I've analyzed your sales data from Google Sheets and found a 15% increase in Q4. I've sent a detailed summary to your team via email."
    )
    session_id: str = Field(
        ..., 
        description="Conversation session ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    request_id: str = Field(
        ..., 
        description="Unique request identifier",
        example="req_456e7890-e89b-12d3-a456-426614174001"
    )
    status: ReactStatus = Field(
        ..., 
        description="Processing status"
    )
    reasoning_trace: List[ReasoningStep] = Field(
        default_factory=list, 
        description="Reasoning steps taken by the agent",
        example=[
            {
                "step_number": 1,
                "step_type": "thought",
                "thought": "I need to read the sales data from Google Sheets first",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ]
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list, 
        description="Tool calls made during processing",
        example=[
            {
                "id": "call_1",
                "tool_name": "google_sheets_connector",
                "parameters": {"spreadsheet_id": "abc123", "range": "A1:Z100"},
                "status": "completed",
                "execution_time_ms": 1500
            }
        ]
    )
    processing_time_ms: Optional[int] = Field(
        None, 
        ge=0,
        description="Total processing time in milliseconds",
        example=3500
    )
    iterations_used: int = Field(
        0, 
        ge=0,
        description="Number of reasoning iterations used",
        example=3
    )
    tokens_used: Optional[int] = Field(
        None, 
        ge=0,
        description="Tokens consumed (if available)",
        example=1250
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional response metadata",
        example={"user_id": "user_123", "agent_version": "1.0.0"}
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Response timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "response": "I've successfully analyzed your sales data and sent the summary to your team.",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "request_id": "req_456e7890-e89b-12d3-a456-426614174001",
                "status": "completed",
                "reasoning_trace": [
                    {
                        "step_number": 1,
                        "step_type": "thought",
                        "thought": "I need to access the Google Sheets data first",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                ],
                "tool_calls": [
                    {
                        "id": "call_1",
                        "tool_name": "google_sheets_connector",
                        "parameters": {"spreadsheet_id": "abc123"},
                        "status": "completed",
                        "execution_time_ms": 1500
                    }
                ],
                "processing_time_ms": 3500,
                "iterations_used": 3,
                "tokens_used": 1250,
                "metadata": {"user_id": "user_123"},
                "created_at": "2024-01-15T10:30:05Z"
            }
        }


class ReactError(BaseModel):
    """Comprehensive error model for ReAct agent failures with detailed information."""
    error_type: str = Field(
        ..., 
        description="Type of error",
        example="tool_execution_error"
    )
    error_code: Optional[str] = Field(
        None,
        description="Unique error code for tracking",
        example="REACT_TOOL_EXEC_001"
    )
    message: str = Field(
        ..., 
        description="Technical error message",
        example="Tool execution failed due to authentication error"
    )
    user_message: str = Field(
        ...,
        description="User-friendly error message",
        example="There was an issue with your Google Sheets connection. Please check your authentication."
    )
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Detailed error information",
        example={
            "tool_name": "google_sheets_connector",
            "error_category": "authentication",
            "retry_count": 2
        }
    )
    reasoning_trace: List[ReasoningStep] = Field(
        default_factory=list, 
        description="Reasoning steps before error occurred"
    )
    failed_tool_calls: List[ToolCall] = Field(
        default_factory=list, 
        description="Tool calls that failed"
    )
    suggestions: List[str] = Field(
        default_factory=list, 
        description="Suggested actions for user",
        example=[
            "Check your Google Sheets authentication",
            "Try reconnecting your account",
            "Contact support if the issue persists"
        ]
    )
    recovery_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Specific recovery actions with instructions",
        example=[
            {
                "action": "reauth",
                "title": "Re-authenticate",
                "description": "Reconnect your Google Sheets account",
                "url": "/auth/google-sheets"
            }
        ]
    )
    session_id: Optional[str] = Field(
        None, 
        description="Session ID where error occurred",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracking",
        example="req_456e7890-e89b-12d3-a456-426614174001"
    )
    retryable: bool = Field(
        False,
        description="Whether the operation can be retried",
        example=True
    )
    retry_after: Optional[int] = Field(
        None,
        description="Seconds to wait before retrying",
        example=60
    )
    severity: str = Field(
        "medium",
        description="Error severity level",
        example="high"
    )
    category: str = Field(
        "system",
        description="Error category for classification",
        example="authentication"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context about the error",
        example={
            "user_id": "user_123",
            "operation": "process_request",
            "iteration_count": 3
        }
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Error timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "error_type": "tool_execution_error",
                "error_code": "REACT_TOOL_EXEC_001",
                "message": "Google Sheets connector authentication failed",
                "user_message": "There was an issue with your Google Sheets connection. Please check your authentication.",
                "details": {
                    "tool_name": "google_sheets_connector",
                    "error_category": "authentication",
                    "retry_count": 2
                },
                "reasoning_trace": [],
                "failed_tool_calls": [],
                "suggestions": [
                    "Check your Google Sheets authentication",
                    "Try reconnecting your account",
                    "Contact support if the issue persists"
                ],
                "recovery_actions": [
                    {
                        "action": "reauth",
                        "title": "Re-authenticate",
                        "description": "Reconnect your Google Sheets account",
                        "url": "/auth/google-sheets"
                    }
                ],
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "request_id": "req_456e7890-e89b-12d3-a456-426614174001",
                "retryable": True,
                "retry_after": 60,
                "severity": "high",
                "category": "authentication",
                "context": {
                    "user_id": "user_123",
                    "operation": "process_request"
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ReactConversation(BaseModel):
    """Model for ReAct agent conversation sessions."""
    id: str = Field(..., description="Unique conversation identifier")
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    state: ConversationState = Field(ConversationState.INITIAL, description="Conversation state")
    messages: List['ReactMessage'] = Field(default_factory=list, description="Conversation messages")
    tool_executions: List[ToolCall] = Field(default_factory=list, description="All tool executions")
    reasoning_traces: List[ReasoningStep] = Field(default_factory=list, description="All reasoning steps")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Conversation metadata")


class ReactMessage(BaseModel):
    """Model for messages within ReAct agent conversations."""
    id: str = Field(..., description="Unique message identifier")
    conversation_id: str = Field(..., description="Parent conversation ID")
    role: str = Field(..., description="Message role: user, assistant, or tool")
    content: str = Field(..., description="Message content")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls in this message")
    reasoning_step: Optional[ReasoningStep] = Field(None, description="Associated reasoning step")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")


class ReactSessionInfo(BaseModel):
    """Information about a ReAct agent session."""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    state: ConversationState = Field(..., description="Current session state")
    message_count: int = Field(0, description="Number of messages in session")
    tool_calls_count: int = Field(0, description="Number of tool calls made")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    created_at: datetime = Field(..., description="Session creation timestamp")
    is_active: bool = Field(True, description="Whether session is active")


class ReactToolMetadata(BaseModel):
    """Metadata about available tools for ReAct agent."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(..., description="Tool parameter schema")
    auth_required: bool = Field(False, description="Whether tool requires authentication")
    category: Optional[str] = Field(None, description="Tool category")
    usage_count: int = Field(0, description="Number of times tool has been used")
    success_rate: float = Field(0.0, description="Tool success rate (0.0 to 1.0)")
    avg_execution_time_ms: Optional[int] = Field(None, description="Average execution time")


class ReactAgentStatus(BaseModel):
    """Status information about the ReAct agent service."""
    status: str = Field(..., description="Service status")
    initialized: bool = Field(False, description="Whether service is initialized")
    tools_available: int = Field(0, description="Number of available tools")
    active_sessions: int = Field(0, description="Number of active sessions")
    total_requests: int = Field(0, description="Total requests processed")
    success_rate: float = Field(0.0, description="Overall success rate")
    avg_response_time_ms: Optional[int] = Field(None, description="Average response time")
    last_health_check: datetime = Field(default_factory=datetime.utcnow, description="Last health check")
    version: str = Field("1.0.0", description="Agent service version")


# Update forward references
ReactConversation.model_rebuild()
ReactMessage.model_rebuild()


# API-specific request/response models with enhanced validation

class ChatRequestAPI(BaseModel):
    """API request model for ReAct agent chat interactions with validation."""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=5000, 
        description="User's natural language query",
        example="Help me analyze the sales data in my Google Sheets and send a summary via email"
    )
    session_id: Optional[str] = Field(
        None, 
        description="Optional conversation session ID",
        pattern=r'^[a-fA-F0-9-]{36}$',
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    max_iterations: int = Field(
        10, 
        ge=1, 
        le=20, 
        description="Maximum reasoning iterations",
        example=10
    )
    context: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional context for the request",
        example={"include_tool_context": True, "priority": "high"}
    )
    tools: Optional[List[str]] = Field(
        None, 
        description="Restrict to specific tools",
        example=["gmail_connector", "google_sheets_connector"]
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Validate and sanitize query input."""
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        
        # Remove excessive whitespace
        v = ' '.join(v.split())
        
        # Check for potentially malicious content
        dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError(f'Query contains potentially dangerous content: {pattern}')
        
        return v
    
    @validator('tools')
    def validate_tools(cls, v):
        """Validate tool names."""
        if v is not None:
            # Check for valid tool name format
            valid_tool_pattern = r'^[a-zA-Z0-9_-]+$'
            import re
            for tool in v:
                if not re.match(valid_tool_pattern, tool):
                    raise ValueError(f'Invalid tool name format: {tool}')
                if len(tool) > 50:
                    raise ValueError(f'Tool name too long: {tool}')
        return v
    
    @validator('context')
    def validate_context(cls, v):
        """Validate context dictionary."""
        if v is not None:
            # Limit context size
            import json
            context_str = json.dumps(v)
            if len(context_str) > 10000:  # 10KB limit
                raise ValueError('Context data too large (max 10KB)')
            
            # Check for dangerous keys
            dangerous_keys = ['__proto__', 'constructor', 'prototype']
            for key in v.keys():
                if key in dangerous_keys:
                    raise ValueError(f'Context contains dangerous key: {key}')
        return v
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "query": "Read the latest sales data from my Google Sheets, analyze trends, and email a summary to my team",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "max_iterations": 10,
                "context": {"include_tool_context": True},
                "tools": ["google_sheets_connector", "gmail_connector"]
            }
        }


class ChatResponseAPI(BaseModel):
    """API response model for ReAct agent chat interactions."""
    response: str = Field(
        ..., 
        description="Agent's response to the user",
        example="I've analyzed your sales data from Google Sheets and found a 15% increase in Q4. I've sent a detailed summary to your team via email."
    )
    session_id: str = Field(
        ..., 
        description="Conversation session ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    reasoning_trace: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Reasoning steps taken by the agent"
    )
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Tools called during processing"
    )
    status: str = Field(
        ..., 
        description="Processing status",
        example="completed"
    )
    processing_time_ms: Optional[int] = Field(
        None, 
        ge=0,
        description="Processing time in milliseconds",
        example=3500
    )
    iterations_used: int = Field(
        0, 
        ge=0,
        description="Number of reasoning iterations used",
        example=3
    )
    tools_used: int = Field(
        0, 
        ge=0,
        description="Number of tools used",
        example=2
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "response": "I've successfully analyzed your sales data and sent the summary to your team.",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "reasoning_trace": [
                    {
                        "step_number": 1,
                        "step_type": "thought",
                        "content": "I need to access the Google Sheets data first",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                ],
                "tool_calls": [
                    {
                        "id": "call_1",
                        "tool_name": "google_sheets_connector",
                        "parameters": {"spreadsheet_id": "abc123"},
                        "status": "completed",
                        "execution_time_ms": 1500
                    }
                ],
                "status": "completed",
                "processing_time_ms": 3500,
                "iterations_used": 3,
                "tools_used": 2,
                "metadata": {"user_id": "user_123"}
            }
        }


class ConversationHistoryResponseAPI(BaseModel):
    """API response model for conversation history retrieval."""
    session_id: str = Field(
        ..., 
        description="Session identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Conversation messages"
    )
    status: str = Field(
        ..., 
        description="Conversation status",
        example="active"
    )
    created_at: Optional[str] = Field(
        None, 
        description="Creation timestamp",
        example="2024-01-15T10:00:00Z"
    )
    updated_at: Optional[str] = Field(
        None, 
        description="Last update timestamp",
        example="2024-01-15T10:30:00Z"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Conversation summary statistics"
    )
    context_summary: Optional[str] = Field(
        None, 
        description="Context summary",
        example="User requested sales data analysis and email summary"
    )
    tool_usage_history: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Tool usage history"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "messages": [
                    {
                        "id": "msg_1",
                        "role": "user",
                        "content": "Analyze my sales data",
                        "timestamp": "2024-01-15T10:00:00Z"
                    },
                    {
                        "id": "msg_2",
                        "role": "assistant",
                        "content": "I'll analyze your sales data from Google Sheets",
                        "timestamp": "2024-01-15T10:00:05Z"
                    }
                ],
                "status": "active",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "summary": {
                    "message_count": 6,
                    "tool_calls_count": 2,
                    "duration_minutes": 30
                },
                "context_summary": "User requested sales data analysis and email summary",
                "tool_usage_history": [
                    {
                        "tool_name": "google_sheets_connector",
                        "usage_count": 1,
                        "last_used": "2024-01-15T10:15:00Z"
                    }
                ]
            }
        }


class ReactErrorAPI(BaseModel):
    """API error response model for ReAct agent failures."""
    error_type: str = Field(
        ..., 
        description="Type of error",
        example="validation_error"
    )
    message: str = Field(
        ..., 
        description="Human-readable error message",
        example="The query contains invalid characters"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Detailed error information"
    )
    session_id: Optional[str] = Field(
        None, 
        description="Session ID where error occurred",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    suggestions: List[str] = Field(
        default_factory=list, 
        description="Suggested actions for user",
        example=["Please check your query for special characters", "Try rephrasing your request"]
    )
    timestamp: str = Field(
        ..., 
        description="Error timestamp",
        example="2024-01-15T10:30:00Z"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "error_type": "validation_error",
                "message": "The query contains invalid characters",
                "details": {"field": "query", "invalid_chars": ["<", ">"]},
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "suggestions": [
                    "Please check your query for special characters",
                    "Try rephrasing your request"
                ],
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


# Validation utility functions

def sanitize_string_input(value: str, max_length: int = 1000) -> str:
    """Sanitize string input by removing dangerous content and limiting length."""
    if not value:
        return ""
    
    # Remove excessive whitespace
    value = ' '.join(value.split())
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Remove potentially dangerous HTML/script content
    import re
    # Remove HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    
    # Remove script-like content
    dangerous_patterns = [
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'on\w+\s*=',  # event handlers like onclick=
    ]
    
    for pattern in dangerous_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    return value


def validate_session_id(session_id: Optional[str]) -> Optional[str]:
    """Validate session ID format."""
    if session_id is None:
        return None
    
    import re
    # UUID v4 format
    uuid_pattern = r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[89abAB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$'
    
    if not re.match(uuid_pattern, session_id):
        raise ValueError(f"Invalid session ID format: {session_id}")
    
    return session_id


def validate_tool_names(tools: Optional[List[str]]) -> Optional[List[str]]:
    """Validate tool names list."""
    if tools is None:
        return None
    
    if len(tools) > 10:  # Reasonable limit
        raise ValueError("Too many tools specified (max 10)")
    
    import re
    valid_tool_pattern = r'^[a-zA-Z0-9_-]+$'
    
    validated_tools = []
    for tool in tools:
        if not isinstance(tool, str):
            raise ValueError(f"Tool name must be string: {tool}")
        
        if len(tool) > 50:
            raise ValueError(f"Tool name too long: {tool}")
        
        if not re.match(valid_tool_pattern, tool):
            raise ValueError(f"Invalid tool name format: {tool}")
        
        validated_tools.append(tool)
    
    return validated_tools


def format_reasoning_trace_for_api(reasoning_trace: List[ReasoningStep]) -> List[Dict[str, Any]]:
    """Format reasoning trace for API response."""
    formatted_trace = []
    
    for step in reasoning_trace:
        formatted_step = {
            "step_number": step.step_number,
            "step_type": step.step_type.value if hasattr(step.step_type, 'value') else str(step.step_type),
            "timestamp": step.timestamp.isoformat() if hasattr(step.timestamp, 'isoformat') else str(step.timestamp)
        }
        
        # Add optional fields if present
        if step.thought:
            formatted_step["thought"] = step.thought
        if step.action:
            formatted_step["action"] = step.action
        if step.action_input:
            formatted_step["action_input"] = step.action_input
        if step.observation:
            formatted_step["observation"] = step.observation
        if step.metadata:
            formatted_step["metadata"] = step.metadata
        
        formatted_trace.append(formatted_step)
    
    return formatted_trace


def format_tool_calls_for_api(tool_calls: List[ToolCall]) -> List[Dict[str, Any]]:
    """Format tool calls for API response."""
    formatted_calls = []
    
    for call in tool_calls:
        formatted_call = {
            "id": call.id,
            "tool_name": call.tool_name,
            "parameters": call.parameters,
            "status": call.status.value if hasattr(call.status, 'value') else str(call.status),
            "started_at": call.started_at.isoformat() if hasattr(call.started_at, 'isoformat') else str(call.started_at)
        }
        
        # Add optional fields if present
        if call.result:
            formatted_call["result"] = call.result
        if call.error:
            formatted_call["error"] = call.error
        if call.execution_time_ms:
            formatted_call["execution_time_ms"] = call.execution_time_ms
        if call.completed_at:
            formatted_call["completed_at"] = call.completed_at.isoformat() if hasattr(call.completed_at, 'isoformat') else str(call.completed_at)
        if call.metadata:
            formatted_call["metadata"] = call.metadata
        
        formatted_calls.append(formatted_call)
    
    return formatted_calls


class ConversationListResponseAPI(BaseModel):
    """Response model for listing conversations."""
    conversations: List['UserConversationResponseAPI'] = Field(
        default_factory=list,
        description="List of user conversations"
    )
    total_count: int = Field(default=0, description="Total number of conversations")
    has_more: bool = Field(default=False, description="Whether there are more conversations")


class UserConversationResponseAPI(BaseModel):
    """Response model for user conversation summary."""
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    updated_at: str = Field(..., description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages in conversation")
    created_at: str = Field(..., description="Creation timestamp")
    status: str = Field(default="active", description="Conversation status")


class ConversationResponseAPI(BaseModel):
    """Response model for individual conversation details."""
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation messages"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Conversation metadata")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


# Helper functions for formatting API responses
def format_reasoning_trace_for_api(reasoning_trace: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format reasoning trace for API response.
    Handles both standardized ReasoningStep objects and legacy dictionary format.
    """
    if not reasoning_trace:
        return []
    
    formatted = []
    for i, step in enumerate(reasoning_trace):
        # Handle standardized ReasoningStep objects
        if isinstance(step, dict):
            # Ensure step_number is always present to fix attribute errors
            step_number = step.get("step_number", i + 1)
            
            formatted_step = {
                "step_number": step_number,
                "step_type": step.get("step_type", "unknown"),
                "content": step.get("content", ""),
                "timestamp": step.get("timestamp", ""),
                "tool_name": step.get("tool_name"),
                "action_input": step.get("action_input", {}),
                # Legacy fields for backward compatibility
                "thought": step.get("thought", step.get("content", "")),
                "action": step.get("action", step.get("tool_name", "")),
                "observation": step.get("observation", step.get("content", "")),
                "success": step.get("success", True)
            }
            formatted.append(formatted_step)
        else:
            # Handle unexpected format - create minimal valid step
            formatted.append({
                "step_number": i + 1,
                "step_type": "unknown",
                "content": str(step),
                "timestamp": "",
                "tool_name": None,
                "action_input": {},
                "thought": str(step),
                "action": "",
                "observation": "",
                "success": True
            })
    
    return formatted


def format_tool_calls_for_api(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format tool calls for API response.
    Handles both standardized ToolCall objects and legacy dictionary format.
    """
    if not tool_calls:
        return []
    
    formatted = []
    for call in tool_calls:
        if isinstance(call, dict):
            formatted_call = {
                "id": call.get("id", ""),
                "tool_name": call.get("tool_name", ""),
                "parameters": call.get("parameters", {}),
                "result": call.get("result"),
                "error": call.get("error"),
                "status": call.get("status", "completed"),
                "execution_time": call.get("execution_time", call.get("execution_time_ms", 0)),
                "timestamp": call.get("timestamp", ""),
                # Legacy fields for backward compatibility
                "input": call.get("parameters", {}),
                "output": call.get("result", "")
            }
            formatted.append(formatted_call)
        else:
            # Handle unexpected format - create minimal valid call
            formatted.append({
                "id": "",
                "tool_name": "unknown_tool",
                "parameters": {},
                "result": None,
                "error": f"Invalid tool call format: {call}",
                "status": "failed",
                "execution_time": 0,
                "timestamp": "",
                "input": {},
                "output": ""
            })
    
    return formatted