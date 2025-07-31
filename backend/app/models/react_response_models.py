"""
Standardized response models for ReAct agent to fix attribute errors and ensure consistent structure.
This addresses the "'dict' object has no attribute 'step_number'" error by providing proper data classes.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import json
import uuid


class ReactStatus(str, Enum):
    """Status of ReAct agent processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ReasoningStepType(str, Enum):
    """Types of reasoning steps."""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL_ANSWER = "final_answer"
    ERROR = "error"


class ToolCallStatus(str, Enum):
    """Status of individual tool calls."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReasoningStep:
    """
    Standardized reasoning step model with all required fields.
    Ensures step_number attribute is always present to fix frontend errors.
    """
    step_number: int
    step_type: str  # Using string to allow flexibility while maintaining structure
    content: str
    timestamp: float
    tool_name: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    
    # Additional fields for compatibility
    thought: Optional[str] = None
    action: Optional[str] = None
    observation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure content is populated from appropriate field."""
        if not self.content:
            if self.step_type.lower() == "thought" and self.thought:
                self.content = self.thought
            elif self.step_type.lower() == "action" and self.action:
                self.content = self.action
            elif self.step_type.lower() == "observation" and self.observation:
                self.content = self.observation
            else:
                self.content = self.content or ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReasoningStep':
        """Create ReasoningStep from dictionary data."""
        # Ensure step_number is present
        if 'step_number' not in data:
            data['step_number'] = data.get('step', 1)
        
        # Ensure timestamp is present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().timestamp()
        
        # Ensure content is present
        if 'content' not in data or not data['content']:
            content = (
                data.get('thought') or 
                data.get('action') or 
                data.get('observation') or 
                data.get('message') or 
                ""
            )
            data['content'] = content
        
        # Filter out None values and unknown fields
        valid_fields = {
            'step_number', 'step_type', 'content', 'timestamp', 
            'tool_name', 'action_input', 'thought', 'action', 
            'observation', 'metadata'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields and v is not None}
        
        return cls(**filtered_data)


