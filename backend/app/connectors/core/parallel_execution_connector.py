"""
Parallel Execution Connector

This connector handles parallel execution scenarios by distributing input data
to multiple target nodes, resolving the "Already found path" error in LangGraph workflows.
"""
import logging
import copy
from typing import Dict, Any, List
from datetime import datetime

from app.connectors.base import BaseConnector
from app.models.connector import ConnectorResult, ConnectorExecutionContext
from app.core.exceptions import ConnectorException

logger = logging.getLogger(__name__)


class ParallelExecutionError(ConnectorException):
    """Exception for parallel execution failures."""
    
    def __init__(self, message: str, failed_targets: List[str] = None, partial_results: Dict[str, Any] = None):
        super().__init__(message)
        self.failed_targets = failed_targets or []
        self.partial_results = partial_results or {}


class ParallelExecutionConnector(BaseConnector):
    """
    Connector that distributes input data to multiple target nodes for parallel execution.
    
    This connector acts as an intermediary that takes input from one node and makes it
    available to multiple dependent nodes, enabling parallel execution patterns while
    avoiding LangGraph's "Already found path" limitation.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "parallel_execution"
        self.description = "Distributes input data to multiple target nodes for parallel execution"
        
    async def execute(self, params: Dict[str, Any], context: ConnectorExecutionContext) -> ConnectorResult:
        """
        Execute parallel data distribution.
        
        Args:
            params: Dictionary containing:
                - input_data: Data to distribute to target nodes
                - target_nodes: List of target node identifiers
                - distribution_mode: "copy" or "reference" (default: "reference")
            context: Execution context with user info and previous results
            
        Returns:
            ConnectorResult with distributed data and metadata
        """
        try:
            # Extract parameters
            input_data = params.get("input_data")
            target_nodes = params.get("target_nodes", [])
            distribution_mode = params.get("distribution_mode", "reference")
            
            # Validate parameters
            if input_data is None:
                raise ParallelExecutionError("input_data parameter is required")
            
            if not target_nodes:
                raise ParallelExecutionError("target_nodes parameter is required and must not be empty")
            
            if not isinstance(target_nodes, list):
                raise ParallelExecutionError("target_nodes must be a list of strings")
            
            if distribution_mode not in ["copy", "reference"]:
                raise ParallelExecutionError("distribution_mode must be 'copy' or 'reference'")
            
            logger.info(f"Parallel execution: distributing data to {len(target_nodes)} targets using {distribution_mode} mode")
            
            # Distribute data based on mode
            distributed_data = self._distribute_data(input_data, target_nodes, distribution_mode)
            
            # For simplicity, just pass through the original data
            # The distributed_data is available for reference but we return the original data
            # This avoids LangGraph path conflicts while still enabling parallel access
            result_data = input_data
            
            logger.info(f"Successfully distributed data to {len(target_nodes)} targets")
            
            return ConnectorResult(
                success=True,
                data=result_data,
                metadata={
                    "connector_name": self.name,
                    "execution_type": "parallel_passthrough",
                    "target_nodes": target_nodes,
                    "distribution_mode": distribution_mode,
                    "original_data": input_data,
                    "distributed_data": distributed_data
                }
            )
            
        except ParallelExecutionError:
            raise
        except Exception as e:
            logger.error(f"Parallel execution failed: {str(e)}")
            raise ParallelExecutionError(f"Parallel execution failed: {str(e)}")
    
    def _distribute_data(self, input_data: Any, target_nodes: List[str], distribution_mode: str) -> Dict[str, Any]:
        """
        Distribute input data to target nodes based on distribution mode.
        
        Args:
            input_data: Data to distribute
            target_nodes: List of target node identifiers
            distribution_mode: "copy" or "reference"
            
        Returns:
            Dictionary mapping target nodes to their data
        """
        distributed_data = {}
        
        try:
            for target_node in target_nodes:
                if distribution_mode == "copy":
                    # Create a deep copy for each target
                    distributed_data[target_node] = copy.deepcopy(input_data)
                    logger.debug(f"Created deep copy of data for target: {target_node}")
                else:  # reference mode
                    # Share the same reference
                    distributed_data[target_node] = input_data
                    logger.debug(f"Created reference to data for target: {target_node}")
            
            return distributed_data
            
        except Exception as e:
            logger.error(f"Failed to distribute data: {str(e)}")
            raise ParallelExecutionError(f"Data distribution failed: {str(e)}")
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for this connector's parameters.
        
        Returns:
            JSON schema dictionary
        """
        return {
            "type": "object",
            "properties": {
                "input_data": {
                    "type": "any",
                    "description": "Data to distribute to target nodes",
                    "required": True
                },
                "target_nodes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of target node identifiers",
                    "required": True,
                    "minItems": 1
                },
                "distribution_mode": {
                    "type": "string",
                    "enum": ["copy", "reference"],
                    "default": "reference",
                    "description": "How to distribute data (copy creates new instances, reference shares)"
                }
            },
            "required": ["input_data", "target_nodes"]
        }
    
    def get_example_params(self) -> Dict[str, Any]:
        """
        Get example parameters for this connector.
        
        Returns:
            Example parameters dictionary
        """
        return {
            "input_data": {"message": "Hello from source node", "timestamp": "2024-01-01T00:00:00Z"},
            "target_nodes": ["node_b", "node_c", "node_d"],
            "distribution_mode": "reference"
        }
    
    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize parameters for this connector.
        
        Args:
            params: Raw parameters to validate
            
        Returns:
            Validated and normalized parameters
        """
        validated = params.copy()
        
        # Ensure target_nodes is a list
        if "target_nodes" in validated and not isinstance(validated["target_nodes"], list):
            raise ParallelExecutionError("target_nodes must be a list")
        
        # Set default distribution mode
        if "distribution_mode" not in validated:
            validated["distribution_mode"] = "reference"
        
        # Validate distribution mode
        if validated.get("distribution_mode") not in ["copy", "reference"]:
            raise ParallelExecutionError("distribution_mode must be 'copy' or 'reference'")
        
        return validated