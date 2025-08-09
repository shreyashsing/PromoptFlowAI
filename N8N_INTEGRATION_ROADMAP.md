# n8n Integration Roadmap for PromptFlow AI

## Overview

This roadmap provides a step-by-step plan to integrate n8n's proven scalability patterns into your PromptFlow AI workflow execution system while maintaining your existing strengths.

## Phase 1: Foundation Enhancement (Week 1-2)

### 1.1 Enhanced State Management Implementation

**Goal**: Implement n8n-inspired comprehensive state tracking

**Tasks**:
- [ ] Create `NodeState` enum with detailed states
- [ ] Implement `NodeExecutionContext` dataclass
- [ ] Add state transition logging
- [ ] Update database schema for state persistence

**Code Changes**:
```python
# backend/app/models/execution.py
from enum import Enum
from dataclasses import dataclass, field
from typing import Set, Dict, Any, Optional
from datetime import datetime

class NodeState(Enum):
    WAITING = "waiting"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"

@dataclass
class NodeExecutionContext:
    node_id: str
    state: NodeState = NodeState.WAITING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    waiting_for: Set[str] = field(default_factory=set)
```

**Database Migration**:
```sql
-- Add to workflow_executions table
ALTER TABLE workflow_executions ADD COLUMN node_states JSONB;
ALTER TABLE workflow_executions ADD COLUMN state_transitions JSONB[];
ALTER TABLE workflow_executions ADD COLUMN retry_attempts JSONB;

-- Create indexes for performance
CREATE INDEX idx_workflow_executions_node_states ON workflow_executions USING GIN (node_states);
```

### 1.2 WorkflowGraph Implementation

**Goal**: Create n8n-inspired workflow graph with sophisticated dependency management

**Tasks**:
- [ ] Implement `WorkflowGraph` class
- [ ] Add connection-based data flow
- [ ] Implement dependency resolution algorithms
- [ ] Add cycle detection

**Code Changes**:
```python
# backend/app/services/workflow_graph.py
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from app.models.base import WorkflowNode, WorkflowEdge
from app.models.execution import NodeExecutionContext, NodeState

@dataclass
class ConnectionData:
    from_node: str
    to_node: str
    from_output: str = "main"
    to_input: str = "main"
    data: Any = None

class WorkflowGraph:
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.node_contexts: Dict[str, NodeExecutionContext] = {}
        self.connections: List[ConnectionData] = []
        self.waiting_execution: Dict[str, Dict[str, Any]] = {}
    
    def add_node(self, node: WorkflowNode) -> None:
        """Add node with dependency tracking."""
        self.nodes[node.id] = node
        self.node_contexts[node.id] = NodeExecutionContext(
            node_id=node.id,
            dependencies=set(node.dependencies) if node.dependencies else set()
        )
    
    def add_connection(self, from_node: str, to_node: str, 
                      from_output: str = "main", to_input: str = "main") -> None:
        """Add connection with automatic dependency tracking."""
        connection = ConnectionData(from_node, to_node, from_output, to_input)
        self.connections.append(connection)
        
        if to_node in self.node_contexts:
            self.node_contexts[to_node].dependencies.add(from_node)
        if from_node in self.node_contexts:
            self.node_contexts[from_node].dependents.add(to_node)
    
    def get_ready_nodes(self) -> List[str]:
        """Get nodes ready for execution (n8n-inspired)."""
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
            
            if dependencies_satisfied:
                ready_nodes.append(node_id)
        
        return ready_nodes
    
    def prepare_node_input(self, node_id: str) -> Dict[str, Any]:
        """Prepare input data from connected nodes (n8n-inspired)."""
        input_data = {}
        
        incoming_connections = [
            conn for conn in self.connections 
            if conn.to_node == node_id
        ]
        
        for connection in incoming_connections:
            from_context = self.node_contexts.get(connection.from_node)
            if from_context and from_context.state == NodeState.SUCCESS:
                output_data = from_context.output_data.get(connection.from_output)
                if output_data is not None:
                    input_data[connection.to_input] = output_data
        
        return input_data
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies."""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node_id: str, path: List[str]) -> bool:
            if node_id in rec_stack:
                cycle_start = path.index(node_id)
                cycles.append(path[cycle_start:] + [node_id])
                return True
            
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            context = self.node_contexts.get(node_id)
            if context:
                for dependent in context.dependents:
                    if dfs(dependent, path + [node_id]):
                        return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.node_contexts:
            if node_id not in visited:
                dfs(node_id, [])
        
        return cycles
```