@dataclass
class ToolCall:
    """
    Standardized tool call model with all required fields.
    Ensures consistent structure for frontend compatibility.
    """
    tool_name: str
    parameters: Dict[str, Any]
    execution_time: float  # in milliseconds
    timestamp: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status: str = ToolCallStatus.COMPLETED.value
    
    # Additional fields for compatibility
    id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure required fields are populated."""
        if not self.id:
            self.id = str(uuid.uuid4())
        
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        
        # Set status based on error
        if self.error:
            self.status = ToolCallStatus.FAILED.value
        elif self.result is not None:
            self.status = ToolCallStatus.COMPLETED.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to strings
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolCall':
        """Create ToolCall from dictionary data."""
        # Ensure required fields are present
        if 'tool_name' not in data:
            data['tool_name'] = data.get('name', 'unknown_tool')
        
        if 'parameters' not in data:
            data['parameters'] = data.get('args', {})
        
        if 'execution_time' not in data:
            data['execution_time'] = data.get('duration_ms', 0)
        
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()
        
        # Filter out None values and unknown fields
        valid_fields = {
            'tool_name', 'parameters', 'execution_time', 'timestamp',
            'result', 'error', 'status', 'id', 'started_at', 
            'completed_at', 'metadata'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields and v is not None}
        
        return cls(**filtered_data)


@dataclass
class ReactAgentResponse:
    """
    Standardized ReAct agent response model.
    Ensures consistent structure across all code paths and frontend compatibility.
    """
    response: str  # Final response message
    session_id: str
    status: str
    reasoning_trace: List[ReasoningStep] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    
    # Optional fields
    request_id: Optional[str] = None
    processing_time_ms: Optional[int] = None
    iterations_used: int = 0
    tokens_used: Optional[int] = None
    tools_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    # Error information
    error: Optional['ReactError'] = None
    
    def __post_init__(self):
        """Ensure required fields are populated."""
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
        
        if not self.created_at:
            self.created_at = datetime.utcnow()
        elif isinstance(self.created_at, str):
            # Convert string to datetime if needed
            try:
                if 'T' in self.created_at:
                    self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
                else:
                    self.created_at = datetime.utcnow()
            except ValueError:
                self.created_at = datetime.utcnow()
        
        # Calculate tools_used from tool_calls
        self.tools_used = len(self.tool_calls)
        
        # Ensure reasoning_trace has proper step numbers
        for i, step in enumerate(self.reasoning_trace):
            if not hasattr(step, 'step_number') or step.step_number <= 0:
                step.step_number = i + 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        
        # Convert datetime to string - handle both datetime objects and strings
        if self.created_at:
            if isinstance(self.created_at, datetime):
                data['created_at'] = self.created_at.isoformat()
            elif isinstance(self.created_at, str):
                data['created_at'] = self.created_at
            else:
                data['created_at'] = str(self.created_at)
        
        # Convert reasoning_trace to list of dicts
        data['reasoning_trace'] = [step.to_dict() for step in self.reasoning_trace]
        
        # Convert tool_calls to list of dicts
        data['tool_calls'] = [call.to_dict() for call in self.tool_calls]
        
        # Convert error to dict if present
        if self.error:
            data['error'] = self.error.to_dict()
        
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReactAgentResponse':
        """Create ReactAgentResponse from dictionary data."""
        # Ensure required fields are present
        if 'response' not in data:
            data['response'] = data.get('message', '')
        
        if 'session_id' not in data:
            data['session_id'] = str(uuid.uuid4())
        
        if 'status' not in data:
            data['status'] = ReactStatus.COMPLETED.value
        
        # Convert reasoning_trace from list of dicts
        if 'reasoning_trace' in data and isinstance(data['reasoning_trace'], list):
            reasoning_steps = []
            for i, step_data in enumerate(data['reasoning_trace']):
                if isinstance(step_data, dict):
                    # Ensure step_number is set
                    if 'step_number' not in step_data:
                        step_data['step_number'] = i + 1
                    reasoning_steps.append(ReasoningStep.from_dict(step_data))
                else:
                    # Handle case where step_data is not a dict
                    reasoning_steps.append(ReasoningStep(
                        step_number=i + 1,
                        step_type="unknown",
                        content=str(step_data),
                        timestamp=datetime.utcnow().timestamp()
                    ))
            data['reasoning_trace'] = reasoning_steps
        else:
            data['reasoning_trace'] = []
        
        # Convert tool_calls from list of dicts
        if 'tool_calls' in data and isinstance(data['tool_calls'], list):
            tool_calls = []
            for call_data in data['tool_calls']:
                if isinstance(call_data, dict):
                    tool_calls.append(ToolCall.from_dict(call_data))
                else:
                    # Handle case where call_data is not a dict
                    tool_calls.append(ToolCall(
                        tool_name="unknown_tool",
                        parameters={},
                        execution_time=0,
                        timestamp=datetime.utcnow().isoformat(),
                        error=f"Invalid tool call data: {call_data}"
                    ))
            data['tool_calls'] = tool_calls
        else:
            data['tool_calls'] = []
        
        # Handle error field
        if 'error' in data and isinstance(data['error'], dict):
            data['error'] = ReactError.from_dict(data['error'])
        
        # Handle created_at field - convert string to datetime if needed
        if 'created_at' in data:
            if isinstance(data['created_at'], str):
                try:
                    # Try to parse ISO format datetime string
                    if 'T' in data['created_at']:
                        # ISO format with T separator
                        data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                    else:
                        # Fallback to current datetime if format is unexpected
                        data['created_at'] = datetime.utcnow()
                except ValueError:
                    # Fallback to current datetime if parsing fails
                    data['created_at'] = datetime.utcnow()
            elif not isinstance(data['created_at'], datetime):
                # If it's neither string nor datetime, set to current time
                data['created_at'] = datetime.utcnow()
        
        # Filter out None values and unknown fields
        valid_fields = {
            'response', 'session_id', 'status', 'reasoning_trace', 'tool_calls',
            'request_id', 'processing_time_ms', 'iterations_used', 'tokens_used',
            'tools_used', 'metadata', 'created_at', 'error'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields and v is not None}
        
        return cls(**filtered_data)


@dataclass
class ReactError:
    """
    Standardized error model for ReAct agent failures.
    Maintains consistent structure even in error cases.
    """
    error_type: str
    message: str
    user_message: str
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Optional fields
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    reasoning_trace: List[ReasoningStep] = field(default_factory=list)
    failed_tool_calls: List[ToolCall] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    recovery_actions: List[Dict[str, Any]] = field(default_factory=list)
    retryable: bool = False
    retry_after: Optional[int] = None
    severity: str = "medium"
    category: str = "system"
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Ensure required fields are populated."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
        
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        
        # Convert datetime to string
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        
        # Convert reasoning_trace to list of dicts
        data['reasoning_trace'] = [step.to_dict() for step in self.reasoning_trace]
        
        # Convert failed_tool_calls to list of dicts
        data['failed_tool_calls'] = [call.to_dict() for call in self.failed_tool_calls]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReactError':
        """Create ReactError from dictionary data."""
        # Ensure required fields are present
        if 'error_type' not in data:
            data['error_type'] = 'unknown_error'
        
        if 'message' not in data:
            data['message'] = str(data.get('error', 'Unknown error occurred'))
        
        if 'user_message' not in data:
            data['user_message'] = data.get('message', 'An error occurred while processing your request')
        
        # Convert reasoning_trace from list of dicts
        if 'reasoning_trace' in data and isinstance(data['reasoning_trace'], list):
            reasoning_steps = []
            for i, step_data in enumerate(data['reasoning_trace']):
                if isinstance(step_data, dict):
                    if 'step_number' not in step_data:
                        step_data['step_number'] = i + 1
                    reasoning_steps.append(ReasoningStep.from_dict(step_data))
            data['reasoning_trace'] = reasoning_steps
        else:
            data['reasoning_trace'] = []
        
        # Convert failed_tool_calls from list of dicts
        if 'failed_tool_calls' in data and isinstance(data['failed_tool_calls'], list):
            tool_calls = []
            for call_data in data['failed_tool_calls']:
                if isinstance(call_data, dict):
                    tool_calls.append(ToolCall.from_dict(call_data))
            data['failed_tool_calls'] = tool_calls
        else:
            data['failed_tool_calls'] = []
        
        # Filter out None values and unknown fields
        valid_fields = {
            'error_type', 'message', 'user_message', 'session_id', 'request_id',
            'error_code', 'details', 'reasoning_trace', 'failed_tool_calls',
            'suggestions', 'recovery_actions', 'retryable', 'retry_after',
            'severity', 'category', 'context', 'timestamp'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields and v is not None}
        
        return cls(**filtered_data)


# Utility functions for response formatting

def create_reasoning_step(
    step_number: int,
    step_type: str,
    content: str,
    tool_name: Optional[str] = None,
    action_input: Optional[Dict[str, Any]] = None
) -> ReasoningStep:
    """Create a properly formatted reasoning step."""
    return ReasoningStep(
        step_number=step_number,
        step_type=step_type,
        content=content,
        timestamp=datetime.utcnow().timestamp(),
        tool_name=tool_name,
        action_input=action_input
    )


def create_tool_call(
    tool_name: str,
    parameters: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    execution_time: float = 0
) -> ToolCall:
    """Create a properly formatted tool call."""
    return ToolCall(
        tool_name=tool_name,
        parameters=parameters,
        result=result,
        error=error,
        execution_time=execution_time,
        timestamp=datetime.utcnow().isoformat()
    )


def create_success_response(
    response: str,
    session_id: str,
    reasoning_trace: List[ReasoningStep] = None,
    tool_calls: List[ToolCall] = None,
    processing_time_ms: Optional[int] = None,
    iterations_used: int = 0,
    metadata: Optional[Dict[str, Any]] = None
) -> ReactAgentResponse:
    """Create a standardized success response."""
    return ReactAgentResponse(
        response=response,
        session_id=session_id,
        status=ReactStatus.COMPLETED.value,
        reasoning_trace=reasoning_trace or [],
        tool_calls=tool_calls or [],
        processing_time_ms=processing_time_ms,
        iterations_used=iterations_used,
        metadata=metadata or {}
    )


def create_error_response(
    error_message: str,
    session_id: str,
    error_type: str = "processing_error",
    user_message: Optional[str] = None,
    reasoning_trace: List[ReasoningStep] = None,
    failed_tool_calls: List[ToolCall] = None,
    suggestions: List[str] = None,
    processing_time_ms: Optional[int] = None
) -> ReactAgentResponse:
    """Create a standardized error response."""
    error = ReactError(
        error_type=error_type,
        message=error_message,
        user_message=user_message or "An error occurred while processing your request",
        session_id=session_id,
        reasoning_trace=reasoning_trace or [],
        failed_tool_calls=failed_tool_calls or [],
        suggestions=suggestions or []
    )
    
    return ReactAgentResponse(
        response=f"❌ {error.user_message}",
        session_id=session_id,
        status=ReactStatus.FAILED.value,
        reasoning_trace=reasoning_trace or [],
        tool_calls=failed_tool_calls or [],
        processing_time_ms=processing_time_ms,
        error=error,
        metadata={"error": True}
    )


def format_langgraph_response(
    langgraph_output: Dict[str, Any],
    session_id: str,
    processing_time_ms: Optional[int] = None
) -> ReactAgentResponse:
    """
    Format LangGraph agent output to standardized response structure.
    This fixes the step_number attribute errors by ensuring proper structure.
    """
    try:
        # Extract basic response - handle different LangGraph response formats
        response_text = ""
        messages = []
        
        if "messages" in langgraph_output:
            # LangGraph response with messages array
            messages = langgraph_output["messages"]
            if messages:
                final_message = messages[-1]
                if hasattr(final_message, 'content'):
                    response_text = final_message.content
                elif isinstance(final_message, dict):
                    response_text = final_message.get('content', str(final_message))
                else:
                    response_text = str(final_message)
        else:
            # Fallback to other response formats
            response_text = langgraph_output.get('output', langgraph_output.get('response', str(langgraph_output)))
        
        # Extract and format reasoning trace with proper step numbering
        reasoning_trace = []
        step_counter = 1
        
        # Process messages to extract reasoning steps
        for message in messages:
            timestamp = datetime.utcnow().timestamp()
            
            # Handle different message types
            if hasattr(message, 'type'):
                message_type = message.type
                content = getattr(message, 'content', str(message))
                
                if message_type == "human":
                    # User input - create thought step
                    reasoning_step = ReasoningStep(
                        step_number=step_counter,
                        step_type="thought",
                        content=f"User query: {content}",
                        timestamp=timestamp
                    )
                    reasoning_trace.append(reasoning_step)
                    step_counter += 1
                    
                elif message_type == "ai":
                    # AI response - could be thought or final answer
                    if content and content.strip():
                        # Determine if this is a reasoning step or final answer
                        if any(keyword in content.lower() for keyword in ["i need to", "let me", "i should", "first", "next"]):
                            step_type = "thought"
                        else:
                            step_type = "final_answer"
                        
                        reasoning_step = ReasoningStep(
                            step_number=step_counter,
                            step_type=step_type,
                            content=content,
                            timestamp=timestamp
                        )
                        reasoning_trace.append(reasoning_step)
                        step_counter += 1
                
                elif message_type == "tool":
                    # Tool result - create observation step
                    reasoning_step = ReasoningStep(
                        step_number=step_counter,
                        step_type="observation",
                        content=f"Tool result: {content}",
                        timestamp=timestamp
                    )
                    reasoning_trace.append(reasoning_step)
                    step_counter += 1
            
            # Extract tool calls from message
            if hasattr(message, 'additional_kwargs') and message.additional_kwargs.get('tool_calls'):
                for tool_call_data in message.additional_kwargs['tool_calls']:
                    # Add action step for tool call
                    tool_name = tool_call_data.get('function', {}).get('name', 'unknown_tool')
                    reasoning_step = ReasoningStep(
                        step_number=step_counter,
                        step_type="action",
                        content=f"Using tool: {tool_name}",
                        timestamp=timestamp,
                        tool_name=tool_name,
                        action_input=tool_call_data.get('function', {}).get('arguments', {})
                    )
                    reasoning_trace.append(reasoning_step)
                    step_counter += 1
        
        # Handle legacy intermediate_steps format
        intermediate_steps = langgraph_output.get('intermediate_steps', [])
        for i, step in enumerate(intermediate_steps):
            if isinstance(step, dict):
                reasoning_step = ReasoningStep.from_dict({
                    'step_number': step_counter,
                    'step_type': step.get('type', 'thought'),
                    'content': step.get('content', step.get('thought', '')),
                    'timestamp': datetime.utcnow().timestamp(),
                    'tool_name': step.get('tool_name'),
                    'action_input': step.get('action_input')
                })
                reasoning_trace.append(reasoning_step)
                step_counter += 1
            elif isinstance(step, tuple) and len(step) >= 2:
                # Handle LangChain-style (action, observation) tuples
                action, observation = step[0], step[1]
                
                # Add action step
                reasoning_trace.append(ReasoningStep(
                    step_number=step_counter,
                    step_type="action",
                    content=str(action),
                    timestamp=datetime.utcnow().timestamp()
                ))
                step_counter += 1
                
                # Add observation step
                reasoning_trace.append(ReasoningStep(
                    step_number=step_counter,
                    step_type="observation",
                    content=str(observation),
                    timestamp=datetime.utcnow().timestamp()
                ))
                step_counter += 1
        
        # Extract and format tool calls with proper structure
        tool_calls = []
        
        # Extract tool calls from messages
        for message in messages:
            if hasattr(message, 'additional_kwargs') and message.additional_kwargs.get('tool_calls'):
                for tool_call_data in message.additional_kwargs['tool_calls']:
                    try:
                        tool_call = ToolCall(
                            tool_name=tool_call_data.get('function', {}).get('name', 'unknown_tool'),
                            parameters=tool_call_data.get('function', {}).get('arguments', {}),
                            execution_time=0,  # Will be updated if available
                            timestamp=datetime.utcnow().isoformat(),
                            result={"status": "completed"},  # Default result
                            status="completed"
                        )
                        tool_calls.append(tool_call)
                    except Exception as tool_error:
                        logger.warning(f"Failed to parse tool call: {tool_error}")
        
        # Extract tool calls from legacy format
        tool_executions = langgraph_output.get('tool_calls', [])
        for call_data in tool_executions:
            if isinstance(call_data, dict):
                try:
                    tool_call = ToolCall.from_dict(call_data)
                    tool_calls.append(tool_call)
                except Exception as tool_error:
                    logger.warning(f"Failed to parse legacy tool call: {tool_error}")
        
        # Ensure we have at least one reasoning step if none were extracted
        if not reasoning_trace and response_text:
            reasoning_trace.append(ReasoningStep(
                step_number=1,
                step_type="final_answer",
                content=response_text,
                timestamp=datetime.utcnow().timestamp()
            ))
        
        # Create standardized response
        return ReactAgentResponse(
            response=response_text,
            session_id=session_id,
            status=ReactStatus.COMPLETED.value,
            reasoning_trace=reasoning_trace,
            tool_calls=tool_calls,
            processing_time_ms=processing_time_ms,
            iterations_used=len([step for step in reasoning_trace if step.step_type in ["thought", "action"]]),
            metadata=langgraph_output.get('metadata', {})
        )
        
    except Exception as e:
        logger.error(f"Failed to format LangGraph response: {e}")
        # If formatting fails, create error response with proper structure
        return create_error_response(
            error_message=f"Failed to format LangGraph response: {str(e)}",
            session_id=session_id,
            error_type="response_formatting_error",
            processing_time_ms=processing_time_ms
        )


def serialize_complex_objects(obj: Any) -> Any:
    """
    Serialize complex objects for JSON compatibility.
    Handles datetime objects, dataclasses, and other non-serializable types.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (ReasoningStep, ToolCall, ReactAgentResponse, ReactError)):
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):
        # Handle other objects with __dict__
        return {k: serialize_complex_objects(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, dict):
        return {k: serialize_complex_objects(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_complex_objects(item) for item in obj]
    elif isinstance(obj, tuple):
        return [serialize_complex_objects(item) for item in obj]
    else:
        return obj


def ensure_response_structure(response_data: Any, session_id: str) -> ReactAgentResponse:
    """
    Ensure any response data conforms to the standardized structure.
    This is a safety net to prevent attribute errors by fixing step_number issues.
    """
    try:
        if isinstance(response_data, ReactAgentResponse):
            # Validate and fix step numbers in existing response
            for i, step in enumerate(response_data.reasoning_trace):
                if not hasattr(step, 'step_number') or step.step_number <= 0:
                    step.step_number = i + 1
            return response_data
            
        elif isinstance(response_data, dict):
            # Fix reasoning trace step numbers before creating response
            if 'reasoning_trace' in response_data and isinstance(response_data['reasoning_trace'], list):
                for i, step_data in enumerate(response_data['reasoning_trace']):
                    if isinstance(step_data, dict):
                        # Ensure step_number is present and valid
                        if 'step_number' not in step_data or step_data['step_number'] <= 0:
                            step_data['step_number'] = i + 1
                        
                        # Ensure required fields are present
                        if 'step_type' not in step_data:
                            step_data['step_type'] = 'unknown'
                        if 'content' not in step_data:
                            step_data['content'] = step_data.get('thought', step_data.get('action', step_data.get('observation', '')))
                        if 'timestamp' not in step_data:
                            step_data['timestamp'] = datetime.utcnow().timestamp()
            
            # Fix tool calls structure
            if 'tool_calls' in response_data and isinstance(response_data['tool_calls'], list):
                for call_data in response_data['tool_calls']:
                    if isinstance(call_data, dict):
                        # Ensure required fields are present
                        if 'tool_name' not in call_data:
                            call_data['tool_name'] = call_data.get('name', 'unknown_tool')
                        if 'parameters' not in call_data:
                            call_data['parameters'] = call_data.get('args', {})
                        if 'execution_time' not in call_data:
                            call_data['execution_time'] = call_data.get('duration_ms', 0)
                        if 'timestamp' not in call_data:
                            call_data['timestamp'] = datetime.utcnow().isoformat()
            
            return ReactAgentResponse.from_dict(response_data)
        else:
            # Handle unexpected response types
            return ReactAgentResponse(
                response=str(response_data),
                session_id=session_id,
                status=ReactStatus.COMPLETED.value,
                reasoning_trace=[
                    ReasoningStep(
                        step_number=1,
                        step_type="unknown",
                        content=f"Converted from {type(response_data).__name__}: {str(response_data)}",
                        timestamp=datetime.utcnow().timestamp()
                    )
                ],
                tool_calls=[],
                metadata={"original_type": type(response_data).__name__}
            )
    except Exception as e:
        logger.error(f"Failed to ensure response structure: {e}")
        # Last resort: create minimal error response with proper structure
        return create_error_response(
            error_message=f"Failed to ensure response structure: {str(e)}",
            session_id=session_id,
            error_type="structure_validation_error"
        )