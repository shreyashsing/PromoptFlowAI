"""
LangGraph-based workflow orchestration system.

This module implements the workflow execution engine using LangGraph for
orchestrating complex automation workflows with state management, error handling,
and trigger support.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, TypedDict
from uuid import uuid4

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, Trigger
from app.models.execution import (
    ExecutionResult, 
    ExecutionStatus, 
    NodeExecutionResult, 
    ErrorHandlingResult
)
from app.models.connector import ConnectorExecutionContext
from app.connectors.registry import connector_registry
from app.core.exceptions import WorkflowException, ConnectorException
from app.core.database import get_supabase_client
from app.core.error_utils import handle_database_errors, log_function_performance, ErrorBoundary
from app.services.auth_tokens import get_auth_token_service
from app.services.workflow_transformer import WorkflowTransformer
from app.services.parallel_workflow_executor import ParallelWorkflowExecutor
from app.models.base import AuthType


logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State structure for LangGraph workflow execution."""
    workflow_id: str
    user_id: str
    execution_id: str
    current_node: Optional[str]
    node_results: Dict[str, Any]
    errors: List[str]
    status: ExecutionStatus
    metadata: Dict[str, Any]


class WorkflowOrchestrator:
    """
    Main orchestrator for workflow execution using LangGraph.
    
    Handles workflow graph construction, execution, state management,
    and error handling.
    """
    
    def __init__(self):
        self.connector_registry = connector_registry
        self.active_executions: Dict[str, ExecutionResult] = {}
        self.triggers: Dict[str, Callable] = {}
        self.checkpointer = MemorySaver()
        self.transformer = WorkflowTransformer()
        self.parallel_executor = ParallelWorkflowExecutor()
        
    @handle_database_errors("validate_workflow")
    @log_function_performance("validate_workflow")
    async def validate_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a workflow definition.
        
        Args:
            workflow: The workflow definition to validate
            
        Returns:
            Dict with validation results
        """
        # Simple validation logic
        errors = []
        
        # Check required fields
        if not workflow.get("name"):
            errors.append("Workflow name is required")
            
        if not workflow.get("steps") and not workflow.get("nodes"):
            errors.append("Workflow must have steps or nodes array")
        
        # Check steps if present
        steps = workflow.get("steps", [])
        if steps:
            for i, step in enumerate(steps):
                if not step.get("id"):
                    errors.append(f"Step {i+1} missing required 'id' field")
                if not step.get("connector_id"):
                    errors.append(f"Step {i+1} missing required 'connector_id' field")
        
        # Check nodes if present
        nodes = workflow.get("nodes", [])
        if nodes:
            for i, node in enumerate(nodes):
                if not node.get("id"):
                    errors.append(f"Node {i+1} missing required 'id' field")
                    
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
        
    @handle_database_errors("execute_workflow")
    @log_function_performance("execute_workflow")
    async def execute_workflow(self, workflow: WorkflowPlan) -> ExecutionResult:
        """
        Execute a workflow using LangGraph orchestration.
        
        Args:
            workflow: The workflow plan to execute
            
        Returns:
            ExecutionResult with execution details and results
        """
        execution_id = str(uuid4())
        execution_result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            status=ExecutionStatus.PENDING,
            started_at=datetime.utcnow()
        )
        
        self.active_executions[execution_id] = execution_result
        
        try:
            # Check if workflow would benefit from parallel execution
            if self.parallel_executor.should_use_parallel_execution(workflow):
                logger.info(f"Using parallel execution for workflow {workflow.id}")
                return await self.parallel_executor.execute_workflow(workflow)
            
            # Use LangGraph for simple workflows
            logger.info(f"Using LangGraph execution for workflow {workflow.id}")
            
            # Transform workflow to handle any remaining parallel scenarios
            transformed_workflow = self.transformer.transform_workflow(workflow)
            
            # Build LangGraph workflow
            graph = await self._build_langgraph_workflow(transformed_workflow)
            
            # Initialize workflow state
            initial_state = WorkflowState(
                workflow_id=workflow.id,
                user_id=workflow.user_id,
                execution_id=execution_id,
                current_node=None,
                node_results={},
                errors=[],
                status=ExecutionStatus.RUNNING,
                metadata={}
            )
            
            execution_result.status = ExecutionStatus.RUNNING
            
            # Execute the workflow graph
            config = {"configurable": {"thread_id": execution_id}}
            final_state = await graph.ainvoke(initial_state, config=config)
            
            # Update execution result based on final state
            execution_result.status = final_state["status"]
            execution_result.completed_at = datetime.utcnow()
            execution_result.total_duration_ms = int(
                (execution_result.completed_at - execution_result.started_at).total_seconds() * 1000
            )
            
            # Convert node results to NodeExecutionResult objects
            for node_id, result_data in final_state["node_results"].items():
                node_result = NodeExecutionResult(
                    node_id=node_id,
                    connector_name=result_data.get("connector_name", "unknown"),
                    status=ExecutionStatus.COMPLETED if result_data.get("success") else ExecutionStatus.FAILED,
                    result=result_data.get("data"),
                    error=result_data.get("error"),
                    started_at=result_data.get("started_at", execution_result.started_at),
                    completed_at=result_data.get("completed_at", execution_result.completed_at),
                    duration_ms=result_data.get("duration_ms", 0)
                )
                execution_result.node_results.append(node_result)
            
            if final_state["errors"]:
                execution_result.error = "; ".join(final_state["errors"])
            
            # Store execution result in database
            await self._store_execution_result(execution_result)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            execution_result.status = ExecutionStatus.FAILED
            execution_result.error = str(e)
            execution_result.completed_at = datetime.utcnow()
            
            await self._store_execution_result(execution_result)
            return execution_result
        
        finally:
            # Clean up active execution
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _build_langgraph_workflow(self, workflow: WorkflowPlan) -> StateGraph:
        """
        Build a LangGraph StateGraph from a WorkflowPlan.
        
        Args:
            workflow: The workflow plan to convert
            
        Returns:
            Compiled StateGraph ready for execution
        """
        # Create the state graph
        graph = StateGraph(WorkflowState)
        
        # Add start node
        graph.add_node("start", self._start_node)
        graph.set_entry_point("start")
        
        # Add nodes for each workflow node
        for node in workflow.nodes:
            graph.add_node(node.id, self._create_node_executor(node))
        
        # Add end node
        graph.add_node("end", self._end_node)
        graph.set_finish_point("end")
        
        # Add edges based on workflow structure
        await self._add_workflow_edges(graph, workflow)
        
        # Compile the graph with checkpointer for state persistence
        return graph.compile(checkpointer=self.checkpointer)
    
    def _create_node_executor(self, node: WorkflowNode) -> Callable:
        """
        Create an executor function for a workflow node.
        
        Args:
            node: The workflow node to create an executor for
            
        Returns:
            Async function that executes the node
        """
        async def execute_node(state: WorkflowState) -> WorkflowState:
            """Execute a single workflow node."""
            logger.info(f"Executing node {node.id} with connector {node.connector_name}")
            
            start_time = datetime.utcnow()
            state["current_node"] = node.id
            
            try:
                # Get the connector
                connector = self.connector_registry.create_connector(node.connector_name)
                
                # Load authentication tokens for this connector
                auth_tokens = await self._load_auth_tokens_for_connector(
                    state["user_id"], 
                    node.connector_name
                )
                
                # Debug: Log auth token status
                if auth_tokens:
                    token_keys = list(auth_tokens.keys())
                    logger.info(f"Loaded auth tokens for {node.connector_name}: {token_keys}")
                else:
                    logger.warning(f"No auth tokens loaded for {node.connector_name}")
                
                # Prepare execution context
                context = ConnectorExecutionContext(
                    user_id=state["user_id"],
                    workflow_id=state["workflow_id"],
                    node_id=node.id,
                    auth_tokens=auth_tokens,
                    previous_results=state["node_results"]
                )
                
                # Resolve parameters with previous results
                resolved_params = await self._resolve_node_parameters(
                    node.parameters, 
                    state["node_results"]
                )
                
                # Execute the connector
                result = await connector.execute_with_retry(resolved_params, context)
                
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Store node result
                state["node_results"][node.id] = {
                    "connector_name": node.connector_name,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "started_at": start_time,
                    "completed_at": end_time,
                    "duration_ms": duration_ms
                }
                
                if not result.success:
                    error_msg = f"Node {node.id} failed: {result.error}"
                    state["errors"].append(error_msg)
                    logger.error(error_msg)
                
                logger.info(f"Node {node.id} completed in {duration_ms}ms")
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                error_msg = f"Node {node.id} execution failed: {str(e)}"
                state["errors"].append(error_msg)
                logger.error(error_msg)
                
                # Store failed result
                state["node_results"][node.id] = {
                    "connector_name": node.connector_name,
                    "success": False,
                    "data": None,
                    "error": str(e),
                    "started_at": start_time,
                    "completed_at": end_time,
                    "duration_ms": duration_ms
                }
            
            return state
        
        return execute_node
    
    async def _resolve_node_parameters(
        self, 
        parameters: Dict[str, Any], 
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve node parameters by substituting references to previous results.
        
        Args:
            parameters: Raw parameters that may contain references
            previous_results: Results from previously executed nodes
            
        Returns:
            Resolved parameters with references substituted
        """
        import re
        
        resolved = {}
        
        # Create a mapping from connector names to node IDs for easier lookup
        connector_to_node_map = {}
        for node_id, result_data in previous_results.items():
            connector_name = result_data.get("connector_name")
            if connector_name:
                connector_to_node_map[connector_name] = node_id
        
        logger.info(f"Available previous results: {list(previous_results.keys())}")
        logger.info(f"Connector to node mapping: {connector_to_node_map}")
        
        for key, value in parameters.items():
            if isinstance(value, str):
                resolved_value = value
                
                # Process patterns sequentially to avoid conflicts
                # 1. First process double braces {{...}}
                double_brace_pattern = r'\{\{([^}]+)\}\}'
                double_matches = re.findall(double_brace_pattern, value)
                
                for reference in double_matches:
                    original_pattern = f"{{{{{reference}}}}}"  # {{reference}}
                    logger.info(f"Processing reference: {reference} (pattern: {original_pattern})")
                    
                    replacement_value = self._resolve_reference(reference, previous_results, connector_to_node_map)
                    
                    if replacement_value is not None:
                        resolved_value = resolved_value.replace(original_pattern, str(replacement_value))
                        logger.info(f"Replaced {original_pattern} with: {replacement_value}")
                
                # 2. Then process dollar braces ${...}
                dollar_brace_pattern = r'\$\{([^}]+)\}'
                dollar_matches = re.findall(dollar_brace_pattern, resolved_value)
                
                for reference in dollar_matches:
                    original_pattern = f"${{{reference}}}"
                    logger.info(f"Processing reference: {reference} (pattern: {original_pattern})")
                    
                    replacement_value = self._resolve_reference(reference, previous_results, connector_to_node_map)
                    
                    if replacement_value is not None:
                        resolved_value = resolved_value.replace(original_pattern, str(replacement_value))
                        logger.info(f"Replaced {original_pattern} with: {replacement_value}")
                
                # 3. Finally process single braces {...} (but only if no double braces were processed)
                if not double_matches:
                    single_brace_pattern = r'\{([^}]+)\}'
                    single_matches = re.findall(single_brace_pattern, resolved_value)
                    
                    for reference in single_matches:
                        original_pattern = f"{{{reference}}}"
                        logger.info(f"Processing reference: {reference} (pattern: {original_pattern})")
                        
                        replacement_value = self._resolve_reference(reference, previous_results, connector_to_node_map)
                        
                        if replacement_value is not None:
                            resolved_value = resolved_value.replace(original_pattern, str(replacement_value))
                            logger.info(f"Replaced {original_pattern} with: {replacement_value}")
                
                resolved[key] = resolved_value
                if resolved_value != value:
                    logger.info(f"Parameter {key}: '{value}' -> '{resolved_value}'")
            else:
                resolved[key] = value
        
        return resolved
    
    def _resolve_reference(
        self, 
        reference: str, 
        previous_results: Dict[str, Any], 
        connector_to_node_map: Dict[str, str]
    ) -> Any:
        """
        Resolve a single parameter reference to its actual value.
        
        Args:
            reference: The reference string (e.g., "text_summarizer.result")
            previous_results: Results from previously executed nodes
            connector_to_node_map: Mapping from connector names to node IDs
            
        Returns:
            The resolved value or None if not found
        """
        if "." in reference:
            # Handle node_id.field_path or connector_name.field_path
            node_or_connector, field_path = reference.split(".", 1)
            
            # Try node ID first, then connector name
            target_node_id = None
            if node_or_connector in previous_results:
                target_node_id = node_or_connector
            elif node_or_connector in connector_to_node_map:
                target_node_id = connector_to_node_map[node_or_connector]
            
            if target_node_id:
                node_result = previous_results[target_node_id]
                logger.info(f"Found node result for {node_or_connector} -> {target_node_id}")
                logger.info(f"Node result data: {node_result.get('data')}")
                
                # Navigate the field path
                replacement_value = self._get_nested_value(node_result.get("data"), field_path)
                logger.info(f"Extracted value for {field_path}: {replacement_value}")
                return replacement_value
            else:
                logger.warning(f"Referenced node/connector {node_or_connector} not found in previous results")
                return None
        else:
            # Simple node reference
            target_node_id = None
            if reference in previous_results:
                target_node_id = reference
            elif reference in connector_to_node_map:
                target_node_id = connector_to_node_map[reference]
            
            if target_node_id:
                replacement_value = previous_results[target_node_id].get("data")
                return replacement_value
            else:
                logger.warning(f"Referenced node/connector {reference} not found in previous results")
                return None
    
    def _get_nested_value(self, data: Any, field_path: str) -> Any:
        """
        Get a nested value from data using dot notation with intelligent field mapping.
        
        Args:
            data: The data structure to navigate
            field_path: Dot-separated path to the desired field
            
        Returns:
            The value at the specified path, or None if not found
        """
        if data is None:
            return None
        
        # Define connector-specific field mappings for common patterns
        FIELD_MAPPINGS = {
            'result': [
                'result', 'data', 'output', 'response', 'summary', 'content', 
                'text', 'message', 'answer', 'value'
            ]
        }
        
        current = data
        fields = field_path.split(".")
        
        for i, field in enumerate(fields):
            if isinstance(current, dict):
                # First try the exact field name
                if field in current:
                    current = current[field]
                # If field is 'result' and not found, try mapped alternatives with intelligent combining
                elif field == 'result' and field not in current:
                    found_value = None
                    
                    # Special handling for Perplexity data with citations
                    if 'response' in current and 'citations' in current and current.get('citations'):
                        # Combine content and citations for rich output
                        main_content = current['response']
                        citations = current['citations']
                        
                        # Format citations as clickable links
                        if isinstance(citations, list) and citations:
                            citation_text = "\n\n📚 **Sources:**\n"
                            for idx, citation in enumerate(citations, 1):
                                if isinstance(citation, str):
                                    citation_text += f"{idx}. {citation}\n"
                                elif isinstance(citation, dict) and 'url' in citation:
                                    title = citation.get('title', citation['url'])
                                    citation_text += f"{idx}. [{title}]({citation['url']})\n"
                            
                            combined_result = f"{main_content}{citation_text}"
                            logger.info(f"Combined Perplexity content with {len(citations)} citations")
                            return combined_result
                    
                    # Fallback to standard field mapping
                    for alternative in FIELD_MAPPINGS['result']:
                        if alternative in current:
                            current = current[alternative]
                            logger.info(f"Mapped field 'result' to '{alternative}' in data: {current}")
                            found_value = current
                            break
                            
                    if found_value is None:
                        logger.warning(f"Field '{field}' not found in data. Available fields: {list(current.keys())}")
                        return None
                else:
                    logger.warning(f"Field '{field}' not found in data. Available fields: {list(current.keys())}")
                    return None
            elif isinstance(current, list) and field.isdigit():
                index = int(field)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    logger.warning(f"Index {index} out of range for list of length {len(current)}")
                    return None
            else:
                logger.warning(f"Cannot navigate field '{field}' in data type {type(current)}")
                return None
        
        logger.info(f"Successfully extracted value from path '{field_path}': {current}")
        return current
    
    async def _load_auth_tokens_for_connector(self, user_id: str, connector_name: str) -> Dict[str, Any]:
        """
        Load authentication tokens for a specific connector and user.
        Automatically refreshes access tokens if needed.
        
        Args:
            user_id: The user ID
            connector_name: The connector name to load tokens for
            
        Returns:
            Dictionary containing authentication tokens for the connector
        """
        try:
            supabase = get_supabase_client()
            auth_service = await get_auth_token_service(supabase)
            
            # Try to get OAuth2 token first (most common for connectors like Gmail)
            oauth_token = await auth_service.get_token(user_id, connector_name, AuthType.OAUTH2)
            if oauth_token:
                token_data = oauth_token["token_data"]
                
                # Check if we have access_token, if not try to refresh using refresh_token
                if "access_token" not in token_data and "refresh_token" in token_data:
                    logger.info(f"Access token missing for {connector_name}, attempting to refresh using refresh token")
                    
                    refreshed_tokens = await self._refresh_oauth_token(
                        connector_name, 
                        token_data["refresh_token"]
                    )
                    
                    if refreshed_tokens:
                        # Update stored tokens with refreshed data
                        combined_token_data = {**token_data, **refreshed_tokens}
                        
                        # Store updated tokens
                        from app.models.database import CreateAuthTokenRequest
                        update_request = CreateAuthTokenRequest(
                            connector_name=connector_name,
                            token_type=AuthType.OAUTH2,
                            token_data=combined_token_data
                        )
                        await auth_service.store_token(user_id, update_request)
                        
                        logger.info(f"Successfully refreshed and stored access token for {connector_name}")
                        return self._normalize_token_data(combined_token_data)
                    else:
                        logger.error(f"Failed to refresh access token for {connector_name}")
                        return {}
                
                # Normalize token data types (ensure expires_in is string)
                normalized_token_data = self._normalize_token_data(token_data)
                return normalized_token_data
            
            # Try API key if OAuth2 not found
            api_key_token = await auth_service.get_token(user_id, connector_name, AuthType.API_KEY)
            if api_key_token:
                return self._normalize_token_data(api_key_token["token_data"])
            
            # Return empty dict if no tokens found
            logger.warning(f"No authentication tokens found for user {user_id}, connector {connector_name}")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to load auth tokens for {connector_name}: {str(e)}")
            return {}
    
    def _normalize_token_data(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize token data types to match expected Pydantic model requirements.
        
        Args:
            token_data: Raw token data from database
            
        Returns:
            Normalized token data with correct types
        """
        normalized = token_data.copy()
        
        # Convert expires_in to string if it's an integer
        if "expires_in" in normalized and isinstance(normalized["expires_in"], int):
            logger.debug(f"Converting expires_in from int {normalized['expires_in']} to string")
            normalized["expires_in"] = str(normalized["expires_in"])
        
        # Ensure token_type is string
        if "token_type" in normalized and normalized["token_type"] is not None:
            normalized["token_type"] = str(normalized["token_type"])
        
        # Ensure other common fields are strings
        for field in ["access_token", "refresh_token", "scope"]:
            if field in normalized and normalized[field] is not None:
                normalized[field] = str(normalized[field])
        
        return normalized
    
    async def _refresh_oauth_token(self, connector_name: str, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh OAuth access token using refresh token.
        
        Args:
            connector_name: The connector name (e.g., 'gmail_connector')
            refresh_token: The refresh token to use
            
        Returns:
            Dictionary with new access token and related data, or None if refresh failed
        """
        try:
            if connector_name == "gmail_connector":
                from app.core.config import settings
                import httpx
                
                if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
                    logger.error("Gmail OAuth credentials not configured")
                    return None
                
                # Make token refresh request to Google
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": settings.GMAIL_CLIENT_ID,
                            "client_secret": settings.GMAIL_CLIENT_SECRET,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token"
                        }
                    )
                    
                    if response.status_code == 200:
                        tokens = response.json()
                        return {
                            "access_token": tokens["access_token"],
                            "token_type": tokens.get("token_type", "Bearer"),
                            "expires_in": str(tokens.get("expires_in")) if tokens.get("expires_in") is not None else None,
                            "scope": tokens.get("scope")
                        }
                    else:
                        logger.error(f"Token refresh failed with status {response.status_code}: {response.text}")
                        return None
            
            # Add support for other OAuth connectors here as needed
            logger.warning(f"Token refresh not implemented for connector: {connector_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error refreshing OAuth token for {connector_name}: {str(e)}")
            return None
    
    async def _add_workflow_edges(self, graph: StateGraph, workflow: WorkflowPlan):
        """
        Add edges to the LangGraph based on workflow structure.
        
        Args:
            graph: The StateGraph to add edges to
            workflow: The workflow plan containing edge definitions
        """
        # Keep track of added edges to avoid duplicates
        added_edges = set()
        
        # Connect start to first nodes (nodes with no dependencies)
        first_nodes = [node for node in workflow.nodes if not node.dependencies]
        if first_nodes:
            for node in first_nodes:
                edge_key = ("start", node.id)
                if edge_key not in added_edges:
                    graph.add_edge("start", node.id)
                    added_edges.add(edge_key)
        else:
            # If no first nodes, connect start to end
            graph.add_edge("start", "end")
            added_edges.add(("start", "end"))
        
        # Get all valid node IDs (including start and end)
        valid_node_ids = {"start", "end"} | {node.id for node in workflow.nodes}
        
        # Add edges based on workflow edges (explicit edges take precedence)
        for edge in workflow.edges:
            # Validate that both source and target nodes exist
            if edge.source not in valid_node_ids:
                logger.warning(f"Edge source node '{edge.source}' not found in workflow nodes")
                continue
            if edge.target not in valid_node_ids:
                logger.warning(f"Edge target node '{edge.target}' not found in workflow nodes")
                continue
                
            edge_key = (edge.source, edge.target)
            if edge_key not in added_edges:
                if edge.condition:
                    # Conditional edge
                    graph.add_conditional_edges(
                        edge.source,
                        self._create_condition_evaluator(edge.condition),
                        {
                            True: edge.target,
                            False: "end"  # Skip to end if condition fails
                        }
                    )
                else:
                    # Regular edge
                    graph.add_edge(edge.source, edge.target)
                added_edges.add(edge_key)
        
        # Add edges based on node dependencies (only if not already added by explicit edges)
        for node in workflow.nodes:
            for dependency in node.dependencies:
                # Validate that dependency node exists
                if dependency not in valid_node_ids:
                    logger.warning(f"Dependency node '{dependency}' not found for node '{node.id}'")
                    continue
                    
                edge_key = (dependency, node.id)
                if edge_key not in added_edges:
                    graph.add_edge(dependency, node.id)
                    added_edges.add(edge_key)
        
        # Connect nodes with no outgoing edges to end
        nodes_with_outgoing = set()
        for edge in workflow.edges:
            nodes_with_outgoing.add(edge.source)
        
        # Also check dependency-based edges
        for node in workflow.nodes:
            if node.dependencies:
                nodes_with_outgoing.update(node.dependencies)
        
        for node in workflow.nodes:
            if node.id not in nodes_with_outgoing:
                edge_key = (node.id, "end")
                if edge_key not in added_edges:
                    graph.add_edge(node.id, "end")
                    added_edges.add(edge_key)
    

    
    def _create_condition_evaluator(self, condition: str) -> Callable:
        """
        Create a condition evaluator function for conditional edges.
        
        Args:
            condition: The condition string to evaluate
            
        Returns:
            Function that evaluates the condition against workflow state
        """
        def evaluate_condition(state: WorkflowState) -> bool:
            """Evaluate a condition against the current workflow state."""
            try:
                # Simple condition evaluation - can be extended for complex logic
                # Format: "node_id.field == value" or "node_id.success == true"
                if "==" in condition:
                    left, right = condition.split("==", 1)
                    left = left.strip()
                    right = right.strip().strip('"\'')
                    
                    if "." in left:
                        node_id, field_path = left.split(".", 1)
                        if node_id in state["node_results"]:
                            node_result = state["node_results"][node_id]
                            actual_value = self._get_nested_value(node_result.get("data"), field_path)
                            
                            # Type conversion for comparison
                            if right.lower() == "true":
                                return bool(actual_value)
                            elif right.lower() == "false":
                                return not bool(actual_value)
                            elif right.isdigit():
                                return str(actual_value) == right
                            else:
                                return str(actual_value) == right
                
                return False
            except Exception as e:
                logger.error(f"Condition evaluation failed: {str(e)}")
                return False
        
        return evaluate_condition
    
    async def _start_node(self, state: WorkflowState) -> WorkflowState:
        """
        Start node for workflow execution.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        logger.info(f"Starting workflow execution {state['execution_id']}")
        state["status"] = ExecutionStatus.RUNNING
        return state
    
    async def _end_node(self, state: WorkflowState) -> WorkflowState:
        """
        End node for workflow execution.
        
        Args:
            state: Current workflow state
            
        Returns:
            Final workflow state
        """
        logger.info(f"Completing workflow execution {state['execution_id']}")
        
        # Determine final status based on errors
        if state["errors"]:
            state["status"] = ExecutionStatus.FAILED
        else:
            state["status"] = ExecutionStatus.COMPLETED
        
        return state
    
    async def _store_execution_result(self, execution_result: ExecutionResult):
        """
        Store execution result in the database.
        
        Args:
            execution_result: The execution result to store
        """
        try:
            supabase = get_supabase_client()
            
            # Prepare execution log from node results
            execution_log = []
            for node_result in execution_result.node_results:
                execution_log.append({
                    "node_id": node_result.node_id,
                    "connector_name": node_result.connector_name,
                    "status": node_result.status.value,
                    "started_at": node_result.started_at.isoformat(),
                    "completed_at": node_result.completed_at.isoformat() if node_result.completed_at else None,
                    "duration_ms": node_result.duration_ms,
                    "error": node_result.error
                })
            
            # Prepare result data
            result_data = {
                "node_results": {
                    node_result.node_id: {
                        "data": node_result.result,
                        "status": node_result.status.value
                    }
                    for node_result in execution_result.node_results
                }
            }
            
            # Insert execution record
            execution_data = {
                "id": execution_result.execution_id,
                "workflow_id": execution_result.workflow_id,
                "user_id": execution_result.user_id,
                "status": execution_result.status.value,
                "trigger_type": "manual",  # TODO: Support other trigger types
                "execution_log": execution_log,
                "result": result_data,
                "error_message": execution_result.error,
                "started_at": execution_result.started_at.isoformat(),
                "completed_at": execution_result.completed_at.isoformat() if execution_result.completed_at else None,
                "duration_ms": execution_result.total_duration_ms
            }
            
            response = supabase.table("workflow_executions").insert(execution_data).execute()
            
            if response.data:
                logger.info(f"Stored execution result for {execution_result.execution_id}")
            else:
                logger.error(f"Failed to store execution result: {response}")
                
        except Exception as e:
            logger.error(f"Error storing execution result: {str(e)}")
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionResult]:
        """
        Get the current status of a workflow execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            ExecutionResult if found, None otherwise
        """
        # Check active executions first
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]
        
        # Check database for completed executions
        try:
            supabase = get_supabase_client()
            response = supabase.table("workflow_executions").select("*").eq("id", execution_id).execute()
            
            if response.data:
                execution_data = response.data[0]
                
                # Convert database record back to ExecutionResult
                execution_result = ExecutionResult(
                    execution_id=execution_data["id"],
                    workflow_id=execution_data["workflow_id"],
                    user_id=execution_data["user_id"],
                    status=ExecutionStatus(execution_data["status"]),
                    started_at=datetime.fromisoformat(execution_data["started_at"]),
                    completed_at=datetime.fromisoformat(execution_data["completed_at"]) if execution_data["completed_at"] else None,
                    total_duration_ms=execution_data["duration_ms"],
                    error=execution_data["error_message"]
                )
                
                # Reconstruct node results from execution log or result data
                if execution_data["execution_log"]:
                    # Original format (LangGraph execution)
                    for log_entry in execution_data["execution_log"]:
                        node_result = NodeExecutionResult(
                            node_id=log_entry["node_id"],
                            connector_name=log_entry["connector_name"],
                            status=ExecutionStatus(log_entry["status"]),
                            result=execution_data["result"]["node_results"].get(log_entry["node_id"], {}).get("data"),
                            error=log_entry.get("error"),
                            started_at=datetime.fromisoformat(log_entry["started_at"]),
                            completed_at=datetime.fromisoformat(log_entry["completed_at"]) if log_entry["completed_at"] else None,
                            duration_ms=log_entry.get("duration_ms")
                        )
                        execution_result.node_results.append(node_result)
                elif execution_data["result"] and "node_results" in execution_data["result"]:
                    # Parallel execution format
                    for node_data in execution_data["result"]["node_results"]:
                        node_result = NodeExecutionResult(
                            node_id=node_data["node_id"],
                            connector_name=node_data["connector_name"],
                            status=ExecutionStatus(node_data["status"]),
                            result=node_data["result"],
                            error=node_data.get("error"),
                            started_at=datetime.fromisoformat(node_data["started_at"]),
                            completed_at=datetime.fromisoformat(node_data["completed_at"]) if node_data["completed_at"] else None,
                            duration_ms=node_data.get("duration_ms")
                        )
                        execution_result.node_results.append(node_result)
                
                return execution_result
                
        except Exception as e:
            logger.error(f"Error retrieving execution status: {str(e)}")
        
        return None
    
    async def list_workflow_executions(
        self, 
        workflow_id: str, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[ExecutionResult]:
        """
        List executions for a workflow.
        
        Args:
            workflow_id: The workflow ID
            user_id: The user ID for authorization
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of ExecutionResult objects
        """
        try:
            supabase = get_supabase_client()
            
            response = supabase.table("workflow_executions").select(
                "id, workflow_id, user_id, status, started_at, completed_at, duration_ms, error_message"
            ).eq("workflow_id", workflow_id).eq("user_id", user_id).order(
                "started_at", desc=True
            ).range(offset, offset + limit - 1).execute()
            
            executions = []
            if response.data:
                for exec_data in response.data:
                    execution = ExecutionResult(
                        execution_id=exec_data["id"],
                        workflow_id=exec_data["workflow_id"],
                        user_id=exec_data["user_id"],
                        status=ExecutionStatus(exec_data["status"]),
                        started_at=datetime.fromisoformat(exec_data["started_at"]),
                        completed_at=datetime.fromisoformat(exec_data["completed_at"]) if exec_data["completed_at"] else None,
                        total_duration_ms=exec_data["duration_ms"],
                        error=exec_data["error_message"]
                    )
                    executions.append(execution)
            
            return executions
            
        except Exception as e:
            logger.error(f"Error listing workflow executions: {str(e)}")
            return []
    
    async def get_workflow_execution_stats(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get execution statistics for a workflow.
        
        Args:
            workflow_id: The workflow ID
            user_id: The user ID for authorization
            
        Returns:
            Dictionary with execution statistics
        """
        try:
            supabase = get_supabase_client()
            
            # Get execution counts by status
            response = supabase.table("workflow_executions").select(
                "status"
            ).eq("workflow_id", workflow_id).eq("user_id", user_id).execute()
            
            stats = {
                "total_executions": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "pending": 0,
                "cancelled": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0
            }
            
            if response.data:
                stats["total_executions"] = len(response.data)
                
                for exec_data in response.data:
                    status = exec_data["status"]
                    stats[status] = stats.get(status, 0) + 1
                
                # Calculate success rate
                if stats["total_executions"] > 0:
                    stats["success_rate"] = stats["completed"] / stats["total_executions"] * 100
            
            # Get average duration for completed executions
            duration_response = supabase.table("workflow_executions").select(
                "duration_ms"
            ).eq("workflow_id", workflow_id).eq("user_id", user_id).eq(
                "status", "completed"
            ).not_.is_("duration_ms", "null").execute()
            
            if duration_response.data:
                durations = [execution["duration_ms"] for execution in duration_response.data]
                if durations:
                    stats["average_duration_ms"] = sum(durations) / len(durations)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting workflow execution stats: {str(e)}")
            return {
                "total_executions": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "pending": 0,
                "cancelled": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0
            }
    
    async def cancel_execution(self, execution_id: str, user_id: str) -> bool:
        """
        Cancel a running workflow execution.
        
        Args:
            execution_id: The execution ID to cancel
            user_id: The user ID for authorization
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            # Check if execution is in active executions
            if execution_id in self.active_executions:
                execution = self.active_executions[execution_id]
                
                # Verify user authorization
                if execution.user_id != user_id:
                    return False
                
                # Only cancel if still running
                if execution.status in [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]:
                    execution.status = ExecutionStatus.CANCELLED
                    execution.completed_at = datetime.utcnow()
                    execution.error = "Execution cancelled by user"
                    
                    # Store the cancelled execution
                    await self._store_execution_result(execution)
                    
                    # Remove from active executions
                    del self.active_executions[execution_id]
                    
                    logger.info(f"Cancelled execution {execution_id} for user {user_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling execution {execution_id}: {str(e)}")
            return False
    
    async def handle_node_error(self, node: WorkflowNode, error: Exception) -> ErrorHandlingResult:
        """
        Handle errors that occur during node execution.
        
        Args:
            node: The workflow node that failed
            error: The exception that occurred
            
        Returns:
            ErrorHandlingResult with retry and recovery instructions
        """
        logger.error(f"Node {node.id} failed with error: {str(error)}")
        
        # Determine error handling strategy based on error type
        if isinstance(error, ConnectorException):
            # Connector-specific error handling
            if "rate limit" in str(error).lower():
                return ErrorHandlingResult(
                    should_retry=True,
                    retry_delay_seconds=60,
                    max_retries=3,
                    user_notification="Rate limit exceeded. Retrying in 60 seconds."
                )
            elif "authentication" in str(error).lower():
                return ErrorHandlingResult(
                    should_retry=False,
                    user_notification="Authentication failed. Please check your credentials."
                )
            else:
                return ErrorHandlingResult(
                    should_retry=True,
                    retry_delay_seconds=5,
                    max_retries=2,
                    user_notification="Connector error occurred. Retrying..."
                )
        
        elif isinstance(error, WorkflowException):
            # Workflow-specific error handling
            return ErrorHandlingResult(
                should_retry=False,
                user_notification=f"Workflow error: {str(error)}"
            )
        
        else:
            # Generic error handling
            return ErrorHandlingResult(
                should_retry=True,
                retry_delay_seconds=10,
                max_retries=1,
                user_notification="An unexpected error occurred. Retrying once..."
            )