### 1.3 Advanced Error Handling

**Goal**: Implement n8n-style retry logic with exponential backoff

**Tasks**:
- [ ] Create configurable retry policies
- [ ] Implement exponential backoff
- [ ] Add error classification
- [ ] Create retry attempt logging

**Code Changes**:
```python
# backend/app/services/retry_manager.py
import asyncio
import logging
from typing import Optional, Callable, Any, Type
from dataclasses import dataclass
from enum import Enum

class ErrorType(Enum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    RATE_LIMITED = "rate_limited"

@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

class RetryManager:
    def __init__(self, policy: RetryPolicy = None):
        self.policy = policy or RetryPolicy()
        self.logger = logging.getLogger(__name__)
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        error_classifier: Optional[Callable[[Exception], ErrorType]] = None,
        **kwargs
    ) -> Any:
        """Execute function with n8n-inspired retry logic."""
        
        for attempt in range(self.policy.max_retries + 1):
            try:
                return await func(*args, **kwargs)
                
            except Exception as e:
                error_type = self._classify_error(e, error_classifier)
                
                if error_type == ErrorType.NON_RETRYABLE:
                    self.logger.error(f"Non-retryable error: {str(e)}")
                    raise
                
                if attempt >= self.policy.max_retries:
                    self.logger.error(f"Max retries ({self.policy.max_retries}) exceeded: {str(e)}")
                    raise
                
                delay = self._calculate_delay(attempt, error_type)
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s")
                
                await asyncio.sleep(delay)
        
        raise RuntimeError("Retry logic error - should not reach here")
    
    def _classify_error(self, error: Exception, classifier: Optional[Callable] = None) -> ErrorType:
        """Classify error for retry decision."""
        if classifier:
            return classifier(error)
        
        # Default classification
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorType.RETRYABLE
        elif "rate limit" in str(error).lower():
            return ErrorType.RATE_LIMITED
        else:
            return ErrorType.NON_RETRYABLE
    
    def _calculate_delay(self, attempt: int, error_type: ErrorType) -> float:
        """Calculate delay with exponential backoff."""
        if error_type == ErrorType.RATE_LIMITED:
            # Longer delay for rate limiting
            base_delay = self.policy.base_delay * 5
        else:
            base_delay = self.policy.base_delay
        
        delay = min(
            base_delay * (self.policy.exponential_base ** attempt),
            self.policy.max_delay
        )
        
        # Add jitter to prevent thundering herd
        if self.policy.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
```

## Phase 2: Core Integration (Week 3-4)

### 2.1 Enhanced Orchestrator Integration

**Goal**: Integrate enhanced orchestrator with existing system

**Tasks**:
- [ ] Update main orchestrator to use enhanced version
- [ ] Implement intelligent routing logic
- [ ] Add performance monitoring
- [ ] Create fallback mechanisms

