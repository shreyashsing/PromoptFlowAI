"""
Tests for LangGraph workflow orchestration system.

This module tests the workflow execution engine including:
- Workflow graph construction
- Node execution with state management
- Error handling and recovery
- Trigger system integration
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.services.workflow_orchestrator import WorkflowOrchestrator, WorkflowState
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, NodePosition
from app.models.execution import ExecutionResult, ExecutionStatus
from app.models.connector import ConnectorResult


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    return WorkflowPlan(
        id=str(uuid4()),
        user_id=str(uuid4()),
        name="Test Workflow",
        description="A test workflow for orchestration",
        nodes=[
            WorkflowNode(
                id="node1",
                connector_name="http_connector",
                parameters={"url": "https://api.example.com/data", "method": "GET"},
                position=NodePosition(x=100, y=100),
                dependencies=[]
            ),
            WorkflowNode(
                id="node2",
                connector_name="gmail_connector",
                parameters={"to": "test@example.com", "subject": "Test", "body": "${node1.data}"},
                position=NodePosition(x=200, y=100),
                dependencies=["node1"]
            )
        ],
        edges=[
            WorkflowEdge(
                id="edge1",
                source="node1",
                target="node2"
            )
        ]
    )


@pytest.fixture
def mock_connector():
    """Create a mock connector for testing."""
    connector = Mock()
    connector.execute_with_retry = AsyncMock(return_value=ConnectorResult(
        success=True,
        data={"message": "Test data"},
        error=None
    ))
    return connector


@pytest.fixture
def orchestrator():
    """Create a workflow orchestrator instance."""
    return WorkflowOrchestrator()


class TestWorkflowOrchestrator:
    """Test cases for WorkflowOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_workflow_state_initialization(self, orchestrator, sample_workflow):
        """Test that workflow state is properly initialized."""
        execution_id = str(uuid4())
        
        # Mock the connector registry
        with patch.object(orchestrator.connector_registry, 'get_connector', return_value=None):
            with patch.object(orchestrator, '_store_execution_result', return_value=None):
                # This will fail due to missing connector, but we can check state initialization
                result = await orchestrator.execute_workflow(sample_workflow)
                
                assert result.workflow_id == sample_workflow.id
                assert result.user_id == sample_workflow.user_id
                assert result.status == ExecutionStatus.FAILED  # Due to missing connector
    
    @pytest.mark.asyncio
    async def test_successful_workflow_execution(self, orchestrator, sample_workflow, mock_connector):
        """Test successful execution of a complete workflow."""
        # Mock the connector registry to return our mock connector
        with patch.object(orchestrator.connector_registry, 'get_connector', return_value=mock_connector):
            with patch.object(orchestrator, '_store_execution_result', return_value=None):
                result = await orchestrator.execute_workflow(sample_workflow)
                
                assert result.status == ExecutionStatus.COMPLETED
                assert len(result.node_results) == 2
                assert result.error is None
                
                # Check that both nodes were executed
                node_ids = [nr.node_id for nr in result.node_results]
                assert "node1" in node_ids
                assert "node2" in node_ids
    
    @pytest.mark.asyncio
    async def test_node_parameter_resolution(self, orchestrator):
        """Test that node parameters are correctly resolved with previous results."""
        previous_results = {
            "node1": {
                "data": {"user": {"name": "John", "email": "john@example.com"}},
                "success": True
            }
        }
        
        parameters = {
            "to": "${node1.user.email}",
            "subject": "Hello ${node1.user.name}",
            "static_value": "unchanged"
        }
        
        resolved = await orchestrator._resolve_node_parameters(parameters, previous_results)
        
        assert resolved["to"] == "john@example.com"
        assert resolved["subject"] == "Hello John"
        assert resolved["static_value"] == "unchanged"
    
    @pytest.mark.asyncio
    async def test_nested_value_extraction(self, orchestrator):
        """Test extraction of nested values from data structures."""
        data = {
            "user": {
                "profile": {
                    "name": "Alice",
                    "contacts": ["alice@example.com", "alice.work@company.com"]
                }
            },
            "items": [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        }
        
        # Test nested object access
        assert orchestrator._get_nested_value(data, "user.profile.name") == "Alice"
        
        # Test array access
        assert orchestrator._get_nested_value(data, "user.profile.contacts.0") == "alice@example.com"
        assert orchestrator._get_nested_value(data, "items.1.name") == "Item 2"
        
        # Test non-existent paths
        assert orchestrator._get_nested_value(data, "user.nonexistent") is None
        assert orchestrator._get_nested_value(data, "items.10.name") is None
    
    @pytest.mark.asyncio
    async def test_workflow_with_conditional_edges(self, orchestrator):
        """Test workflow execution with conditional edges."""
        workflow = WorkflowPlan(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Conditional Workflow",
            description="Workflow with conditional logic",
            nodes=[
                WorkflowNode(
                    id="check_node",
                    connector_name="http_connector",
                    parameters={"url": "https://api.example.com/check"},
                    position=NodePosition(x=100, y=100),
                    dependencies=[]
                ),
                WorkflowNode(
                    id="success_node",
                    connector_name="gmail_connector",
                    parameters={"subject": "Success"},
                    position=NodePosition(x=200, y=50),
                    dependencies=["check_node"]
                ),
                WorkflowNode(
                    id="failure_node",
                    connector_name="gmail_connector",
                    parameters={"subject": "Failure"},
                    position=NodePosition(x=200, y=150),
                    dependencies=["check_node"]
                )
            ],
            edges=[
                WorkflowEdge(
                    id="success_edge",
                    source="check_node",
                    target="success_node",
                    condition="check_node.success == true"
                ),
                WorkflowEdge(
                    id="failure_edge",
                    source="check_node",
                    target="failure_node",
                    condition="check_node.success == false"
                )
            ]
        )
        
        # Mock connector that returns success
        success_connector = Mock()
        success_connector.execute_with_retry = AsyncMock(return_value=ConnectorResult(
            success=True,
            data={"success": True},
            error=None
        ))
        
        with patch.object(orchestrator.connector_registry, 'get_connector', return_value=success_connector):
            with patch.object(orchestrator, '_store_execution_result', return_value=None):
                result = await orchestrator.execute_workflow(workflow)
                
                # Should execute check_node and success_node, but not failure_node
                assert result.status == ExecutionStatus.COMPLETED
                node_ids = [nr.node_id for nr in result.node_results]
                assert "check_node" in node_ids
                # Note: Conditional edge logic would need to be fully implemented in the orchestrator
    
    @pytest.mark.asyncio
    async def test_error_handling_in_node_execution(self, orchestrator, sample_workflow):
        """Test error handling when a node fails."""
        # Mock connector that fails
        failing_connector = Mock()
        failing_connector.execute_with_retry = AsyncMock(return_value=ConnectorResult(
            success=False,
            data=None,
            error="Connection timeout"
        ))
        
        with patch.object(orchestrator.connector_registry, 'get_connector', return_value=failing_connector):
            with patch.object(orchestrator, '_store_execution_result', return_value=None):
                result = await orchestrator.execute_workflow(sample_workflow)
                
                assert result.status == ExecutionStatus.FAILED
                assert result.error is not None
                
                # Check that node results contain error information
                failed_nodes = [nr for nr in result.node_results if nr.status == ExecutionStatus.FAILED]
                assert len(failed_nodes) > 0
                assert failed_nodes[0].error == "Connection timeout"
    
    @pytest.mark.asyncio
    async def test_execution_status_tracking(self, orchestrator, sample_workflow, mock_connector):
        """Test that execution status is properly tracked."""
        with patch.object(orchestrator.connector_registry, 'get_connector', return_value=mock_connector):
            with patch.object(orchestrator, '_store_execution_result', return_value=None):
                result = await orchestrator.execute_workflow(sample_workflow)
                
                # Check timing information
                assert result.started_at is not None
                assert result.completed_at is not None
                assert result.total_duration_ms is not None
                assert result.total_duration_ms > 0
                
                # Check node timing
                for node_result in result.node_results:
                    assert node_result.started_at is not None
                    assert node_result.completed_at is not None
                    assert node_result.duration_ms is not None
                    assert node_result.duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, orchestrator, sample_workflow):
        """Test workflow execution cancellation."""
        execution_id = str(uuid4())
        
        # Create a mock execution result
        execution_result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=sample_workflow.id,
            user_id=sample_workflow.user_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # Add to active executions
        orchestrator.active_executions[execution_id] = execution_result
        
        with patch.object(orchestrator, '_store_execution_result', return_value=None):
            # Cancel the execution
            success = await orchestrator.cancel_execution(execution_id, sample_workflow.user_id)
            
            assert success is True
            assert execution_result.status == ExecutionStatus.CANCELLED
            assert execution_result.error == "Execution cancelled by user"
            assert execution_id not in orchestrator.active_executions
    
    @pytest.mark.asyncio
    async def test_execution_status_retrieval(self, orchestrator):
        """Test retrieval of execution status."""
        execution_id = str(uuid4())
        workflow_id = str(uuid4())
        user_id = str(uuid4())
        
        # Mock database response
        mock_db_data = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "user_id": user_id,
            "status": "completed",
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "duration_ms": 5000,
            "error_message": None,
            "execution_log": [
                {
                    "node_id": "node1",
                    "connector_name": "http_connector",
                    "status": "completed",
                    "started_at": datetime.utcnow().isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "duration_ms": 2000
                }
            ],
            "result": {
                "node_results": {
                    "node1": {
                        "data": {"message": "success"},
                        "status": "completed"
                    }
                }
            }
        }
        
        with patch('app.core.database.get_supabase_client') as mock_supabase:
            mock_client = Mock()
            mock_table = Mock()
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = Mock(data=[mock_db_data])
            mock_supabase.return_value = mock_client
            
            result = await orchestrator.get_execution_status(execution_id)
            
            assert result is not None
            assert result.execution_id == execution_id
            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.node_results) == 1
            assert result.node_results[0].node_id == "node1"


