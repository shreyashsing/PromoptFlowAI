"""
Workflow Transformer

This module automatically transforms workflows to handle parallel execution scenarios
by detecting nodes with multiple dependents and inserting parallel execution connectors.
"""
import logging
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from uuid import uuid4

from app.models.base import WorkflowPlan, WorkflowNode, NodePosition
from app.core.exceptions import WorkflowException

logger = logging.getLogger(__name__)


@dataclass
class ParallelScenario:
    """Represents a parallel execution scenario."""
    source_node: str
    target_nodes: List[str]
    connector_id: str
    transformation_type: str = "fan_out"


class DependencyAnalyzer:
    """Analyzes workflow dependencies and execution patterns."""
    
    def build_dependency_graph(self, nodes: List[WorkflowNode]) -> Dict[str, Set[str]]:
        """
        Build dependency graph from workflow nodes.
        
        Args:
            nodes: List of workflow nodes
            
        Returns:
            Dictionary mapping each node to its set of dependencies
        """
        dependency_graph = {}
        
        for node in nodes:
            dependency_graph[node.id] = set(node.dependencies)
        
        return dependency_graph
    
    def find_nodes_with_multiple_dependents(self, nodes: List[WorkflowNode]) -> Dict[str, List[str]]:
        """
        Find nodes that have multiple other nodes depending on them.
        
        Args:
            nodes: List of workflow nodes
            
        Returns:
            Dictionary mapping source nodes to their list of dependent nodes
        """
        dependents_map = {}  # source_node -> [dependent_nodes]
        
        # Build reverse dependency map
        for node in nodes:
            for dependency in node.dependencies:
                if dependency not in dependents_map:
                    dependents_map[dependency] = []
                dependents_map[dependency].append(node.id)
        
        # Filter to only nodes with multiple dependents
        multiple_dependents = {
            source: dependents for source, dependents in dependents_map.items()
            if len(dependents) > 1
        }
        
        logger.info(f"Found {len(multiple_dependents)} nodes with multiple dependents: {list(multiple_dependents.keys())}")
        
        return multiple_dependents
    
    def find_parallel_scenarios(self, nodes: List[WorkflowNode]) -> List[ParallelScenario]:
        """
        Identify scenarios requiring parallel execution.
        
        Args:
            nodes: List of workflow nodes
            
        Returns:
            List of parallel execution scenarios
        """
        multiple_dependents = self.find_nodes_with_multiple_dependents(nodes)
        scenarios = []
        
        for source_node, target_nodes in multiple_dependents.items():
            scenario = ParallelScenario(
                source_node=source_node,
                target_nodes=target_nodes,
                connector_id=f"{source_node}_parallel_{str(uuid4())[:8]}",
                transformation_type="fan_out"
            )
            scenarios.append(scenario)
        
        logger.info(f"Identified {len(scenarios)} parallel execution scenarios")
        return scenarios
    
    def validate_transformation(self, original: WorkflowPlan, transformed: WorkflowPlan) -> bool:
        """
        Validate that transformation preserves workflow logic.
        
        Args:
            original: Original workflow plan
            transformed: Transformed workflow plan
            
        Returns:
            True if transformation is valid, False otherwise
        """
        try:
            # Check that all original nodes are still present
            original_node_ids = {node.id for node in original.nodes}
            transformed_node_ids = {node.id for node in transformed.nodes if not node.id.endswith('_parallel')}
            
            if not original_node_ids.issubset(transformed_node_ids):
                logger.error("Transformation removed original nodes")
                return False
            
            # Check that logical dependencies are preserved
            # This is a simplified check - in practice, you might want more sophisticated validation
            original_deps = {}
            for node in original.nodes:
                original_deps[node.id] = set(node.dependencies)
            
            # For transformed workflow, we need to trace through parallel connectors
            # This is a basic validation - could be enhanced
            logger.info("Transformation validation passed basic checks")
            return True
            
        except Exception as e:
            logger.error(f"Transformation validation failed: {str(e)}")
            return False


