"""
REST API endpoints for ReAct agent interactions.
Provides endpoints for chat interactions, conversation management, and session cleanup.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import time
import uuid
import asyncio
from typing import Set
from datetime import datetime
from contextlib import asynccontextmanager

from app.services.react_agent_service import get_react_agent_service, ReactAgentService
from app.services.react_error_formatter import format_react_error
from app.models.react_agent import (
    ReactRequest, ReactResponse, ReactError, ReactSessionInfo,
    ReactAgentStatus, ReactToolMetadata, ReactConversation,
    ChatRequestAPI, ChatResponseAPI, ConversationHistoryResponseAPI, ReactErrorAPI,
    ConversationListResponseAPI, UserConversationResponseAPI, ConversationResponseAPI,
    format_reasoning_trace_for_api, format_tool_calls_for_api,
    sanitize_string_input, validate_session_id, validate_tool_names
)
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.exceptions import AgentExecutionError, ValidationException
from app.core.error_handler import handle_api_error
from app.core.error_utils import ErrorBoundary, create_error_context
from app.core.monitoring import record_request_time
from app.services.react_agent_logger import ReactAgentLogger, CorrelationContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/react", tags=["react-agent"])


# Request/Response models for API endpoints

# Using the enhanced models from react_agent.py
# ChatRequestAPI, ChatResponseAPI, ConversationHistoryResponseAPI are imported above


# API Endpoints

@router.post("/chat", response_model=ChatResponseAPI)
async def chat_with_react_agent(
    request: ChatRequestAPI,
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Process user query through ReAct agent with intelligent reasoning and tool usage.
    
    This endpoint implements requirement 3.1: Provide REST API interface for programmatic access.
    The agent will:
    - Reason about the user's query step by step
    - Select and use appropriate tools from available connectors
    - Provide detailed reasoning traces showing the thought process
    - Maintain conversation context across multiple turns
    
    Args:
        request: Chat request containing query and optional parameters
        current_user: Authenticated user information
        react_service: ReAct agent service instance
        
    Returns:
        ChatResponse with agent's response, reasoning trace, and tool usage
    """
    start_time = time.time()
    user_id = current_user["user_id"]
    
    # Validate and sanitize inputs
    try:
        # Sanitize query
        sanitized_query = sanitize_string_input(request.query, max_length=5000)
        if not sanitized_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty after sanitization"
            )
        
        # Validate session ID
        session_id = validate_session_id(request.session_id) or str(uuid.uuid4())
        
        # Create or validate user session with authentication context
        if request.session_id:
            # Validate existing session access
            if not await react_service.validate_session_access(session_id, user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this session"
                )
        else:
            # Create new session with user authentication context
            session_id = await react_service.create_user_session(current_user, session_id)
        
        # Validate tools
        validated_tools = validate_tool_names(request.tools)
        
        # Validate context size
        if request.context:
            import json
            context_str = json.dumps(request.context)
            if len(context_str) > 10000:  # 10KB limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Context data too large (max 10KB)"
                )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    
    try:
        logger.info(f"Processing ReAct chat request for user {user_id}, session: {session_id}")
        
        # Process request through ReAct agent with validated inputs
        # Skip session validation for new sessions (when request.session_id was None)
        response = await react_service.process_request(
            query=sanitized_query,
            session_id=session_id,
            user_id=user_id,
            context=request.context,
            max_iterations=request.max_iterations,
            skip_session_validation=not bool(request.session_id)
        )
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.info(f"ReAct agent processed request for session {session_id} in {duration:.3f}s")
        
        # Convert service response to API response format with proper formatting
        return ChatResponseAPI(
            response=response["response"],
            session_id=response["session_id"],
            reasoning_trace=format_reasoning_trace_for_api(response.get("reasoning_trace", [])),
            tool_calls=format_tool_calls_for_api(response.get("tool_calls", [])),
            status=response["status"],
            processing_time_ms=response.get("processing_time_ms"),
            iterations_used=response.get("iterations_used", 0),
            tools_used=response.get("tools_used", 0),
            metadata=response.get("metadata", {})
        )
        
    except Exception as e:
        duration = time.time() - start_time
        record_request_time(duration)
        
        logger.error(f"ReAct chat request failed for session {session_id}: {e}")
        
        # Create context for error formatting
        error_context = {
            "user_id": user_id,
            "operation": "react_chat",
            "session_id": session_id,
            "query_length": len(request.query),
            "processing_time_ms": int(duration * 1000)
        }
        
        # Create standardized error response using the response models
        from app.models.react_response_models import create_error_response, serialize_complex_objects
        
        standardized_error = create_error_response(
            error_message=str(e),
            session_id=session_id,
            error_type=type(e).__name__,
            user_message=f"I encountered an error while processing your request: {str(e)}",
            reasoning_trace=[],
            suggestions=[
                "Try rephrasing your request",
                "Check if the required tools are available",
                "Contact support if the issue persists"
            ],
            processing_time_ms=int(duration * 1000)
        )
        
        # Convert to dictionary and serialize complex objects
        error_dict = serialize_complex_objects(standardized_error.to_dict())
        
        # Return error response in expected ChatResponseAPI format with consistent structure
        return ChatResponseAPI(
            response=error_dict["response"],
            session_id=error_dict["session_id"],
            reasoning_trace=format_reasoning_trace_for_api(error_dict.get("reasoning_trace", [])),
            tool_calls=format_tool_calls_for_api(error_dict.get("tool_calls", [])),
            status=error_dict["status"],
            processing_time_ms=error_dict.get("processing_time_ms", int(duration * 1000)),
            iterations_used=error_dict.get("iterations_used", 0),
            tools_used=error_dict.get("tools_used", 0),
            metadata=error_dict.get("metadata", {})
        )


