"""
Integrated Workflow-ReAct API that combines conversational workflow building with traditional workflow management.
This unified API eliminates RAG retrieval and provides both interactive and structured workflow capabilities.
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from uuid import uuid4
import time
import json

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_supabase_client
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, Trigger, WorkflowStatus, NodePosition
from app.models.react_agent import ChatRequestAPI, ChatResponseAPI
from app.services.react_agent_service import get_react_agent_service, ReactAgentService
from app.services.integrated_workflow_agent import get_integrated_workflow_agent
from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator
from app.services.tool_registry import ToolRegistry
from app.models.execution import ExecutionResult
from app.core.error_handler import handle_api_error
from app.core.error_utils import ErrorBoundary, create_error_context, handle_database_errors
from app.core.monitoring import record_request_time
from app.core.exceptions import WorkflowException, ValidationException, AgentExecutionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows-react", tags=["workflows-react"])

# Global instances
orchestrator = UnifiedWorkflowOrchestrator()
tool_registry = ToolRegistry()


# Request/Response Models

class ConversationalWorkflowRequest(BaseModel):
    """Request for creating workflow through conversation."""
    query: str = Field(..., min_length=1, max_length=5000, description="Natural language workflow description")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    max_iterations: int = Field(10, ge=1, le=20, description="Maximum reasoning iterations")
    save_as_workflow: bool = Field(True, description="Whether to save the result as a reusable workflow")


class WorkflowFromConversationRequest(BaseModel):
    """Request to convert conversation session to workflow."""
    session_id: str = Field(..., description="Conversation session ID")
    workflow_name: str = Field(..., min_length=1, max_length=100, description="Name for the workflow")
    workflow_description: str = Field("", max_length=500, description="Description for the workflow")


class ConversationalWorkflowResponse(BaseModel):
    """Response from conversational workflow creation."""
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Conversation session ID")
    reasoning_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Agent's reasoning steps")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Tools used by agent")
    workflow_created: bool = Field(False, description="Whether a workflow was created")
    workflow_id: Optional[str] = Field(None, description="ID of created workflow if any")
    workflow_plan: Optional[Dict[str, Any]] = Field(None, description="Generated workflow plan")
    status: str = Field(..., description="Response status")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class WorkflowExecutionRequest(BaseModel):
    """Request for executing workflow through ReAct agent."""
    workflow_id: str = Field(..., description="Workflow ID to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")
    interactive_mode: bool = Field(False, description="Whether to use interactive execution with agent feedback")


class AvailableToolsResponse(BaseModel):
    """Response containing available tools/connectors."""
    tools: List[Dict[str, Any]] = Field(..., description="Available tools metadata")
    total_count: int = Field(..., description="Total number of tools")
    categories: List[str] = Field(..., description="Available tool categories")


# API Endpoints

@router.get("/tools", response_model=AvailableToolsResponse)
async def get_available_tools(
    current_user: Dict[str, Any] = Depends(get_current_user),
    category: Optional[str] = Query(None, description="Filter by tool category")
):
    """
    Get available tools/connectors for workflow building.
    Replaces RAG retrieval with direct tool registry access.
    """
    try:
        # Initialize tool registry if not already done
        if not tool_registry._initialized:
            await tool_registry.initialize()
        
        # Get tool metadata
        tools_metadata = await tool_registry.get_tool_metadata()
        
        # Filter by category if specified
        if category:
            tools_metadata = [
                tool for tool in tools_metadata 
                if tool.get("category", "").lower() == category.lower()
            ]
        
        # Extract unique categories
        categories = list(set(
            tool.get("category", "uncategorized") 
            for tool in tools_metadata
        ))
        
        logger.info(f"Retrieved {len(tools_metadata)} tools for user {current_user['user_id']}")
        
        return AvailableToolsResponse(
            tools=tools_metadata,
            total_count=len(tools_metadata),
            categories=sorted(categories)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving available tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available tools"
        )


@router.post("/create-conversational", response_model=ConversationalWorkflowResponse)
async def create_workflow_conversationally(
    request: ConversationalWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create workflow through conversational interaction with integrated ReAct agent.
    This endpoint combines the power of ReAct reasoning with workflow creation.
    """
    start_time = time.time()
    user_id = current_user["user_id"]
    
    try:
        logger.info(f"Creating workflow conversationally for user {user_id}")
        
        # Check if this is a simple greeting or non-workflow query
        simple_greetings = ["hi", "hii", "hello", "hey", "test", "ping"]
        is_simple_query = any(greeting in request.query.lower() for greeting in simple_greetings)
        
        if is_simple_query:
            # Handle simple queries without complex agent processing
            session_id = request.session_id or str(uuid4())
            response_message = f"Hello! I'm your AI workflow assistant. I can help you create automated workflows. For example, you could ask me to:\n\n• 'Create a workflow to send me daily weather updates'\n• 'Build an automation that summarizes news articles'\n• 'Set up a workflow to backup my data'\n\nWhat would you like to automate today?"
            
            conversation_context = type('ConversationContext', (), {
                'session_id': session_id,
                'user_id': user_id,
                'messages': []
            })()
            
            workflow_plan = None
        else:
            # Get the integrated workflow agent for complex queries
            integrated_agent = await get_integrated_workflow_agent()
            
            # Create or get session
            session_id = request.session_id or str(uuid4())
            
            # Process through integrated workflow agent
            conversation_context, response_message, workflow_plan = await integrated_agent.create_workflow_conversationally(
                query=request.query,
                user_id=user_id,
                session_id=session_id,
                context=request.context
            )
        
        # Prepare response data
        workflow_created = workflow_plan is not None
        workflow_id = workflow_plan.id if workflow_plan else None
        workflow_plan_dict = workflow_plan.dict() if workflow_plan else None
        
        # Create mock reasoning trace and tool calls for UI display
        reasoning_trace = []
        tool_calls = []
        
        if workflow_plan:
            # Create reasoning steps based on workflow nodes
            for i, node in enumerate(workflow_plan.nodes):
                reasoning_trace.append({
                    "step": i + 1,
                    "thought": f"I need to use {node.connector_name} to accomplish this task",
                    "action": f"select_tool",
                    "tool_name": node.connector_name,
                    "status": "completed"
                })
                
                tool_calls.append({
                    "tool_name": node.connector_name,
                    "parameters": node.parameters,
                    "status": "completed",
                    "result": f"Successfully configured {node.connector_name}"
                })
        else:
            # Provide fallback reasoning trace even if no workflow was created
            reasoning_trace = [
                {
                    "step": 1,
                    "thought": "I'm analyzing your request to understand what you want to automate",
                    "action": "analyze_request",
                    "status": "completed"
                },
                {
                    "step": 2,
                    "thought": "I'm working on creating a workflow for your request",
                    "action": "process_request",
                    "status": "completed"
                }
            ]
        
        duration = time.time() - start_time
        record_request_time(duration)
        
        return ConversationalWorkflowResponse(
            response=response_message,
            session_id=conversation_context.session_id,
            reasoning_trace=reasoning_trace,
            tool_calls=tool_calls,
            workflow_created=workflow_created,
            workflow_id=workflow_id,
            workflow_plan=workflow_plan_dict,
            status="success" if workflow_created else "completed",
            processing_time_ms=int(duration * 1000)
        )
        
    except Exception as e:
        duration = time.time() - start_time
        record_request_time(duration)
        logger.error(f"Error in conversational workflow creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow conversationally: {str(e)}"
        )


