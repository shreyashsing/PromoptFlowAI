"""
Enhanced execution models with n8n-inspired state management.

This module provides comprehensive state tracking for workflow execution,
including detailed node states, execution contexts, and state transitions.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Union
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum
from pydantic import Field

from app.models.execution import ExecutionResult, ExecutionStatus, NodeExecutionResult

logger = logging.getLogger(__name__)


class NodeState(Enum):
    """
    Detailed node execution states inspired by n8n's state management.
    
    These states provide comprehensive tracking of node lifecycle:
    - WAITING: Node is waiting for dependencies or execution slot
    - QUEUED: Node is queued for execution (dependencies satisfied)
    - RUNNING: Node is currently executing
    - SUCCESS: Node completed successfully
    - ERROR: Node failed with error
    - SKIPPED: Node was skipped due to conditions
    - CANCELLED: Node execution was cancelled
    """
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ConnectionState(Enum):
    """State of data connections between nodes."""
    EMPTY = "empty"
    PARTIAL = "partial"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StateTransition:
    """Records a state transition for audit and debugging."""
    from_state: NodeState
    to_state: NodeState
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionData:
    """
    Represents data flow between nodes with n8n-inspired connection handling.
    """
    from_node: str
    to_node: str
    from_output: str = "main"
    to_input: str = "main"
    data: Any = None
    state: ConnectionState = ConnectionState.EMPTY
    timestamp: Optional[datetime] = None


@dataclass
class NodeExecutionContext:
    """
    Enhanced execution context with comprehensive state tracking.
    
    This provides n8n-inspired detailed tracking of node execution state,
    including input/output data, dependencies, retry information, and timing.
    """
    node_id: str
    state: NodeState = NodeState.WAITING
    
    # Data flow
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    
    # Error handling
    error: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    
    # Dependencies
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    waiting_for: Set[str] = field(default_factory=set)
    
    # State history
    state_transitions: List[StateTransition] = field(default_factory=list)
    
    # Execution metadata
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def transition_to(self, new_state: NodeState, reason: str, metadata: Dict[str, Any] = None) -> None:
        """
        Transition to a new state with proper logging and audit trail.
        
        Args:
            new_state: The new state to transition to
            reason: Reason for the state transition
            metadata: Additional metadata for the transition
        """
        if self.state == new_state:
            return  # No transition needed
        
        old_state = self.state
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            timestamp=datetime.utcnow(),
            reason=reason,
            metadata=metadata or {}
        )
        
        self.state_transitions.append(transition)
        self.state = new_state
        self.last_heartbeat = datetime.utcnow()
        
        logger.info(f"Node {self.node_id} transitioned from {old_state.value} to {new_state.value}: {reason}")
    
    def is_ready_to_execute(self) -> bool:
        """Check if node is ready to execute (all dependencies satisfied)."""
        return (
            self.state == NodeState.WAITING and
            len(self.waiting_for) == 0 and
            all(dep not in self.waiting_for for dep in self.dependencies)
        )
    
    def mark_dependency_satisfied(self, dependency_id: str) -> None:
        """Mark a dependency as satisfied."""
        if dependency_id in self.waiting_for:
            self.waiting_for.remove(dependency_id)
            logger.debug(f"Node {self.node_id}: dependency {dependency_id} satisfied. "
                        f"Still waiting for: {self.waiting_for}")
    
    def get_execution_duration_ms(self) -> int:
        """Get execution duration in milliseconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return 0
    
    def get_total_duration_ms(self) -> int:
        """Get total duration from creation to completion."""
        if self.state_transitions and self.completed_at:
            first_transition = self.state_transitions[0]
            return int((self.completed_at - first_transition.timestamp).total_seconds() * 1000)
        return 0
    
    def is_terminal_state(self) -> bool:
        """Check if node is in a terminal state (won't change further)."""
        return self.state in {NodeState.SUCCESS, NodeState.ERROR, NodeState.SKIPPED, NodeState.CANCELLED}
    
    def can_retry(self) -> bool:
        """Check if node can be retried."""
        return (
            self.state == NodeState.ERROR and
            self.retry_count < self.max_retries
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "error_details": self.error_details,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "waiting_for": list(self.waiting_for),
            "state_transitions": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "reason": t.reason,
                    "metadata": t.metadata
                }
                for t in self.state_transitions
            ],
            "execution_metadata": self.execution_metadata,
            "execution_duration_ms": self.get_execution_duration_ms(),
            "total_duration_ms": self.get_total_duration_ms()
        }


