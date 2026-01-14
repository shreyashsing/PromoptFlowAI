"""
Individual Node Execution API

This module provides endpoints for executing individual workflow nodes
and previewing their data output, similar to n8n's node execution system.
"""
import logging
import re
import json
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
import time
import json

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_supabase_client
from app.models.connector import ConnectorExecutionContext, ConnectorResult
from app.connectors.registry import connector_registry
from app.services.auth_tokens import get_auth_token_service
from app.services.auth_context_manager import AuthContextManager
from app.core.error_handler import handle_api_error
from app.core.exceptions import ConnectorException, AuthenticationException
from app.services.output_formatter import format_connector_output

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nodes", tags=["node-execution"])


def substitute_template_variables(parameters: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Substitute template variables in parameters with actual values from previous results.
    
    Supports patterns like:
    - {perplexity_search.result} -> previous_results['perplexity_search']['response'] 
    - {node_name.field} -> previous_results['node_name']['field']
    - {user.email} -> keeps as is (handled by connector)
    """
    if not parameters or not previous_results:
        return parameters
        
    processed_params = {}
    
    for key, value in parameters.items():
        if isinstance(value, str):
            # Find template variables like {node_name.field}
            template_pattern = r'\{([^}]+)\}'
            matches = re.findall(template_pattern, value)
            
            processed_value = value
            for match in matches:
                if '.' in match:
                    node_name, field = match.split('.', 1)
                    logger.info(f"🔍 Looking for node: {node_name}, field: {field}")
                    
                    # Check if node exists in previous results
                    if node_name in previous_results:
                        node_data = previous_results[node_name]
                        logger.info(f"📊 Node data keys: {list(node_data.keys()) if isinstance(node_data, dict) else type(node_data)}")
                        
                        # Map common field names to actual result keys
                        field_mapping = {
                            'result': 'response',     # {node.result} -> response field
                            'output': 'response',     # {node.output} -> response field  
                            'data': 'response',       # {node.data} -> response field
                            'content': 'response',    # {node.content} -> response field
                            'text': 'response',       # {node.text} -> response field
                            'answer': 'response',     # {node.answer} -> response field
                            'response': 'response',   # {node.response} -> response field
                        }
                        
                        # Special mappings for specific connectors
                        if node_name == 'text_summarizer':
                            field_mapping.update({
                                'result': 'summary',
                                'output': 'summary', 
                                'text': 'summary',
                                'content': 'summary'
                            })
                        elif node_name == 'gmail_connector':
                            field_mapping.update({
                                'result': 'message_id',
                                'id': 'message_id'
                            })
                        
                        # Try the mapped field first, then the original field
                        possible_fields = [field_mapping.get(field, field), field]
                        if field != 'response' and field != 'summary':
                            possible_fields.extend(['response', 'summary'])  # Always try common fields as fallback
                        
                        replacement_value = None
                        used_field = None
                        
                        for possible_field in possible_fields:
                            if isinstance(node_data, dict) and possible_field in node_data:
                                replacement_value = node_data[possible_field]
                                used_field = possible_field
                                break
                        
                        if replacement_value is not None:
                            if isinstance(replacement_value, (dict, list)):
                                replacement_value = json.dumps(replacement_value)
                            processed_value = processed_value.replace(f'{{{match}}}', str(replacement_value))
                            logger.info(f"✅ Template substitution: {{{match}}} -> {node_name}.{used_field} (first 100 chars: {str(replacement_value)[:100]}...)")
                        else:
                            available_fields = list(node_data.keys()) if isinstance(node_data, dict) else 'Not a dict'
                            logger.warning(f"⚠️ Template variable {{{match}}} not found. Available fields in {node_name}: {available_fields}")
                    else:
                        logger.warning(f"⚠️ Node '{node_name}' not found in previous results. Available nodes: {list(previous_results.keys())}")
                        
            processed_params[key] = processed_value
        else:
            processed_params[key] = value
            
    return processed_params


class NodeExecutionRequest(BaseModel):
    """Request model for executing individual nodes."""
    connector_name: str = Field(..., description="Name of the connector to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Node parameters")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="Authentication configuration")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    node_id: Optional[str] = Field(None, description="Node ID within workflow")
    previous_results: Dict[str, Any] = Field(default_factory=dict, description="Results from previous nodes in sequential execution")


class NodeExecutionResponse(BaseModel):
    """Response model for node execution results."""
    success: bool
    execution_id: str
    connector_name: str
    output_data: Dict[str, Any]
    formatted_output: Optional[str] = None
    execution_time_ms: int
    timestamp: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NodeDataPreviewResponse(BaseModel):
    """Response model for node data preview."""
    connector_name: str
    data_structure: Dict[str, Any]
    sample_data: Dict[str, Any]
    data_types: Dict[str, str]
    record_count: Optional[int] = None
    preview_truncated: bool = False


@router.post("/execute", response_model=NodeExecutionResponse)
async def execute_node(
    request: NodeExecutionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Execute an individual workflow node and return its output data.
    
    This endpoint allows users to test and preview the output of individual
    connectors without running the entire workflow, similar to n8n's node execution.
    """
    start_time = time.time()
    execution_id = str(uuid4())
    user_id = current_user["user_id"]
    
    logger.info(f"Executing node {request.connector_name} for user {user_id}")
    logger.info(f"Request auth_config: {request.auth_config}")
    logger.info(f"Request parameters: {request.parameters}")
    logger.info(f"Previous results keys: {list(request.previous_results.keys()) if request.previous_results else 'None'}")
    logger.info(f"Previous results data: {request.previous_results}")
    
    # Log template variables for debugging
    if request.parameters:
        for key, value in request.parameters.items():
            if isinstance(value, str) and '{' in value and '}' in value:
                logger.info(f"🎯 Found template variable in {key}: {value}")
    
    # Process template variables in parameters if previous results exist
    processed_parameters = request.parameters.copy() if request.parameters else {}
    if request.previous_results:
        logger.info(f"🔄 Starting template substitution with previous results from: {type(request.previous_results)}")
        processed_parameters = substitute_template_variables(
            processed_parameters, 
            request.previous_results
        )
        logger.info(f"✅ Parameters after template substitution: {processed_parameters}")
    else:
        logger.warning(f"⚠️ No previous results available for template substitution")
    
    try:
        # Get authentication context
        auth_context = AuthContextManager()
        
        # Get the connector
        if not connector_registry.is_registered(request.connector_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector '{request.connector_name}' not found"
            )
        
        connector = connector_registry.create_connector(request.connector_name)
        
        # Get auth tokens if needed
        auth_tokens = {}
        
        # Always try to get stored tokens from auth context manager first
        from app.services.auth_context_manager import get_auth_context_manager
        auth_context_manager = await get_auth_context_manager()
        try:
            stored_tokens = await auth_context_manager.get_connector_auth_tokens(
                user_id, request.connector_name
            )
            auth_tokens.update(stored_tokens)
            logger.info(f"Retrieved stored auth tokens for '{request.connector_name}': {list(stored_tokens.keys()) if stored_tokens else 'No stored tokens'}")
        except Exception as e:
            logger.warning(f"Could not get stored auth tokens for '{request.connector_name}': {e}")
        
        # Then overlay any auth_config passed directly from frontend (takes precedence)
        if request.auth_config:
            logger.info(f"Overlaying direct auth config: {list(request.auth_config.keys())}")
            auth_tokens.update(request.auth_config)
        
        logger.info(f"Using auth tokens: {list(auth_tokens.keys()) if auth_tokens else 'No auth tokens'}")
        
        # Create execution context
        context = ConnectorExecutionContext(
            user_id=user_id,
            workflow_id=request.workflow_id,
            execution_id=execution_id,
            auth_tokens=auth_tokens,
            previous_results=request.previous_results,  # Pass previous results for sequential execution
            metadata={
                "node_id": request.node_id,
                "execution_type": "individual_sequential",
                "timestamp": datetime.utcnow().isoformat(),
                "has_previous_results": bool(request.previous_results)
            }
        )
        
        # Execute the connector
        logger.info(f"Executing connector {request.connector_name} with parameters: {processed_parameters}")
        result: ConnectorResult = await connector.execute(processed_parameters, context)
        
        # Calculate execution time
        execution_time = int((time.time() - start_time) * 1000)
        
        # Format output for better readability
        formatted_output = None
        try:
            formatted_output = format_connector_output(
                result.data, request.connector_name
            )
        except Exception as e:
            logger.warning(f"Could not format output: {e}")
        
        # Store execution result in database for history
        try:
            supabase = get_supabase_client()
            execution_data = {
                "id": execution_id,
                "user_id": user_id,
                "connector_name": request.connector_name,
                "parameters": request.parameters,
                "output_data": result.data,
                "success": result.success,
                "error_message": result.error,
                "execution_time_ms": execution_time,
                "workflow_id": request.workflow_id,
                "node_id": request.node_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Use upsert to handle potential ID conflicts
            supabase.table("node_executions").upsert(execution_data).execute()
            logger.info(f"Stored node execution result: {execution_id}")
            
        except Exception as e:
            logger.warning(f"Could not store execution result: {e}")
        
        # Return response
        return NodeExecutionResponse(
            success=result.success,
            execution_id=execution_id,
            connector_name=request.connector_name,
            output_data=result.data if isinstance(result.data, dict) else {} if result.data is None else {"result": result.data},
            formatted_output=formatted_output,
            execution_time_ms=execution_time,
            timestamp=datetime.utcnow(),
            error_message=result.error,
            metadata={
                "node_id": request.node_id,
                "workflow_id": request.workflow_id,
                "record_count": len(result.data) if isinstance(result.data, (list, dict)) else None
            }
        )
        
    except HTTPException:
        raise
    except ConnectorException as e:
        logger.error(f"Connector error during node execution: {e}")
        return NodeExecutionResponse(
            success=False,
            execution_id=execution_id,
            connector_name=request.connector_name,
            output_data={},
            execution_time_ms=int((time.time() - start_time) * 1000),
            timestamp=datetime.utcnow(),
            error_message=str(e),
            metadata={"error_type": "connector_error"}
        )
    except AuthenticationException as e:
        logger.error(f"Authentication error during node execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication required for {request.connector_name}: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during node execution: {e}")
        return NodeExecutionResponse(
            success=False,
            execution_id=execution_id,
            connector_name=request.connector_name,
            output_data={},
            execution_time_ms=int((time.time() - start_time) * 1000),
            timestamp=datetime.utcnow(),
            error_message=f"Unexpected error: {str(e)}",
            metadata={"error_type": "system_error"}
        )


@router.get("/preview/{connector_name}", response_model=NodeDataPreviewResponse)
async def preview_node_data(
    connector_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a preview of the data structure that a connector would return.
    
    This provides users with information about what data structure
    to expect from a connector before executing it.
    """
    try:
        logger.info(f"Getting data preview for connector {connector_name}")
        
        # Check if connector exists
        if not connector_registry.is_registered(connector_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector '{connector_name}' not found"
            )
        
        connector = connector_registry.create_connector(connector_name)
        
        # Get connector schema and example data
        schema = getattr(connector, 'schema', {})
        example_params = getattr(connector, 'get_example_params', lambda: {})()
        
        # Try to get sample output structure
        sample_data = {}
        data_types = {}
        
        # Look for output schema or example output
        if hasattr(connector, 'get_output_schema'):
            output_schema = connector.get_output_schema()
            sample_data = _generate_sample_from_schema(output_schema)
            data_types = _extract_types_from_schema(output_schema)
        elif hasattr(connector, 'get_example_output'):
            sample_data = connector.get_example_output()
            data_types = _infer_data_types(sample_data)
        else:
            # Generic sample based on connector category
            sample_data = _generate_generic_sample(connector_name)
            data_types = _infer_data_types(sample_data)
        
        # Get data structure info
        data_structure = {
            "input_schema": schema,
            "output_properties": list(sample_data.keys()) if isinstance(sample_data, dict) else [],
            "connector_category": getattr(connector, 'category', 'unknown')
        }
        
        return NodeDataPreviewResponse(
            connector_name=connector_name,
            data_structure=data_structure,
            sample_data=sample_data,
            data_types=data_types,
            record_count=len(sample_data) if isinstance(sample_data, (list, dict)) else None,
            preview_truncated=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node data preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data preview: {str(e)}"
        )


@router.get("/executions/{execution_id}")
async def get_node_execution_result(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the result of a previous node execution."""
    try:
        user_id = current_user["user_id"]
        supabase = get_supabase_client()
        
        # Get execution result
        result = supabase.table("node_executions").select("*").eq("id", execution_id).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution result not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get execution result"
        )


def _generate_sample_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate sample data from JSON schema."""
    sample = {}
    properties = schema.get('properties', {})
    
    for key, prop in properties.items():
        prop_type = prop.get('type', 'string')
        if prop_type == 'string':
            sample[key] = prop.get('example', f'sample_{key}')
        elif prop_type == 'number':
            sample[key] = prop.get('example', 42)
        elif prop_type == 'boolean':
            sample[key] = prop.get('example', True)
        elif prop_type == 'array':
            sample[key] = prop.get('example', [f'sample_{key}_item'])
        elif prop_type == 'object':
            sample[key] = prop.get('example', {f'{key}_property': 'value'})
    
    return sample


def _extract_types_from_schema(schema: Dict[str, Any]) -> Dict[str, str]:
    """Extract data types from JSON schema."""
    types = {}
    properties = schema.get('properties', {})
    
    for key, prop in properties.items():
        types[key] = prop.get('type', 'unknown')
    
    return types


def _infer_data_types(data: Any) -> Dict[str, str]:
    """Infer data types from sample data."""
    if not isinstance(data, dict):
        return {}
    
    types = {}
    for key, value in data.items():
        if isinstance(value, str):
            types[key] = 'string'
        elif isinstance(value, (int, float)):
            types[key] = 'number'
        elif isinstance(value, bool):
            types[key] = 'boolean'
        elif isinstance(value, list):
            types[key] = 'array'
        elif isinstance(value, dict):
            types[key] = 'object'
        else:
            types[key] = 'unknown'
    
    return types


def _generate_generic_sample(connector_name: str) -> Dict[str, Any]:
    """Generate generic sample data based on connector name."""
    base_sample = {
        "success": True,
        "timestamp": "2025-09-02T10:30:00Z",
        "data": f"Sample output from {connector_name}"
    }
    
    # Customize based on connector type
    if 'gmail' in connector_name.lower():
        base_sample.update({
            "message_id": "sample_message_id",
            "subject": "Sample Email Subject",
            "from": "sender@example.com",
            "to": "recipient@example.com"
        })
    elif 'sheets' in connector_name.lower():
        base_sample.update({
            "spreadsheet_id": "sample_spreadsheet_id",
            "range": "A1:D10",
            "values": [["Header1", "Header2"], ["Value1", "Value2"]]
        })
    elif 'notion' in connector_name.lower():
        base_sample.update({
            "page_id": "sample_page_id",
            "title": "Sample Notion Page",
            "properties": {"Status": "Active"}
        })
    
    return base_sample