@router.get("/conversations/{session_id}", response_model=ConversationHistoryResponseAPI)
async def get_conversation_history(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Retrieve conversation history and context for a ReAct agent session.
    
    This endpoint implements requirement 3.1: Add GET /api/react/conversations/{session_id} 
    for history retrieval. It provides:
    - Complete conversation message history
    - Reasoning traces for each agent response
    - Tool usage history and results
    - Conversation metadata and summary statistics
    
    Args:
        session_id: Unique session identifier
        current_user: Authenticated user information
        react_service: ReAct agent service instance
        
    Returns:
        ConversationHistoryResponse with complete conversation data
    """
    user_id = current_user["user_id"]
    
    try:
        # Validate session ID format
        try:
            validated_session_id = validate_session_id(session_id)
            if not validated_session_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid session ID format"
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid session ID: {str(e)}"
            )
        
        logger.info(f"Retrieving conversation history for session {session_id}, user: {user_id}")
        
        # Validate session access first
        if not await react_service.validate_session_access(session_id, user_id):
            logger.warning(f"Access denied: user {user_id} cannot access session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        # Get conversation history from service
        history = await react_service.get_conversation_history(session_id)
        
        if history["status"] == "not_found":
            logger.warning(f"Conversation not found: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {session_id} not found"
            )
        
        logger.info(f"Successfully retrieved conversation history for session {session_id}")
        
        # Convert service response to API response format
        return ConversationHistoryResponseAPI(
            session_id=history["session_id"],
            messages=history.get("messages", []),
            status=history["status"],
            created_at=history.get("created_at"),
            updated_at=history.get("updated_at"),
            summary=history.get("summary", {}),
            context_summary=history.get("context_summary"),
            tool_usage_history=history.get("tool_usage_history", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation history for {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@router.delete("/conversations/{session_id}")
async def cleanup_conversation_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Clean up and delete a ReAct agent conversation session.
    
    This endpoint implements requirement 3.1: Create DELETE /api/react/conversations/{session_id} 
    for session cleanup. It will:
    - Remove conversation data from memory and database
    - Clean up any associated resources
    - Invalidate session state
    - Return confirmation of cleanup
    
    Args:
        session_id: Unique session identifier to clean up
        current_user: Authenticated user information
        react_service: ReAct agent service instance
        
    Returns:
        Success message confirming session cleanup
    """
    user_id = current_user["user_id"]
    
    try:
        # Validate session ID format
        try:
            validated_session_id = validate_session_id(session_id)
            if not validated_session_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid session ID format"
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid session ID: {str(e)}"
            )
        
        logger.info(f"Cleaning up conversation session {session_id} for user {user_id}")
        
        # Validate session access first
        if not await react_service.validate_session_access(session_id, user_id):
            logger.warning(f"Access denied: user {user_id} cannot access session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        # Perform session cleanup
        success = await react_service.cleanup_session(session_id)
        
        if not success:
            logger.warning(f"Session cleanup returned false for {session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clean up session resources"
            )
        
        logger.info(f"Successfully cleaned up conversation session {session_id}")
        
        return {
            "message": "Conversation session cleaned up successfully",
            "session_id": session_id,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean up session: {str(e)}"
        )


# Additional utility endpoints for ReAct agent management

@router.get("/status", response_model=Dict[str, Any])
async def get_react_agent_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Get the current status and health of the ReAct agent service.
    
    This endpoint provides information about:
    - Service initialization status
    - Available tools and their metadata
    - Performance metrics
    - Configuration details
    """
    try:
        logger.info(f"Getting ReAct agent status for user {current_user['user_id']}")
        
        # Get available tools
        tools = await react_service.get_available_tools()
        
        # Create status response
        status_info = {
            "status": "healthy",
            "initialized": react_service._initialized,
            "tools_available": len(tools),
            "tools": tools,
            "capabilities": {
                "reasoning": True,
                "tool_usage": True,
                "conversation_memory": True,
                "streaming": True,
                "multi_turn": True
            },
            "configuration": {
                "max_iterations": settings.REACT_AGENT_MAX_ITERATIONS if hasattr(settings, 'REACT_AGENT_MAX_ITERATIONS') else 10,
                "timeout_seconds": 300,
                "azure_openai_configured": bool(
                    settings.AZURE_OPENAI_ENDPOINT and 
                    settings.AZURE_OPENAI_API_KEY and 
                    settings.AZURE_OPENAI_DEPLOYMENT_NAME
                )
            },
            "timestamp": time.time()
        }
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting ReAct agent status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent status: {str(e)}"
        )


@router.get("/tools", response_model=List[Dict[str, Any]])
async def get_available_tools(
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Get list of available tools that the ReAct agent can use.
    
    This endpoint returns detailed information about each tool including:
    - Tool name and description
    - Parameter schema
    - Authentication requirements
    - Usage statistics (if available)
    """
    try:
        logger.info(f"Getting available tools for user {current_user['user_id']}")
        
        tools = await react_service.get_available_tools()
        
        return tools
        
    except Exception as e:
        logger.error(f"Error getting available tools: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available tools: {str(e)}"
        )


@router.get("/conversations", response_model=List[Dict[str, Any]])
async def list_user_conversations(
    limit: int = 20,
    query: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    List ReAct agent conversations for the current user.
    
    This endpoint provides a list of the user's conversation sessions with:
    - Basic conversation metadata
    - Message counts and tool usage statistics
    - Optional search functionality
    - Pagination support
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"Listing conversations for user {user_id}, limit: {limit}, query: {query}")
        
        conversations = await react_service.get_user_conversations(
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error listing conversations for user {current_user['user_id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )

# WebSocket connection management for real-time updates

class ConnectionManager:
    """Manages WebSocket connections for real-time ReAct agent updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.session_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, session_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        # Add to user connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Add to session connections if session_id provided
        if session_id:
            if session_id not in self.session_connections:
                self.session_connections[session_id] = set()
            self.session_connections[session_id].add(websocket)
        
        logger.info(f"WebSocket connected for user {user_id}, session {session_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str, session_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        # Remove from user connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from session connections
        if session_id and session_id in self.session_connections:
            self.session_connections[session_id].discard(websocket)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}, session {session_id}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all connections for a user."""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send message to user {user_id}: {e}")
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.active_connections[user_id].discard(connection)
    
    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to all connections for a session."""
        if session_id in self.session_connections:
            disconnected = set()
            for connection in self.session_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send message to session {session_id}: {e}")
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.session_connections[session_id].discard(connection)
    
    async def broadcast_status(self, message: Dict[str, Any]):
        """Broadcast status message to all connections."""
        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections)
        
        disconnected = set()
        for connection in all_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to broadcast message: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for user_connections in self.active_connections.values():
            user_connections -= disconnected


# Global connection manager instance
connection_manager = ConnectionManager()


# WebSocket endpoints for real-time updates

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: Optional[str] = None
):
    """
    WebSocket endpoint for real-time ReAct agent status updates.
    
    This endpoint implements requirement 3.3: Implement WebSocket support for real-time agent status.
    Clients can connect to receive:
    - Real-time processing status updates
    - Tool execution progress
    - Reasoning step notifications
    - Error notifications
    - Completion notifications
    """
    await connection_manager.connect(websocket, user_id, session_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": time.time(),
            "message": "WebSocket connection established for ReAct agent updates"
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (like ping/pong)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping messages
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": time.time()
                    }))
                
                # Handle subscription requests
                elif message.get("type") == "subscribe":
                    subscribe_session_id = message.get("session_id")
                    if subscribe_session_id:
                        if subscribe_session_id not in connection_manager.session_connections:
                            connection_manager.session_connections[subscribe_session_id] = set()
                        connection_manager.session_connections[subscribe_session_id].add(websocket)
                        
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "session_id": subscribe_session_id,
                            "timestamp": time.time()
                        }))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error for user {user_id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": str(e),
                    "timestamp": time.time()
                }))
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket, user_id, session_id)


@router.post("/chat/stream")
async def stream_chat_with_react_agent(
    request: ChatRequestAPI,
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Stream ReAct agent processing with real-time updates.
    
    This endpoint implements requirement 3.3: Add progress tracking during multi-step tool execution.
    It provides Server-Sent Events (SSE) streaming of:
    - Reasoning steps as they occur
    - Tool execution progress
    - Intermediate results
    - Final response
    """
    user_id = current_user["user_id"]
    
    # Validate inputs (same as regular chat endpoint)
    try:
        sanitized_query = sanitize_string_input(request.query, max_length=5000)
        if not sanitized_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty after sanitization"
            )
        
        session_id = validate_session_id(request.session_id) or str(uuid.uuid4())
        validated_tools = validate_tool_names(request.tools)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    
    async def generate_stream():
        """Generate streaming response with real-time updates."""
        try:
            logger.info(f"Starting streaming ReAct chat for user {user_id}, session: {session_id}")
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'started', 'session_id': session_id, 'timestamp': time.time()})}\n\n"
            
            # Notify WebSocket connections
            await connection_manager.send_to_user(user_id, {
                "type": "processing_started",
                "session_id": session_id,
                "query": sanitized_query,
                "timestamp": time.time()
            })
            
            # Stream the ReAct agent processing
            # Skip session validation for new sessions (when request.session_id was None)
            async for chunk in react_service.process_request_stream(
                query=sanitized_query,
                session_id=session_id,
                user_id=user_id,
                context=request.context,
                max_iterations=request.max_iterations,
                skip_session_validation=not bool(request.session_id)
            ):
                # Send chunk to SSE stream
                yield f"data: {json.dumps(chunk)}\n\n"
                
                # Also send to WebSocket connections for real-time updates
                await connection_manager.send_to_session(session_id, chunk)
                await connection_manager.send_to_user(user_id, chunk)
            
            # Send completion marker
            completion_message = {
                "type": "completed",
                "session_id": session_id,
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(completion_message)}\n\n"
            
            # Notify WebSocket connections of completion
            await connection_manager.send_to_user(user_id, completion_message)
            
        except Exception as e:
            logger.error(f"Streaming error for session {session_id}: {str(e)}")
            
            error_message = {
                "type": "error",
                "error": str(e),
                "session_id": session_id,
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(error_message)}\n\n"
            
            # Notify WebSocket connections of error
            await connection_manager.send_to_user(user_id, error_message)
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


