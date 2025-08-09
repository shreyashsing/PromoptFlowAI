"""
Workflow Graph with n8n-inspired sophisticated dependency management.

This module provides advanced workflow graph capabilities including:
- Dependency-based execution planning
- Connection-aware data flow
- Cycle detection and handling
- Multiple input connection management
- Partial execution support
"""
import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

from app.models.base import WorkflowNode, WorkflowEdge
from app.models.enhanced_execution import (
    NodeExecutionContext, 
    NodeState, 
    ConnectionData, 
    ConnectionState,
    WaitingExecution
)

logger = logging.getLogger(__name__)


@dataclass
class GraphConnection:
    """Represents a connection in the workflow graph."""
    from_node: str
    to_node: str
    from_output: str = "main"
    to_input: str = "main"
    output_index: int = 0
    input_index: int = 0


class DirectedGraph:
    """
    Enhanced directed graph implementation with robust cycle detection.
    
    Provides comprehensive graph analysis capabilities including:
    - Strongly connected components detection
    - Topological sorting with cycle handling
    - Path analysis and reachability
    - Graph validation and integrity checks
    """
    
    def __init__(self):
        self.adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.nodes: Set[str] = set()
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add a directed edge from from_node to to_node."""
        self.nodes.add(from_node)
        self.nodes.add(to_node)
        self.adjacency_list[from_node].add(to_node)
        self.reverse_adjacency[to_node].add(from_node)
    
    def has_cycle(self) -> bool:
        """Check if the graph contains any cycles using DFS."""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.adjacency_list[node]:
                if dfs(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False
    
    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the graph using Tarjan's algorithm."""
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        cycles = []
        
        def strongconnect(node: str):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True
            
            for neighbor in self.adjacency_list[node]:
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif on_stack[neighbor]:
                    lowlinks[node] = min(lowlinks[node], index[neighbor])
            
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break
                
                if len(component) > 1:  # Only cycles with more than one node
                    cycles.append(component)
        
        for node in self.nodes:
            if node not in index:
                strongconnect(node)
        
        return cycles
    
    def topological_sort(self) -> Optional[List[str]]:
        """Return topological sort of nodes, or None if cycles exist."""
        if self.has_cycle():
            return None
        
        in_degree = {node: 0 for node in self.nodes}
        for node in self.nodes:
            for neighbor in self.adjacency_list[node]:
                in_degree[neighbor] += 1
        
        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in self.adjacency_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result if len(result) == len(self.nodes) else None