**Code Changes**:
```python
# backend/app/services/workflow_orchestrator.py (Updated)
from app.services.enhanced_workflow_orchestrator import EnhancedWorkflowOrchestrator
from app.services.workflow_graph import WorkflowGraph
from app.services.retry_manager import RetryManager, RetryPolicy

class WorkflowOrchestrator:
    def __init__(self):
        self.enhanced_orchestrator = EnhancedWorkflowOrchestrator()
        self.parallel_executor = ParallelWorkflowExecutor()
        self.retry_manager = RetryManager()
        
    async def execute_workflow(self, workflow: WorkflowPlan) -> ExecutionResult:
        """Enhanced workflow execution with intelligent routing."""
        
        # Analyze workflow complexity
        complexity_score = self._analyze_workflow_complexity(workflow)
        
        try:
            if complexity_score >= 0.7:  # High complexity
                logger.info(f"Using enhanced orchestrator for complex workflow {workflow.id}")
                return await self.enhanced_orchestrator.execute_workflow(workflow)
                
            elif self.parallel_executor.should_use_parallel_execution(workflow):
                logger.info(f"Using parallel executor for workflow {workflow.id}")
                return await self.parallel_executor.execute_workflow(workflow)
                
            else:
                logger.info(f"Using LangGraph for simple workflow {workflow.id}")
                return await self._execute_with_langgraph(workflow)
                
        except Exception as e:
            # Fallback mechanism
            logger.error(f"Primary execution failed: {str(e)}. Attempting fallback.")
            return await self._execute_fallback(workflow, e)
    
    def _analyze_workflow_complexity(self, workflow: WorkflowPlan) -> float:
        """Analyze workflow complexity to determine best execution engine."""
        
        node_count = len(workflow.nodes)
        edge_count = len(workflow.edges)
        
        # Calculate complexity factors
        size_factor = min(node_count / 10.0, 1.0)  # Normalize to 0-1
        connectivity_factor = min(edge_count / (node_count * 2), 1.0) if node_count > 0 else 0
        
        # Check for complex patterns
        multi_input_nodes = sum(1 for node in workflow.nodes if len(node.dependencies or []) > 2)
        multi_input_factor = min(multi_input_nodes / node_count, 1.0) if node_count > 0 else 0
        
        # Check for cycles (would require enhanced orchestrator)
        graph = WorkflowGraph()
        for node in workflow.nodes:
            graph.add_node(node)
        for edge in workflow.edges:
            graph.add_connection(edge.source_node_id, edge.target_node_id)
        
        has_cycles = len(graph.detect_cycles()) > 0
        cycle_factor = 1.0 if has_cycles else 0.0
        
        # Weighted complexity score
        complexity_score = (
            size_factor * 0.3 +
            connectivity_factor * 0.3 +
            multi_input_factor * 0.2 +
            cycle_factor * 0.2
        )
        
        logger.info(f"Workflow complexity analysis: "
                   f"nodes={node_count}, edges={edge_count}, "
                   f"multi_input={multi_input_nodes}, cycles={has_cycles}, "
                   f"score={complexity_score:.2f}")
        
        return complexity_score
    
    async def _execute_fallback(self, workflow: WorkflowPlan, original_error: Exception) -> ExecutionResult:
        """Fallback execution strategy."""
        logger.info("Attempting fallback to parallel executor")
        
        try:
            return await self.parallel_executor.execute_workflow(workflow)
        except Exception as fallback_error:
            logger.error(f"Fallback execution also failed: {str(fallback_error)}")
            
            # Create failed execution result
            execution_result = ExecutionResult(
                execution_id=str(uuid4()),
                workflow_id=workflow.id,
                user_id=workflow.user_id,
                status=ExecutionStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error=f"Primary: {str(original_error)}; Fallback: {str(fallback_error)}"
            )
            
            return execution_result
```

### 2.2 API Integration Updates

**Goal**: Update APIs to support enhanced orchestrator features

**Tasks**:
- [ ] Add execution engine selection endpoint
- [ ] Update execution status API with detailed node states
- [ ] Add retry configuration endpoints
- [ ] Implement real-time execution monitoring

