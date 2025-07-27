"""
Parallel Workflow Executor

Custom execution engine that handles true parallel execution of workflow nodes,
bypassing LangGraph's single-outgoing-edge limitation for parallel scenarios.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
from uuid import uuid4
from dataclasses import dataclass

from app.models.base import WorkflowPlan, WorkflowNode
from app.models.execution import ExecutionResult, ExecutionStatus, NodeExecutionResult
from app.models.connector import ConnectorExecutionContext
from app.connectors.registry import connector_registry
from app.core.exceptions import WorkflowException
from app.core.database import get_supabase_client
from app.core.error_utils import handle_database_errors, log_function_performance
from app.services.auth_tokens import get_auth_token_service
from app.models.base import AuthType

logger = logging.getLogger(__name__)


@dataclass
class ExecutionBatch:
    """Represents a batch of nodes that can be executed in parallel."""
    nodes: List[WorkflowNode]
    batch_id: str
    dependencies_satisfied: bool = False


class ParallelWorkflowExecutor:
    """
    Custom workflow executor that supports true parallel execution.
    
    This executor analyzes workflow dependencies and executes nodes in parallel
    batches, providing significant performance improvements over sequential execution.
    """
    
    def __init__(self):
        self.connector_registry = connector_registry
        
    @handle_database_errors("execute_workflow_parallel")
    @log_function_performance("execute_workflow_parallel")
    async def execute_workflow(self, workflow: WorkflowPlan) -> ExecutionResult:
        """
        Execute a workflow with true parallel execution support.
        
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
        
        try:
            logger.info(f"Starting parallel execution of workflow {workflow.id}")
            execution_result.status = ExecutionStatus.RUNNING
            
            # Analyze workflow and create execution batches
            execution_batches = self._create_execution_batches(workflow.nodes)
            logger.info(f"Created {len(execution_batches)} execution batches")
            
            # Execute batches in dependency order with parallel execution within each batch
            node_results = {}
            for batch_idx, batch in enumerate(execution_batches):
                logger.info(f"Executing batch {batch_idx + 1}/{len(execution_batches)} with {len(batch.nodes)} nodes")
                
                batch_results = await self._execute_batch_parallel(
                    batch, 
                    node_results, 
                    workflow.user_id, 
                    workflow.id, 
                    execution_id
                )
                
                # Update node results with batch results
                node_results.update(batch_results)
                
                # Check if any nodes in this batch failed
                failed_nodes = [node_id for node_id, result in batch_results.items() if not result.success]
                successful_nodes = [node_id for node_id, result in batch_results.items() if result.success]
                
                if failed_nodes:
                    logger.error(f"Batch {batch_idx + 1} failed with {len(failed_nodes)} failed nodes: {failed_nodes}")
                    # Continue execution but mark as failed
                    execution_result.status = ExecutionStatus.FAILED
                
                if successful_nodes:
                    logger.info(f"Batch {batch_idx + 1} completed with {len(successful_nodes)} successful nodes: {successful_nodes}")
                
                logger.info(f"Batch {batch_idx + 1} summary: {len(successful_nodes)} successful, {len(failed_nodes)} failed")
            
            # Convert node results to NodeExecutionResult objects
            for node_id, result_data in node_results.items():
                node_result = NodeExecutionResult(
                    node_id=node_id,
                    connector_name=result_data.connector_name,
                    status=ExecutionStatus.COMPLETED if result_data.success else ExecutionStatus.FAILED,
                    result=result_data.data,
                    error=result_data.error,
                    started_at=result_data.started_at,
                    completed_at=result_data.completed_at,
                    duration_ms=result_data.duration_ms
                )
                execution_result.node_results.append(node_result)
            
            # Set final status if not already failed
            if execution_result.status != ExecutionStatus.FAILED:
                execution_result.status = ExecutionStatus.COMPLETED
            
            execution_result.completed_at = datetime.utcnow()
            execution_result.total_duration_ms = int(
                (execution_result.completed_at - execution_result.started_at).total_seconds() * 1000
            )
            
            # Store execution result in database
            await self._store_execution_result(execution_result)
            
            logger.info(f"Parallel workflow execution completed in {execution_result.total_duration_ms}ms")
            return execution_result
            
        except Exception as e:
            logger.error(f"Parallel workflow execution failed: {str(e)}")
            execution_result.status = ExecutionStatus.FAILED
            execution_result.error = str(e)
            execution_result.completed_at = datetime.utcnow()
            
            await self._store_execution_result(execution_result)
            return execution_result
    
    def _create_execution_batches(self, nodes: List[WorkflowNode]) -> List[ExecutionBatch]:
        """
        Create execution batches based on node dependencies.
        
        Nodes in the same batch can be executed in parallel as they have no
        dependencies on each other within the batch.
        
        Args:
            nodes: List of workflow nodes
            
        Returns:
            List of execution batches in dependency order
        """
        # Build dependency graph
        node_deps = {node.id: set(node.dependencies) for node in nodes}
        node_map = {node.id: node for node in nodes}
        
        batches = []
        remaining_nodes = set(node.id for node in nodes)
        completed_nodes = set()
        
        batch_counter = 0
        while remaining_nodes:
            # Find nodes that can be executed (all dependencies satisfied)
            ready_nodes = []
            for node_id in remaining_nodes:
                if node_deps[node_id].issubset(completed_nodes):
                    ready_nodes.append(node_map[node_id])
            
            if not ready_nodes:
                # Circular dependency or other issue
                logger.error(f"Circular dependency detected. Remaining nodes: {remaining_nodes}")
                # Add remaining nodes to a final batch to prevent infinite loop
                ready_nodes = [node_map[node_id] for node_id in remaining_nodes]
            
            # Create batch with ready nodes
            batch = ExecutionBatch(
                nodes=ready_nodes,
                batch_id=f"batch_{batch_counter}",
                dependencies_satisfied=True
            )
            batches.append(batch)
            
            # Update tracking sets
            batch_node_ids = {node.id for node in ready_nodes}
            remaining_nodes -= batch_node_ids
            completed_nodes.update(batch_node_ids)
            
            batch_counter += 1
            
            logger.debug(f"Created batch {batch_counter} with nodes: {[node.id for node in ready_nodes]}")
        
        return batches
    
    async def _execute_batch_parallel(
        self, 
        batch: ExecutionBatch, 
        previous_results: Dict[str, Any], 
        user_id: str, 
        workflow_id: str, 
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Execute all nodes in a batch in parallel.
        
        Args:
            batch: Execution batch containing nodes to execute
            previous_results: Results from previously executed nodes
            user_id: User ID for authentication
            workflow_id: Workflow ID
            execution_id: Execution ID
            
        Returns:
            Dictionary mapping node IDs to their execution results
        """
        # Create tasks for parallel execution
        tasks = []
        for node in batch.nodes:
            task = asyncio.create_task(
                self._execute_node(node, previous_results, user_id, workflow_id, execution_id),
                name=f"execute_{node.id}"
            )
            tasks.append((node.id, task))
        
        # Wait for all tasks to complete
        batch_results = {}
        for node_id, task in tasks:
            try:
                result = await task
                batch_results[node_id] = result
                logger.info(f"Node {node_id} completed successfully")
            except Exception as e:
                logger.error(f"Node {node_id} failed: {str(e)}")
                # Create a failed result
                batch_results[node_id] = type('Result', (), {
                    'success': False,
                    'data': None,
                    'error': str(e),
                    'connector_name': 'unknown',
                    'started_at': datetime.utcnow(),
                    'completed_at': datetime.utcnow(),
                    'duration_ms': 0
                })()
        
        return batch_results
    
    async def _execute_node(
        self, 
        node: WorkflowNode, 
        previous_results: Dict[str, Any], 
        user_id: str, 
        workflow_id: str, 
        execution_id: str
    ) -> Any:
        """
        Execute a single workflow node.
        
        Args:
            node: The workflow node to execute
            previous_results: Results from previously executed nodes
            user_id: User ID for authentication
            workflow_id: Workflow ID
            execution_id: Execution ID
            
        Returns:
            Node execution result
        """
        start_time = datetime.utcnow()
        logger.info(f"Executing node {node.id} with connector {node.connector_name}")
        
        try:
            # Get the connector
            connector = self.connector_registry.create_connector(node.connector_name)
            
            # Load authentication tokens for this connector
            auth_tokens = await self._load_auth_tokens_for_connector(user_id, node.connector_name)
            
            # Prepare execution context
            context = ConnectorExecutionContext(
                user_id=user_id,
                workflow_id=workflow_id,
                node_id=node.id,
                auth_tokens=auth_tokens,
                previous_results=previous_results
            )
            
            # Resolve parameters with previous results
            resolved_params = await self._resolve_node_parameters(node.parameters, previous_results)
            
            # Execute the connector
            result = await connector.execute_with_retry(resolved_params, context)
            
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Create result object
            node_result = type('NodeResult', (), {
                'success': result.success,
                'data': result.data,
                'error': result.error,
                'connector_name': node.connector_name,
                'started_at': start_time,
                'completed_at': end_time,
                'duration_ms': duration_ms
            })()
            
            if not result.success:
                logger.error(f"Node {node.id} failed: {result.error}")
            else:
                logger.info(f"Node {node.id} completed successfully in {duration_ms}ms")
            
            return node_result
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.error(f"Node {node.id} execution failed: {str(e)}")
            
            # Create failed result
            return type('NodeResult', (), {
                'success': False,
                'data': None,
                'error': str(e),
                'connector_name': node.connector_name,
                'started_at': start_time,
                'completed_at': end_time,
                'duration_ms': duration_ms
            })()
    
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
        
        logger.info(f"Available previous results: {list(previous_results.keys())}")
        logger.debug(f"Input parameters: {parameters}")
        
        for key, value in parameters.items():
            resolved[key] = await self._resolve_parameter_value(value, previous_results)
        
        logger.debug(f"Final resolved parameters: {resolved}")
        return resolved
    
    async def _resolve_parameter_value(self, value: Any, previous_results: Dict[str, Any]) -> Any:
        """
        Recursively resolve a parameter value, handling strings, arrays, and objects.
        
        Args:
            value: The parameter value to resolve (can be string, list, dict, or other)
            previous_results: Results from previously executed nodes
            
        Returns:
            Resolved value with references substituted
        """
        import re
        
        if isinstance(value, str):
            # Process string values for template resolution
            resolved_value = value
            
            # Process patterns sequentially to avoid conflicts
            # 1. First process double braces {{...}}
            double_brace_pattern = r'\{\{([^}]+)\}\}'
            double_matches = re.findall(double_brace_pattern, value)
            
            for reference in double_matches:
                original_pattern = f"{{{{{reference}}}}}"  # {{reference}}
                replacement_value = self._resolve_reference(reference, previous_results)
                
                if replacement_value is not None:
                    resolved_value = resolved_value.replace(original_pattern, str(replacement_value))
                    logger.debug(f"Replaced {original_pattern} with resolved value")
                else:
                    logger.warning(f"Could not resolve reference: {reference}")
            
            if resolved_value != value:
                logger.debug(f"String resolved: '{value}' -> '{resolved_value}'")
            
            return resolved_value
            
        elif isinstance(value, list):
            # Recursively process each item in the list
            resolved_list = []
            for item in value:
                resolved_item = await self._resolve_parameter_value(item, previous_results)
                resolved_list.append(resolved_item)
            
            if resolved_list != value:
                logger.debug(f"List resolved: {value} -> {resolved_list}")
            
            return resolved_list
            
        elif isinstance(value, dict):
            # Recursively process each value in the dictionary
            resolved_dict = {}
            for k, v in value.items():
                resolved_dict[k] = await self._resolve_parameter_value(v, previous_results)
            
            if resolved_dict != value:
                logger.debug(f"Dict resolved: {value} -> {resolved_dict}")
            
            return resolved_dict
            
        else:
            # For other types (int, bool, None, etc.), return as-is
            return value
    
    def _resolve_reference(self, reference: str, previous_results: Dict[str, Any]) -> Any:
        """
        Resolve a single parameter reference to its actual value.
        
        Args:
            reference: The reference string (e.g., "node_id.field_path" or "connector_name.field_path")
            previous_results: Results from previously executed nodes
            
        Returns:
            The resolved value or None if not found
        """
        logger.debug(f"Attempting to resolve reference: '{reference}'")
        logger.debug(f"Available previous results: {list(previous_results.keys())}")
        
        # Handle special system references
        if reference == "schedule.triggered_at":
            from datetime import datetime
            current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            logger.debug(f"Resolved system reference {reference} to current time: {current_time}")
            return current_time
        
        if "." in reference:
            # Handle node_id.field_path or connector_name.field_path
            node_or_connector, field_path = reference.split(".", 1)
            logger.debug(f"Split reference: connector='{node_or_connector}', field='{field_path}'")
            
            # First try direct node ID lookup
            if node_or_connector in previous_results:
                node_result = previous_results[node_or_connector]
                logger.debug(f"Found node result for {node_or_connector}")
                
                # Navigate the field path
                if hasattr(node_result, 'data'):
                    replacement_value = self._get_nested_value(node_result.data, field_path)
                else:
                    replacement_value = self._get_nested_value(node_result, field_path)
                    
                logger.debug(f"Extracted value for {field_path}: {replacement_value}")
                return replacement_value
            
            # If not found by node ID, try to find by connector name
            for node_id, node_result in previous_results.items():
                connector_name = None
                if hasattr(node_result, 'connector_name'):
                    connector_name = node_result.connector_name
                elif isinstance(node_result, dict) and 'connector_name' in node_result:
                    connector_name = node_result['connector_name']
                    
                if connector_name == node_or_connector:
                    logger.debug(f"Found node result by connector name {node_or_connector} -> {node_id}")
                    
                    if hasattr(node_result, 'data'):
                        replacement_value = self._get_nested_value(node_result.data, field_path)
                    elif isinstance(node_result, dict) and 'data' in node_result:
                        replacement_value = self._get_nested_value(node_result['data'], field_path)
                    else:
                        replacement_value = self._get_nested_value(node_result, field_path)
                        
                    logger.debug(f"Extracted value for {field_path}: {replacement_value}")
                    return replacement_value
            
            logger.warning(f"Referenced node/connector {node_or_connector} not found in previous results")
            return None
        else:
            # Simple node reference  
            if reference in previous_results:
                node_result = previous_results[reference]
                if hasattr(node_result, 'data'):
                    return node_result.data
                elif isinstance(node_result, dict) and 'data' in node_result:
                    return node_result['data']
                else:
                    return node_result
            
            # Try to find by connector name
            for node_id, node_result in previous_results.items():
                connector_name = None
                if hasattr(node_result, 'connector_name'):
                    connector_name = node_result.connector_name
                elif isinstance(node_result, dict) and 'connector_name' in node_result:
                    connector_name = node_result['connector_name']
                    
                if connector_name == reference:
                    if hasattr(node_result, 'data'):
                        return node_result.data
                    elif isinstance(node_result, dict) and 'data' in node_result:
                        return node_result['data']
                    else:
                        return node_result
            
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
                            logger.debug(f"Combined Perplexity content with {len(citations)} citations")
                            return combined_result
                    
                    # Fallback to standard field mapping
                    for alternative in FIELD_MAPPINGS['result']:
                        if alternative in current:
                            current = current[alternative]
                            logger.debug(f"Mapped field 'result' to '{alternative}' in data")
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
        
        logger.debug(f"Successfully extracted value from path '{field_path}': {current}")
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
            
            # Try to get OAuth2 token first (most common for connectors like Gmail, Google Sheets)
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
            connector_name: The connector name (e.g., 'gmail_connector', 'google_sheets')
            refresh_token: The refresh token to use
            
        Returns:
            Dictionary with new access token and related data, or None if refresh failed
        """
        try:
            if connector_name in ["gmail_connector", "google_sheets"]:
                from app.core.config import settings
                import httpx
                
                # Use Gmail credentials for Google Sheets as they use the same OAuth app
                if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
                    logger.error("Google OAuth credentials not configured")
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

    async def _store_execution_result(self, execution_result: ExecutionResult):
        """
        Store execution result in database using existing schema.
        
        Args:
            execution_result: The execution result to store
        """
        try:
            supabase = get_supabase_client()
            
            # Convert execution result to match existing database schema exactly
            execution_data = {
                "id": execution_result.execution_id,
                "workflow_id": execution_result.workflow_id,
                "user_id": execution_result.user_id,
                "status": execution_result.status.value,
                "trigger_type": "manual",  # TODO: Support other trigger types
                "execution_log": [],  # Parallel execution doesn't use execution log
                "result": {
                    "node_results": [
                        {
                            "node_id": nr.node_id,
                            "connector_name": nr.connector_name,
                            "status": nr.status.value,
                            "result": nr.result,
                            "error": nr.error,
                            "started_at": nr.started_at.isoformat(),
                            "completed_at": nr.completed_at.isoformat() if nr.completed_at else None,
                            "duration_ms": nr.duration_ms
                        }
                        for nr in execution_result.node_results
                    ]
                },
                "error_message": execution_result.error,
                "started_at": execution_result.started_at.isoformat(),
                "completed_at": execution_result.completed_at.isoformat() if execution_result.completed_at else None,
                "duration_ms": execution_result.total_duration_ms
            }
            
            # Store in database
            response = supabase.table("workflow_executions").insert(execution_data).execute()
            
            if response.data:
                logger.info(f"Stored execution result for {execution_result.execution_id}")
            else:
                logger.error(f"Failed to store execution result: {response}")
            
        except Exception as e:
            logger.error(f"Error storing execution result: {str(e)}")
            # Continue execution even if storage fails
            pass
    
    def should_use_parallel_execution(self, workflow: WorkflowPlan) -> bool:
        """
        Determine if a workflow should use parallel execution.
        
        Args:
            workflow: The workflow to analyze
            
        Returns:
            True if parallel execution would be beneficial
        """
        # Check if workflow has nodes that can be executed in parallel
        node_deps = {node.id: set(node.dependencies) for node in workflow.nodes}
        
        # Find nodes with multiple dependents (parallel scenarios)
        dependents_map = {}
        for node in workflow.nodes:
            for dependency in node.dependencies:
                if dependency not in dependents_map:
                    dependents_map[dependency] = []
                dependents_map[dependency].append(node.id)
        
        # If any node has multiple dependents, parallel execution would be beneficial
        parallel_scenarios = [dep for dep, dependents in dependents_map.items() if len(dependents) > 1]
        
        if parallel_scenarios:
            logger.info(f"Workflow {workflow.id} has parallel scenarios: {parallel_scenarios}")
            return True
        
        # Check if workflow has independent branches that can run in parallel
        batches = self._create_execution_batches(workflow.nodes)
        parallel_batches = [batch for batch in batches if len(batch.nodes) > 1]
        
        if parallel_batches:
            logger.info(f"Workflow {workflow.id} has {len(parallel_batches)} batches with parallel nodes")
            return True
        
        logger.info(f"Workflow {workflow.id} does not benefit from parallel execution")
        return False