class WorkflowGraph:
    """
    n8n-inspired workflow graph with sophisticated dependency management.
    
    This class provides advanced workflow graph capabilities including:
    - Dependency resolution with cycle detection
    - Connection-aware data flow management
    - Multiple input handling with waiting execution logic
    - Parallel execution batch creation
    - Partial workflow execution support
    """
    
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.node_contexts: Dict[str, NodeExecutionContext] = {}
        self.connections: List[GraphConnection] = []
        self.waiting_executions: Dict[str, WaitingExecution] = {}
        self.directed_graph = DirectedGraph()  # Enhanced graph analysis
        
        # Connection mappings for fast lookup (n8n-inspired)
        self.connections_by_source: Dict[str, List[GraphConnection]] = defaultdict(list)
        self.connections_by_destination: Dict[str, List[GraphConnection]] = defaultdict(list)
        
    def add_node(self, node: WorkflowNode) -> None:
        """
        Add a node to the graph with dependency tracking.
        
        Args:
            node: The workflow node to add
        """
        self.nodes[node.id] = node
        
        # Create execution context with dependencies
        dependencies = set(node.dependencies) if node.dependencies else set()
        
        context = NodeExecutionContext(
            node_id=node.id,
            dependencies=dependencies,
            waiting_for=dependencies.copy(),  # Initially waiting for all dependencies
            max_retries=getattr(node, 'max_retries', 3)
        )
        
        context.transition_to(NodeState.WAITING, "Node added to graph")
        self.node_contexts[node.id] = context
        
        logger.debug(f"Added node {node.id} with dependencies: {dependencies}")
    
    def add_connection(
        self, 
        from_node: str, 
        to_node: str, 
        from_output: str = "main", 
        to_input: str = "main",
        output_index: int = 0,
        input_index: int = 0
    ) -> None:
        """
        Add a connection between nodes with automatic dependency tracking.
        
        Args:
            from_node: Source node ID
            to_node: Destination node ID
            from_output: Output name from source node
            to_input: Input name to destination node
            output_index: Output index (for multiple outputs)
            input_index: Input index (for multiple inputs)
        """
        connection = GraphConnection(
            from_node=from_node,
            to_node=to_node,
            from_output=from_output,
            to_input=to_input,
            output_index=output_index,
            input_index=input_index
        )
        
        self.connections.append(connection)
        self.connections_by_source[from_node].append(connection)
        self.connections_by_destination[to_node].append(connection)
        
        # Update directed graph for enhanced cycle detection
        self.directed_graph.add_edge(from_node, to_node)
        
        # Update dependency tracking
        if to_node in self.node_contexts:
            self.node_contexts[to_node].dependencies.add(from_node)
            self.node_contexts[to_node].waiting_for.add(from_node)
            
        if from_node in self.node_contexts:
            self.node_contexts[from_node].dependents.add(to_node)
        
        # Set up waiting execution for nodes with multiple inputs
        self._setup_waiting_execution(to_node)
        
        logger.debug(f"Added connection: {from_node}[{from_output}] -> {to_node}[{to_input}]")
    
    def _setup_waiting_execution(self, node_id: str) -> None:
        """
        Set up waiting execution for nodes with multiple input connections.
        
        This implements n8n's sophisticated multiple input handling.
        
        Args:
            node_id: The node ID to set up waiting execution for
        """
        incoming_connections = self.connections_by_destination[node_id]
        
        if len(incoming_connections) > 1:
            # Node has multiple inputs - set up waiting execution
            if node_id not in self.waiting_executions:
                self.waiting_executions[node_id] = WaitingExecution(node_id=node_id)
            
            waiting_exec = self.waiting_executions[node_id]
            
            for connection in incoming_connections:
                waiting_exec.add_expected_input(
                    connection.to_input,
                    connection.from_node
                )
            
            logger.debug(f"Set up waiting execution for {node_id} with {len(incoming_connections)} inputs")
    
    def get_ready_nodes(self) -> List[str]:
        """
        Get nodes that are ready to execute (n8n-inspired dependency checking).
        
        A node is ready if:
        1. It's in WAITING state
        2. All its dependencies are satisfied (in SUCCESS state)
        3. For multiple input nodes, all expected inputs are received
        
        Returns:
            List of node IDs ready for execution
        """
        ready_nodes = []
        
        for node_id, context in self.node_contexts.items():
            if context.state != NodeState.WAITING:
                continue
            
            # Check if all dependencies are satisfied
            dependencies_satisfied = all(
                self.node_contexts[dep_id].state == NodeState.SUCCESS
                for dep_id in context.dependencies
                if dep_id in self.node_contexts
            )
            
            if not dependencies_satisfied:
                continue
            
            # For nodes with multiple inputs, check waiting execution
            if node_id in self.waiting_executions:
                if not self.waiting_executions[node_id].is_ready():
                    continue
            
            ready_nodes.append(node_id)
        
        return ready_nodes
    
    def prepare_node_input(self, node_id: str) -> Dict[str, Any]:
        """
        Prepare input data for a node by collecting outputs from connected nodes.
        
        This implements n8n's sophisticated input data merging for nodes with
        multiple input connections.
        
        Args:
            node_id: The node ID to prepare input for
            
        Returns:
            Dictionary containing merged input data
        """
        # Check if node has waiting execution (multiple inputs)
        if node_id in self.waiting_executions:
            waiting_exec = self.waiting_executions[node_id]
            if waiting_exec.is_ready():
                return waiting_exec.get_merged_input_data()
            else:
                logger.warning(f"Node {node_id} not ready - missing inputs: {waiting_exec.get_missing_inputs()}")
                return {}
        
        # Single input or no waiting execution - collect data normally
        input_data = {}
        incoming_connections = self.connections_by_destination[node_id]
        
        for connection in incoming_connections:
            from_context = self.node_contexts.get(connection.from_node)
            if from_context and from_context.state == NodeState.SUCCESS:
                output_data = from_context.output_data.get(connection.from_output)
                if output_data is not None:
                    input_data[connection.to_input] = output_data
        
        return input_data
    
    def mark_node_completed(self, node_id: str, output_data: Dict[str, Any]) -> None:
        """
        Mark a node as completed and propagate data to dependent nodes.
        
        Args:
            node_id: The completed node ID
            output_data: The output data from the node
        """
        context = self.node_contexts.get(node_id)
        if not context:
            return
        
        # Update node context
        context.output_data = output_data
        context.transition_to(NodeState.SUCCESS, "Node execution completed")
        
        # Propagate data to dependent nodes with waiting executions
        outgoing_connections = self.connections_by_source[node_id]
        
        for connection in outgoing_connections:
            target_node = connection.to_node
            
            # Update waiting execution if target node has multiple inputs
            if target_node in self.waiting_executions:
                waiting_exec = self.waiting_executions[target_node]
                output_value = output_data.get(connection.from_output)
                waiting_exec.receive_input(
                    connection.to_input,
                    node_id,
                    output_value
                )
                
                # Mark dependency as satisfied in target node context
                target_context = self.node_contexts.get(target_node)
                if target_context:
                    target_context.mark_dependency_satisfied(node_id)
            else:
                # Single input - mark dependency as satisfied
                target_context = self.node_contexts.get(target_node)
                if target_context:
                    target_context.mark_dependency_satisfied(node_id)
        
        logger.info(f"Node {node_id} completed and data propagated to {len(outgoing_connections)} connections")
    
    def get_parallel_batches(self) -> List[List[str]]:
        """
        Create execution batches where nodes in the same batch can run in parallel.
        
        This implements n8n's dependency-based execution planning with sophisticated
        batch creation that considers connection dependencies.
        
        Returns:
            List of batches, where each batch is a list of node IDs that can execute in parallel
        """
        batches = []
        remaining_nodes = set(self.node_contexts.keys())
        completed_nodes = set()
        
        batch_counter = 0
        while remaining_nodes:
            # Find nodes ready for execution
            ready_nodes = []
            
            for node_id in remaining_nodes:
                context = self.node_contexts[node_id]
                
                # Check if all dependencies are in completed_nodes
                if context.dependencies.issubset(completed_nodes):
                    ready_nodes.append(node_id)
            
            if not ready_nodes:
                # Handle circular dependencies or other issues
                cycles = self.detect_cycles()
                if cycles:
                    logger.error(f"Circular dependencies detected: {cycles}")
                    # Break cycles by adding one node from each cycle
                    for cycle in cycles:
                        if cycle[0] in remaining_nodes:
                            ready_nodes.append(cycle[0])
                            break
                else:
                    # No cycles but no ready nodes - add remaining nodes to prevent infinite loop
                    logger.warning(f"No ready nodes found but {len(remaining_nodes)} remaining. "
                                 f"Adding all remaining nodes: {remaining_nodes}")
                    ready_nodes = list(remaining_nodes)
            
            if ready_nodes:
                batches.append(ready_nodes)
                remaining_nodes -= set(ready_nodes)
                completed_nodes.update(ready_nodes)
                
                batch_counter += 1
                logger.debug(f"Created batch {batch_counter} with {len(ready_nodes)} nodes: {ready_nodes}")
        
        return batches
    
    def detect_cycles(self) -> List[List[str]]:
        """
        Detect circular dependencies in the workflow graph.
        
        Uses enhanced DirectedGraph with Tarjan's algorithm for robust cycle detection.
        
        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        # Use enhanced DirectedGraph for more robust cycle detection
        cycles = self.directed_graph.find_cycles()
        
        if cycles:
            logger.warning(f"Detected {len(cycles)} cycles in workflow graph: {cycles}")
        
        return cycles
    
    def has_cycles(self) -> bool:
        """
        Quick check if the graph contains any cycles.
        
        Returns:
            True if cycles exist, False otherwise
        """
        return self.directed_graph.has_cycle()
    
    def get_topological_order(self) -> Optional[List[str]]:
        """
        Get topological ordering of nodes if no cycles exist.
        
        Returns:
            List of node IDs in topological order, or None if cycles exist
        """
        return self.directed_graph.topological_sort()
    
    def is_connection_empty(self, from_node: str, to_node: str, connection_type: str = "main") -> bool:
        """
        Check if a connection is empty (has no data).
        
        This implements n8n's connection emptiness checking for proper data flow validation.
        
        Args:
            from_node: Source node ID
            to_node: Destination node ID
            connection_type: Type of connection (default: "main")
            
        Returns:
            True if connection is empty, False if it has data
        """
        from_context = self.node_contexts.get(from_node)
        if not from_context or from_context.state != NodeState.SUCCESS:
            return True
        
        output_data = from_context.output_data.get(connection_type)
        if output_data is None:
            return True
        
        # Check if data is empty (empty list, empty dict, etc.)
        if isinstance(output_data, (list, dict, str)) and len(output_data) == 0:
            return True
        
        return False
    
    def get_node_input_connections(self, node_id: str) -> List[GraphConnection]:
        """Get all input connections for a node."""
        return self.connections_by_destination[node_id]
    
    def get_node_output_connections(self, node_id: str) -> List[GraphConnection]:
        """Get all output connections for a node."""
        return self.connections_by_source[node_id]
    
    def get_parent_nodes(self, node_id: str) -> Set[str]:
        """Get all parent nodes (dependencies) of a given node."""
        return self.node_contexts[node_id].dependencies if node_id in self.node_contexts else set()
    
    def get_child_nodes(self, node_id: str) -> Set[str]:
        """Get all child nodes (dependents) of a given node."""
        return self.node_contexts[node_id].dependents if node_id in self.node_contexts else set()
    
    def create_subgraph(self, node_ids: Set[str]) -> 'WorkflowGraph':
        """
        Create a subgraph containing only the specified nodes and their connections.
        
        This supports n8n's partial execution capabilities.
        
        Args:
            node_ids: Set of node IDs to include in the subgraph
            
        Returns:
            New WorkflowGraph containing only the specified nodes
        """
        subgraph = WorkflowGraph()
        
        # Add nodes
        for node_id in node_ids:
            if node_id in self.nodes:
                subgraph.add_node(self.nodes[node_id])
        
        # Add connections between included nodes
        for connection in self.connections:
            if connection.from_node in node_ids and connection.to_node in node_ids:
                subgraph.add_connection(
                    connection.from_node,
                    connection.to_node,
                    connection.from_output,
                    connection.to_input,
                    connection.output_index,
                    connection.input_index
                )
        
        return subgraph
    
    def validate_graph(self) -> Dict[str, List[str]]:
        """
        Validate the workflow graph for common issues.
        
        Returns:
            Dictionary with validation results:
            - "errors": List of error messages
            - "warnings": List of warning messages
        """
        errors = []
        warnings = []
        
        # Check for orphaned nodes
        for node_id in self.nodes:
            incoming = len(self.connections_by_destination[node_id])
            outgoing = len(self.connections_by_source[node_id])
            
            if incoming == 0 and outgoing == 0:
                warnings.append(f"Node {node_id} has no connections (orphaned)")
            elif incoming == 0:
                # Could be a trigger node
                pass
            elif outgoing == 0:
                # Could be a final node
                pass
        
        # Check for cycles
        cycles = self.detect_cycles()
        if cycles:
            errors.extend([f"Circular dependency detected: {' -> '.join(cycle)}" for cycle in cycles])
        
        # Check for missing nodes in connections
        all_node_ids = set(self.nodes.keys())
        for connection in self.connections:
            if connection.from_node not in all_node_ids:
                errors.append(f"Connection references missing source node: {connection.from_node}")
            if connection.to_node not in all_node_ids:
                errors.append(f"Connection references missing destination node: {connection.to_node}")
        
        return {
            "errors": errors,
            "warnings": warnings
        }
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get statistics about the workflow graph."""
        node_count = len(self.nodes)
        connection_count = len(self.connections)
        
        # Count nodes by state
        state_counts = {}
        for state in NodeState:
            state_counts[state.value] = sum(
                1 for ctx in self.node_contexts.values()
                if ctx.state == state
            )
        
        # Calculate complexity metrics
        max_dependencies = max(
            len(ctx.dependencies) for ctx in self.node_contexts.values()
        ) if self.node_contexts else 0
        
        max_dependents = max(
            len(ctx.dependents) for ctx in self.node_contexts.values()
        ) if self.node_contexts else 0
        
        return {
            "node_count": node_count,
            "connection_count": connection_count,
            "state_counts": state_counts,
            "max_dependencies": max_dependencies,
            "max_dependents": max_dependents,
            "waiting_executions": len(self.waiting_executions),
            "cycles_detected": len(self.detect_cycles())
        }