**Code Changes**:
```python
# backend/app/api/workflows.py (Enhanced)
from app.services.retry_manager import RetryPolicy
from app.models.execution import NodeState

@router.post("/execute")
async def execute_workflow_enhanced(
    request: ExecuteWorkflowRequest,
    execution_config: Optional[ExecutionConfig] = None,
    current_user: dict = Depends(get_current_user)
):
    """Enhanced workflow execution with configuration options."""
    
    try:
        # Create workflow plan with enhanced configuration
        workflow_plan = WorkflowPlan(
            id=request.workflow_id,
            user_id=current_user["id"],
            nodes=request.nodes,
            edges=request.edges,
            execution_config=execution_config
        )
        
        # Execute with enhanced orchestrator
        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.execute_workflow(workflow_plan)
        
        return {
            "success": True,
            "execution_id": result.execution_id,
            "status": result.status.value,
            "execution_engine": result.metadata.get("execution_engine", "unknown"),
            "complexity_score": result.metadata.get("complexity_score", 0.0),
            "duration_ms": result.total_duration_ms,
            "node_results": [
                {
                    "node_id": nr.node_id,
                    "status": nr.status.value,
                    "duration_ms": nr.duration_ms,
                    "retry_count": nr.metadata.get("retry_count", 0),
                    "error": nr.error
                }
                for nr in result.node_results
            ]
        }
        
    except Exception as e:
        logger.error(f"Enhanced workflow execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/execution/{execution_id}/status")
async def get_execution_status_detailed(
    execution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed execution status with node states."""
    
    try:
        supabase = get_supabase_client()
        
        # Get execution details
        result = await supabase.table("workflow_executions")\
            .select("*")\
            .eq("execution_id", execution_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        execution = result.data[0]
        
        return {
            "execution_id": execution_id,
            "status": execution["status"],
            "execution_engine": execution.get("execution_engine", "unknown"),
            "node_states": execution.get("node_states", {}),
            "state_transitions": execution.get("state_transitions", []),
            "retry_attempts": execution.get("retry_attempts", {}),
            "started_at": execution["started_at"],
            "completed_at": execution.get("completed_at"),
            "duration_ms": execution.get("total_duration_ms", 0),
            "error": execution.get("error")
        }
        
    except Exception as e:
        logger.error(f"Failed to get execution status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execution/{execution_id}/retry")
async def retry_failed_nodes(
    execution_id: str,
    retry_config: Optional[RetryPolicy] = None,
    current_user: dict = Depends(get_current_user)
):
    """Retry failed nodes in an execution."""
    
    try:
        # Get original execution
        supabase = get_supabase_client()
        result = await supabase.table("workflow_executions")\
            .select("*")\
            .eq("execution_id", execution_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        execution = result.data[0]
        
        # Find failed nodes
        node_states = execution.get("node_states", {})
        failed_nodes = [
            node_id for node_id, state in node_states.items()
            if state == NodeState.ERROR.value
        ]
        
        if not failed_nodes:
            return {"message": "No failed nodes to retry"}
        
        # Create retry execution
        orchestrator = WorkflowOrchestrator()
        # Implementation would create a partial workflow with only failed nodes
        
        return {
            "message": f"Retrying {len(failed_nodes)} failed nodes",
            "failed_nodes": failed_nodes,
            "new_execution_id": "retry_" + execution_id
        }
        
    except Exception as e:
        logger.error(f"Failed to retry execution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

## Phase 3: Advanced Features (Week 5-6)

### 3.1 Resource Management

**Goal**: Implement n8n-style resource management and cleanup

**Tasks**:
- [ ] Create resource manager with semaphores
- [ ] Implement memory monitoring
- [ ] Add cleanup function registration
- [ ] Create resource usage metrics

### 3.2 Streaming Support

**Goal**: Add real-time data streaming capabilities

**Tasks**:
- [ ] Implement WebSocket-based streaming
- [ ] Add chunk-based data processing
- [ ] Create streaming API endpoints
- [ ] Add real-time execution monitoring

### 3.3 Performance Monitoring

**Goal**: Add comprehensive performance monitoring

**Tasks**:
- [ ] Create execution metrics collection
- [ ] Implement performance dashboards
- [ ] Add alerting for performance issues
- [ ] Create optimization recommendations

## Testing Strategy

### Unit Tests
```python
# tests/test_enhanced_orchestrator.py
import pytest
from app.services.enhanced_workflow_orchestrator import EnhancedWorkflowOrchestrator
from app.services.workflow_graph import WorkflowGraph
from app.models.execution import NodeState

@pytest.mark.asyncio
async def test_workflow_graph_dependency_resolution():
    graph = WorkflowGraph()
    
    # Create test nodes
    node1 = create_test_node("node1", [])
    node2 = create_test_node("node2", ["node1"])
    node3 = create_test_node("node3", ["node1"])
    node4 = create_test_node("node4", ["node2", "node3"])
    
    # Add to graph
    for node in [node1, node2, node3, node4]:
        graph.add_node(node)
    
    # Test ready nodes
    ready_nodes = graph.get_ready_nodes()
    assert ready_nodes == ["node1"]
    
    # Mark node1 as complete
    graph.node_contexts["node1"].state = NodeState.SUCCESS
    ready_nodes = graph.get_ready_nodes()
    assert set(ready_nodes) == {"node2", "node3"}
    
    # Mark node2 and node3 as complete
    graph.node_contexts["node2"].state = NodeState.SUCCESS
    graph.node_contexts["node3"].state = NodeState.SUCCESS
    ready_nodes = graph.get_ready_nodes()
    assert ready_nodes == ["node4"]