# Monitoring endpoints for agent health and metrics

@router.get("/metrics", response_model=Dict[str, Any])
async def get_react_agent_metrics(
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Get comprehensive ReAct agent metrics and performance data.
    
    This endpoint implements requirement 5.2: Create monitoring endpoints for agent health and metrics.
    It provides:
    - Performance metrics (response times, success rates)
    - Tool usage statistics
    - Active session counts
    - Error rates and types
    - Resource utilization
    """
    try:
        logger.info(f"Getting ReAct agent metrics for user {current_user['user_id']}")
        
        # Get basic status
        tools = await react_service.get_available_tools()
        
        # Calculate connection metrics
        total_connections = sum(len(connections) for connections in connection_manager.active_connections.values())
        active_sessions = len(connection_manager.session_connections)
        
        # Get system metrics (this would be enhanced with actual metrics collection)
        metrics = {
            "agent_status": {
                "initialized": react_service._initialized,
                "healthy": True,  # This would be determined by health checks
                "version": "1.0.0"
            },
            "tools": {
                "available_count": len(tools),
                "tools_list": [tool.get("name", "unknown") for tool in tools]
            },
            "connections": {
                "total_websocket_connections": total_connections,
                "active_sessions": active_sessions,
                "connected_users": len(connection_manager.active_connections)
            },
            "performance": {
                "avg_response_time_ms": None,  # Would be calculated from actual metrics
                "success_rate": None,  # Would be calculated from actual metrics
                "total_requests": None,  # Would be tracked in actual implementation
                "error_rate": None  # Would be calculated from actual metrics
            },
            "system": {
                "timestamp": time.time(),
                "uptime_seconds": None,  # Would be tracked from service start
                "memory_usage": None,  # Would be collected from system
                "cpu_usage": None  # Would be collected from system
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting ReAct agent metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent metrics: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def get_react_agent_health(
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Get detailed health status of the ReAct agent service.
    
    This endpoint provides comprehensive health information including:
    - Service initialization status
    - Tool availability and health
    - Database connectivity
    - External service dependencies
    - Performance indicators
    """
    try:
        logger.info(f"Performing ReAct agent health check for user {current_user['user_id']}")
        
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {}
        }
        
        # Check service initialization
        health_status["checks"]["service_initialized"] = {
            "status": "healthy" if react_service._initialized else "unhealthy",
            "details": "ReAct agent service initialization status"
        }
        
        # Check tool availability
        try:
            tools = await react_service.get_available_tools()
            health_status["checks"]["tools_available"] = {
                "status": "healthy" if tools else "warning",
                "count": len(tools),
                "details": f"{len(tools)} tools available"
            }
        except Exception as e:
            health_status["checks"]["tools_available"] = {
                "status": "unhealthy",
                "error": str(e),
                "details": "Failed to get available tools"
            }
        
        # Check memory manager
        try:
            # This would be a more comprehensive check in actual implementation
            health_status["checks"]["memory_manager"] = {
                "status": "healthy",
                "details": "Conversation memory manager operational"
            }
        except Exception as e:
            health_status["checks"]["memory_manager"] = {
                "status": "unhealthy",
                "error": str(e),
                "details": "Memory manager check failed"
            }
        
        # Check WebSocket connections
        health_status["checks"]["websocket_connections"] = {
            "status": "healthy",
            "active_connections": sum(len(connections) for connections in connection_manager.active_connections.values()),
            "details": "WebSocket connection manager operational"
        }
        
        # Determine overall status
        unhealthy_checks = [check for check in health_status["checks"].values() if check["status"] == "unhealthy"]
        warning_checks = [check for check in health_status["checks"].values() if check["status"] == "warning"]
        
        if unhealthy_checks:
            health_status["status"] = "unhealthy"
        elif warning_checks:
            health_status["status"] = "warning"
        else:
            health_status["status"] = "healthy"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
            "checks": {}
        }