class TestWorkflowStateManagement:
    """Test cases for workflow state management."""
    
    def test_workflow_state_structure(self):
        """Test that WorkflowState has the correct structure."""
        state = WorkflowState(
            workflow_id="test-workflow",
            user_id="test-user",
            execution_id="test-execution",
            current_node=None,
            node_results={},
            errors=[],
            status=ExecutionStatus.PENDING,
            metadata={}
        )
        
        assert state["workflow_id"] == "test-workflow"
        assert state["user_id"] == "test-user"
        assert state["execution_id"] == "test-execution"
        assert state["current_node"] is None
        assert state["node_results"] == {}
        assert state["errors"] == []
        assert state["status"] == ExecutionStatus.PENDING
        assert state["metadata"] == {}
    
    def test_state_updates(self):
        """Test that workflow state can be updated correctly."""
        state = WorkflowState(
            workflow_id="test-workflow",
            user_id="test-user",
            execution_id="test-execution",
            current_node=None,
            node_results={},
            errors=[],
            status=ExecutionStatus.PENDING,
            metadata={}
        )
        
        # Update state
        state["current_node"] = "node1"
        state["status"] = ExecutionStatus.RUNNING
        state["node_results"]["node1"] = {"data": "test", "success": True}
        state["errors"].append("Test error")
        
        assert state["current_node"] == "node1"
        assert state["status"] == ExecutionStatus.RUNNING
        assert state["node_results"]["node1"]["data"] == "test"
        assert "Test error" in state["errors"]


if __name__ == "__main__":
    pytest.main([__file__])