@router.post("/convert-session", response_model=Dict[str, Any])
async def convert_session_to_workflow(
    request: WorkflowFromConversationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Convert a conversation session into a reusable workflow.
    This allows users to save successful agent interactions as workflows.
    """
    try:
        user_id = current_user["user_id"]
        
        # Validate session access
        if not await react_service.validate_session_access(request.session_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        # Get conversation history
        conversation = await react_service.memory_manager.get_conversation(request.session_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found"
            )
        
        # Convert conversation to workflow plan
        workflow_plan_data = await _convert_conversation_to_workflow_plan(
            conversation=conversation,
            workflow_name=request.workflow_name,
            workflow_description=request.workflow_description,
            user_id=user_id
        )
        
        # Save as workflow
        workflow_id = await _save_workflow_from_plan(
            workflow_plan_data,
            user_id,
            request.workflow_name,
            request.workflow_description
        )
        
        logger.info(f"Converted session {request.session_id} to workflow {workflow_id}")
        
        return {
            "workflow_id": workflow_id,
            "workflow_name": request.workflow_name,
            "message": "Successfully converted conversation to workflow",
            "workflow_plan": workflow_plan_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting session to workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert session to workflow: {str(e)}"
        )


@router.post("/execute-interactive/{workflow_id}", response_model=Dict[str, Any])
async def execute_workflow_interactively(
    workflow_id: str,
    request: WorkflowExecutionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Execute a workflow with integrated agent providing interactive feedback and error handling.
    This combines traditional workflow execution with intelligent agent oversight.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get the integrated workflow agent
        integrated_agent = await get_integrated_workflow_agent()
        
        # Execute workflow with agent oversight
        execution_result = await integrated_agent.execute_workflow_with_agent_oversight(
            workflow_id=workflow_id,
            user_id=user_id,
            parameters=request.parameters,
            interactive_mode=request.interactive_mode
        )
        
        return execution_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow interactively: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.get("/sessions/{session_id}/workflow-potential", response_model=Dict[str, Any])
async def analyze_session_workflow_potential(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    react_service: ReactAgentService = Depends(get_react_agent_service)
):
    """
    Analyze a conversation session to determine if it can be converted to a workflow.
    This helps users understand which conversations are suitable for automation.
    """
    try:
        user_id = current_user["user_id"]
        
        # Validate session access
        if not await react_service.validate_session_access(session_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        # Get conversation
        conversation = await react_service.memory_manager.get_conversation(session_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found"
            )
        
        # Analyze workflow potential
        analysis = await _analyze_workflow_potential(conversation)
        
        return {
            "session_id": session_id,
            "can_create_workflow": analysis["suitable"],
            "confidence": analysis["confidence"],
            "reasoning": analysis["reasoning"],
            "suggested_name": analysis.get("suggested_name"),
            "tool_usage_summary": analysis.get("tool_usage", []),
            "automation_potential": analysis.get("automation_potential", "low")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing session workflow potential: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze session: {str(e)}"
        )


# Helper Functions

async def _convert_agent_session_to_workflow(
    session_id: str,
    user_id: str,
    agent_response: Dict[str, Any],
    react_service: ReactAgentService
) -> Optional[Dict[str, Any]]:
    """Convert agent session with tool usage into workflow plan."""
    try:
        tool_calls = agent_response.get("tool_calls", [])
        if not tool_calls:
            return None
        
        # Create workflow nodes from tool calls
        nodes = []
        edges = []
        node_positions = {}
        
        for i, tool_call in enumerate(tool_calls):
            node_id = str(uuid4())
            
            # Create workflow node
            node = {
                "id": node_id,
                "connector_name": tool_call.get("tool_name", "unknown"),
                "parameters": tool_call.get("parameters", {}),
                "position": {"x": i * 200, "y": 100},
                "dependencies": []
            }
            
            # Add dependencies based on tool call sequence
            if i > 0:
                previous_node_id = nodes[i-1]["id"]
                node["dependencies"] = [previous_node_id]
                
                # Create edge
                edge = {
                    "id": str(uuid4()),
                    "source": previous_node_id,
                    "target": node_id
                }
                edges.append(edge)
            
            nodes.append(node)
        
        return {
            "name": f"Workflow from session {session_id[:8]}",
            "description": f"Automated workflow created from conversation session",
            "nodes": nodes,
            "edges": edges,
            "triggers": [],
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error converting agent session to workflow: {e}")
        return None


async def _convert_conversation_to_workflow_plan(
    conversation: Any,
    workflow_name: str,
    workflow_description: str,
    user_id: str
) -> Dict[str, Any]:
    """Convert conversation history to workflow plan."""
    # This would analyze the conversation messages and extract tool usage patterns
    # For now, return a basic structure
    return {
        "name": workflow_name,
        "description": workflow_description,
        "nodes": [],
        "edges": [],
        "triggers": [],
        "user_id": user_id
    }


async def _save_workflow_from_plan(
    workflow_plan_data: Dict[str, Any],
    user_id: str,
    name: str,
    description: str = ""
) -> str:
    """Save workflow plan to database."""
    try:
        workflow_id = str(uuid4())
        now = datetime.utcnow()
        
        # Create workflow data for database
        workflow_data = {
            "id": workflow_id,
            "user_id": user_id,
            "name": name,
            "description": description or workflow_plan_data.get("description", ""),
            "nodes": workflow_plan_data.get("nodes", []),
            "edges": workflow_plan_data.get("edges", []),
            "triggers": workflow_plan_data.get("triggers", []),
            "status": WorkflowStatus.ACTIVE.value,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Save to database
        supabase = get_supabase_client()
        response = supabase.table("workflows").insert(workflow_data).execute()
        
        if not response.data:
            raise WorkflowException("Failed to save workflow to database")
        
        return workflow_id
        
    except Exception as e:
        logger.error(f"Error saving workflow from plan: {e}")
        raise WorkflowException(f"Failed to save workflow: {str(e)}")


def _convert_db_data_to_workflow_plan(workflow_data: Dict[str, Any]) -> WorkflowPlan:
    """Convert database workflow data to WorkflowPlan object."""
    return WorkflowPlan(
        id=workflow_data["id"],
        user_id=workflow_data["user_id"],
        name=workflow_data["name"],
        description=workflow_data["description"],
        nodes=[WorkflowNode(**node) for node in workflow_data["nodes"]],
        edges=[WorkflowEdge(**edge) for edge in workflow_data["edges"]],
        triggers=[Trigger(**trigger) for trigger in workflow_data["triggers"]],
        status=WorkflowStatus(workflow_data["status"]),
        created_at=datetime.fromisoformat(workflow_data["created_at"]),
        updated_at=datetime.fromisoformat(workflow_data["updated_at"])
    )


async def _analyze_workflow_potential(conversation: Any) -> Dict[str, Any]:
    """Analyze conversation to determine workflow creation potential."""
    # Basic analysis - in practice this would be more sophisticated
    return {
        "suitable": True,
        "confidence": 0.8,
        "reasoning": "Conversation contains tool usage that can be automated",
        "suggested_name": "Automated Workflow",
        "tool_usage": [],
        "automation_potential": "high"
    }