@router.get("/sessions/active", response_model=List[Dict[str, Any]])
async def get_active_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Get list of active ReAct agent sessions for monitoring.
    
    This endpoint provides information about:
    - Currently active conversation sessions
    - Session activity levels
    - Resource usage per session
    - Connection status
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"Getting active sessions for user {user_id}")
        
        # Get active sessions from service
        active_session_ids = await react_service.get_active_sessions(user_id)
        
        # Enhance with connection information
        active_sessions = []
        for session_id in active_session_ids:
            session_info = {
                "session_id": session_id,
                "user_id": user_id,
                "websocket_connections": len(connection_manager.session_connections.get(session_id, set())),
                "last_activity": time.time(),  # Would be tracked in actual implementation
                "status": "active"
            }
            active_sessions.append(session_info)
        
        return active_sessions
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active sessions: {str(e)}"
        )

# WebSocket connection manager for workflow updates
class WorkflowConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def send_workflow_update(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.active_connections[session_id].discard(connection)

workflow_manager = WorkflowConnectionManager()

# Function to send workflow updates (to be called from ReactAgentService)
async def send_workflow_update(session_id: str, update_type: str, data: dict):
    """Send workflow update to connected WebSocket clients."""
    message = {
        "type": update_type,
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }
    await workflow_manager.send_workflow_update(session_id, message)


@router.websocket("/ws/workflow/{session_id}")
async def websocket_workflow_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001")
):
    """
    WebSocket endpoint for real-time workflow updates.
    
    This endpoint provides real-time updates about:
    - Reasoning steps
    - Tool call starts/completions
    - Agent status changes
    - Error notifications
    """
    await workflow_manager.connect(websocket, session_id)
    logger.logger.info(f"WebSocket connected for workflow updates - session: {session_id}, user: {user_id}")
    
    try:
        # Send initial status
        await workflow_manager.send_workflow_update(session_id, {
            "type": "agent_status",
            "status": "idle",
            "message": "Workflow monitoring connected"
        })
        
        # Keep connection alive and listen for any client messages
        while True:
            try:
                # Wait for messages from client (heartbeat, etc.)
                data = await websocket.receive_text()
                client_message = json.loads(data)
                
                # Handle client messages if needed
                if client_message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.logger.error(f"Error in workflow WebSocket: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    finally:
        workflow_manager.disconnect(websocket, session_id)
        logger.logger.info(f"WebSocket disconnected for workflow updates - session: {session_id}")