@pytest.mark.asyncio
async def test_enhanced_orchestrator_execution():
    orchestrator = EnhancedWorkflowOrchestrator()
    
    # Create test workflow
    workflow = create_test_workflow_with_dependencies()
    
    # Execute
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify results
    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_results) == len(workflow.nodes)
    assert all(nr.status == ExecutionStatus.COMPLETED for nr in result.node_results)

@pytest.mark.asyncio
async def test_retry_manager():
    from app.services.retry_manager import RetryManager, RetryPolicy
    
    retry_manager = RetryManager(RetryPolicy(max_retries=3))
    
    call_count = 0
    async def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"
    
    result = await retry_manager.execute_with_retry(failing_function)
    assert result == "success"
    assert call_count == 3
```

### Integration Tests
```python
# tests/test_integration_enhanced.py
@pytest.mark.asyncio
async def test_end_to_end_enhanced_execution():
    """Test complete workflow execution with real connectors."""
    
    # Create workflow with Gmail and Google Sheets
    workflow = create_gmail_sheets_workflow()
    
    # Execute with enhanced orchestrator
    orchestrator = WorkflowOrchestrator()
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify execution
    assert result.status == ExecutionStatus.COMPLETED
    assert result.metadata["execution_engine"] == "enhanced"
    
    # Verify node states were tracked
    assert "node_states" in result.metadata
    assert all(
        state == NodeState.SUCCESS.value 
        for state in result.metadata["node_states"].values()
    )

@pytest.mark.asyncio
async def test_fallback_mechanism():
    """Test fallback to parallel executor when enhanced fails."""
    
    # Create workflow that would cause enhanced orchestrator to fail
    workflow = create_problematic_workflow()
    
    orchestrator = WorkflowOrchestrator()
    result = await orchestrator.execute_workflow(workflow)
    
    # Should fallback and still complete
    assert result.status == ExecutionStatus.COMPLETED
    assert result.metadata["execution_engine"] == "parallel"
```

## Success Metrics

### Performance Metrics
- **Execution Time**: 25% improvement for complex workflows
- **Error Recovery**: 90% reduction in permanent failures
- **Resource Usage**: 30% better memory utilization
- **Throughput**: 40% increase in concurrent workflow capacity

### Quality Metrics
- **Test Coverage**: >95% for enhanced orchestrator components
- **Error Rate**: <1% for production workflows
- **Retry Success Rate**: >80% for retryable errors
- **Monitoring Coverage**: 100% of execution paths

### User Experience Metrics
- **Workflow Success Rate**: >99% for properly configured workflows
- **Average Resolution Time**: <2 minutes for failed workflows
- **User Satisfaction**: >4.5/5 for workflow execution reliability

## Risk Mitigation

### Technical Risks
1. **Performance Regression**: Comprehensive benchmarking before deployment
2. **Memory Leaks**: Extensive load testing with memory profiling
3. **Compatibility Issues**: Gradual rollout with feature flags

### Operational Risks
1. **Deployment Issues**: Blue-green deployment strategy
2. **Monitoring Gaps**: Comprehensive alerting and dashboards
3. **Rollback Complexity**: Automated rollback procedures

## Conclusion

This roadmap provides a structured approach to integrating n8n's proven patterns into your PromptFlow AI system. The phased approach ensures minimal risk while maximizing the benefits of enhanced scalability, reliability, and maintainability.

**Expected Outcomes**:
- 🚀 **Enhanced Performance**: Better handling of complex workflows
- 🛡️ **Improved Reliability**: Advanced error handling and retry logic
- 📊 **Better Observability**: Comprehensive state tracking and monitoring
- 🔧 **Easier Maintenance**: Cleaner architecture with better separation of concerns

By following this roadmap, you'll transform your workflow execution system into an enterprise-grade platform that combines your existing strengths with n8n's battle-tested scalability patterns.