@dataclass
class WaitingExecution:
    """
    Manages nodes waiting for multiple inputs (n8n-inspired).
    
    This handles the complex scenario where a node has multiple input connections
    and needs to wait for data from all of them before it can execute.
    """
    node_id: str
    expected_inputs: Dict[str, Set[str]] = field(default_factory=dict)  # input_name -> set of source_node_ids
    received_inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # input_name -> {source_node_id: data}
    
    def add_expected_input(self, input_name: str, source_node_id: str) -> None:
        """Add an expected input from a source node."""
        if input_name not in self.expected_inputs:
            self.expected_inputs[input_name] = set()
        self.expected_inputs[input_name].add(source_node_id)
        
        if input_name not in self.received_inputs:
            self.received_inputs[input_name] = {}
    
    def receive_input(self, input_name: str, source_node_id: str, data: Any) -> None:
        """Receive input data from a source node."""
        if input_name not in self.received_inputs:
            self.received_inputs[input_name] = {}
        
        self.received_inputs[input_name][source_node_id] = data
        logger.debug(f"Node {self.node_id} received input '{input_name}' from {source_node_id}")
    
    def is_ready(self) -> bool:
        """Check if all expected inputs have been received."""
        for input_name, expected_sources in self.expected_inputs.items():
            received_sources = set(self.received_inputs.get(input_name, {}).keys())
            if not expected_sources.issubset(received_sources):
                return False
        return True
    
    def get_merged_input_data(self) -> Dict[str, Any]:
        """Get merged input data for node execution."""
        merged_data = {}
        
        for input_name, source_data in self.received_inputs.items():
            if len(source_data) == 1:
                # Single input - use data directly
                merged_data[input_name] = list(source_data.values())[0]
            else:
                # Multiple inputs - merge as array or use merge strategy
                merged_data[input_name] = list(source_data.values())
        
        return merged_data
    
    def get_missing_inputs(self) -> Dict[str, Set[str]]:
        """Get inputs that are still missing."""
        missing = {}
        
        for input_name, expected_sources in self.expected_inputs.items():
            received_sources = set(self.received_inputs.get(input_name, {}).keys())
            missing_sources = expected_sources - received_sources
            if missing_sources:
                missing[input_name] = missing_sources
        
        return missing


class EnhancedExecutionResult(ExecutionResult):
    """
    Enhanced execution result with detailed state tracking.
    
    Extends the base ExecutionResult with n8n-inspired detailed tracking
    of node states, connections, and execution flow.
    """
    # Enhanced state tracking
    node_contexts: Dict[str, NodeExecutionContext] = Field(default_factory=dict)
    connections: List[ConnectionData] = Field(default_factory=list)
    waiting_executions: Dict[str, WaitingExecution] = Field(default_factory=dict)
    
    # Execution flow tracking
    execution_batches: List[List[str]] = Field(default_factory=list)
    parallel_execution_count: int = 0
    sequential_execution_count: int = 0
    
    # Performance metrics
    dependency_resolution_time_ms: int = 0
    state_management_overhead_ms: int = 0
    
    def get_node_states_summary(self) -> Dict[str, int]:
        """Get summary of node states."""
        summary = {}
        for state in NodeState:
            summary[state.value] = sum(
                1 for ctx in self.node_contexts.values()
                if ctx.state == state
            )
        return summary
    
    def get_failed_nodes(self) -> List[str]:
        """Get list of failed node IDs."""
        return [
            node_id for node_id, ctx in self.node_contexts.items()
            if ctx.state == NodeState.ERROR
        ]
    
    def get_successful_nodes(self) -> List[str]:
        """Get list of successful node IDs."""
        return [
            node_id for node_id, ctx in self.node_contexts.items()
            if ctx.state == NodeState.SUCCESS
        ]
    
    def get_execution_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of all state transitions."""
        timeline = []
        
        for node_id, ctx in self.node_contexts.items():
            for transition in ctx.state_transitions:
                timeline.append({
                    "timestamp": transition.timestamp,
                    "node_id": node_id,
                    "event_type": "state_transition",
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "reason": transition.reason,
                    "metadata": transition.metadata
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        return timeline
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        base_dict = super().to_dict() if hasattr(super(), 'to_dict') else {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error
        }
        
        # Add enhanced tracking data
        base_dict.update({
            "node_states_summary": self.get_node_states_summary(),
            "failed_nodes": self.get_failed_nodes(),
            "successful_nodes": self.get_successful_nodes(),
            "execution_batches": self.execution_batches,
            "parallel_execution_count": self.parallel_execution_count,
            "sequential_execution_count": self.sequential_execution_count,
            "dependency_resolution_time_ms": self.dependency_resolution_time_ms,
            "state_management_overhead_ms": self.state_management_overhead_ms,
            "node_contexts": {
                node_id: ctx.to_dict()
                for node_id, ctx in self.node_contexts.items()
            },
            "execution_timeline": self.get_execution_timeline()
        })
        
        return base_dict