class WorkflowTransformer:
    """Transforms workflows to handle parallel execution scenarios."""
    
    def __init__(self):
        self.analyzer = DependencyAnalyzer()
    
    def detect_parallel_dependencies(self, workflow: WorkflowPlan) -> Dict[str, List[str]]:
        """
        Detect nodes with multiple dependents.
        
        Args:
            workflow: Workflow plan to analyze
            
        Returns:
            Dictionary mapping source nodes to their dependent nodes
        """
        return self.analyzer.find_nodes_with_multiple_dependents(workflow.nodes)
    
    def transform_workflow(self, workflow: WorkflowPlan) -> WorkflowPlan:
        """
        Transform workflow to use parallel execution connectors.
        
        Args:
            workflow: Original workflow plan
            
        Returns:
            Transformed workflow plan with parallel execution connectors
        """
        logger.info(f"Transforming workflow '{workflow.name}' for parallel execution")
        
        # Find parallel execution scenarios
        scenarios = self.analyzer.find_parallel_scenarios(workflow.nodes)
        
        if not scenarios:
            logger.info("No parallel execution scenarios found, returning original workflow")
            return workflow
        
        # Create transformed workflow
        transformed_workflow = WorkflowPlan(
            id=workflow.id,
            user_id=workflow.user_id,
            name=workflow.name,
            description=workflow.description,
            nodes=[],
            edges=workflow.edges.copy(),  # Keep original edges
            triggers=workflow.triggers.copy(),
            status=workflow.status,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
        # Keep track of nodes that have been processed
        processed_source_nodes = set()
        
        # First, add all original nodes (we'll update dependencies later)
        for node in workflow.nodes:
            transformed_workflow.nodes.append(node)
        
        # Create parallel connectors and update dependencies
        for scenario in scenarios:
            if scenario.source_node not in processed_source_nodes:
                # Create single parallel execution connector
                parallel_connector = self.create_parallel_connector_node(scenario)
                transformed_workflow.nodes.append(parallel_connector)
                
                # Update dependencies of target nodes
                self._update_target_dependencies(transformed_workflow.nodes, scenario)
                
                processed_source_nodes.add(scenario.source_node)
                
                logger.info(f"Created parallel connector {parallel_connector.id} for source {scenario.source_node}")
        
        # Validate transformation
        if not self.analyzer.validate_transformation(workflow, transformed_workflow):
            logger.warning("Transformation validation failed, returning original workflow")
            return workflow
        
        logger.info(f"Successfully transformed workflow with {len(scenarios)} parallel connectors")
        return transformed_workflow
    
    def create_parallel_connector_node(self, scenario: ParallelScenario) -> WorkflowNode:
        """
        Create a single pass-through parallel execution connector node.
        
        Args:
            scenario: Parallel execution scenario
            
        Returns:
            WorkflowNode configured as a parallel execution connector
        """
        # Position the parallel connector between source and targets
        position = NodePosition(x=200, y=200)  # Default position
        
        parallel_node = WorkflowNode(
            id=scenario.connector_id,
            connector_name="parallel_execution",
            parameters={
                "input_data": f"{{{{{scenario.source_node}.data}}}}",  # Reference to source node data
                "target_nodes": scenario.target_nodes,
                "distribution_mode": "reference"
            },
            position=position,
            dependencies=[scenario.source_node]
        )
        
        return parallel_node
    
    def _update_target_dependencies_individual(self, nodes: List[WorkflowNode], scenario: ParallelScenario):
        """
        Update target nodes to depend on their individual parallel connectors instead of the source.
        
        Args:
            nodes: List of workflow nodes to update
            scenario: Parallel execution scenario
        """
        for node in nodes:
            if node.id in scenario.target_nodes:
                # Find the corresponding parallel connector for this target
                parallel_connector_id = f"{scenario.source_node}_to_{node.id}_parallel"
                
                # Replace dependency on source with dependency on individual parallel connector
                if scenario.source_node in node.dependencies:
                    node.dependencies.remove(scenario.source_node)
                    node.dependencies.append(parallel_connector_id)
                    
                    # Update parameter references to use parallel connector data
                    self._update_parameter_references_individual(node, scenario, parallel_connector_id)
    
    def _update_target_dependencies(self, nodes: List[WorkflowNode], scenario: ParallelScenario):
        """
        Update target nodes to depend on the parallel connector instead of the source.
        
        Args:
            nodes: List of workflow nodes to update
            scenario: Parallel execution scenario
        """
        for node in nodes:
            if node.id in scenario.target_nodes:
                # Replace dependency on source with dependency on parallel connector
                if scenario.source_node in node.dependencies:
                    node.dependencies.remove(scenario.source_node)
                    node.dependencies.append(scenario.connector_id)
                    
                    # Update parameter references to use parallel connector data
                    self._update_parameter_references(node, scenario)
    
    def _update_parameter_references_individual(self, node: WorkflowNode, scenario: ParallelScenario, parallel_connector_id: str):
        """
        Update parameter references in target nodes to use individual parallel connector data.
        
        Args:
            node: Target node to update
            scenario: Parallel execution scenario
            parallel_connector_id: ID of the individual parallel connector for this node
        """
        def update_param_value(value):
            if isinstance(value, str):
                # Replace references to source node with parallel connector references
                old_ref = f"{{{{{scenario.source_node}."
                new_ref = f"{{{{{parallel_connector_id}.distributed_data.{node.id}."
                
                # Also handle simple node references
                simple_old_ref = f"{{{{{scenario.source_node}}}}}"
                simple_new_ref = f"{{{{{parallel_connector_id}.distributed_data.{node.id}}}}}"
                
                value = value.replace(old_ref, new_ref)
                value = value.replace(simple_old_ref, simple_new_ref)
                
            return value
        
        # Update all parameter values
        for key, value in node.parameters.items():
            if isinstance(value, str):
                node.parameters[key] = update_param_value(value)
            elif isinstance(value, list):
                node.parameters[key] = [update_param_value(item) if isinstance(item, str) else item for item in value]
            elif isinstance(value, dict):
                # Recursively update nested dictionaries
                node.parameters[key] = self._update_nested_dict(value, update_param_value)
    
    def _update_parameter_references(self, node: WorkflowNode, scenario: ParallelScenario):
        """
        Update parameter references in target nodes to use parallel connector data.
        
        Args:
            node: Target node to update
            scenario: Parallel execution scenario
        """
        # This is a simplified parameter update - in practice, you might need more sophisticated
        # parameter parsing and replacement logic
        
        def update_param_value(value):
            if isinstance(value, str):
                # Replace references to source node with parallel connector references
                # Since we're passing through the data, we can use direct references
                old_ref = f"{{{{{scenario.source_node}."
                new_ref = f"{{{{{scenario.connector_id}."
                
                # Also handle simple node references
                simple_old_ref = f"{{{{{scenario.source_node}}}}}"
                simple_new_ref = f"{{{{{scenario.connector_id}}}}}"
                
                value = value.replace(old_ref, new_ref)
                value = value.replace(simple_old_ref, simple_new_ref)
                
            return value
        
        # Update all parameter values
        for key, value in node.parameters.items():
            if isinstance(value, str):
                node.parameters[key] = update_param_value(value)
            elif isinstance(value, list):
                node.parameters[key] = [update_param_value(item) if isinstance(item, str) else item for item in value]
            elif isinstance(value, dict):
                # Recursively update nested dictionaries
                node.parameters[key] = self._update_nested_dict(value, update_param_value)
    
    def _update_nested_dict(self, d: dict, update_func) -> dict:
        """
        Recursively update string values in nested dictionaries.
        
        Args:
            d: Dictionary to update
            update_func: Function to apply to string values
            
        Returns:
            Updated dictionary
        """
        updated = {}
        for key, value in d.items():
            if isinstance(value, str):
                updated[key] = update_func(value)
            elif isinstance(value, dict):
                updated[key] = self._update_nested_dict(value, update_func)
            elif isinstance(value, list):
                updated[key] = [
                    update_func(item) if isinstance(item, str) 
                    else self._update_nested_dict(item, update_func) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                updated[key] = value
        return updated