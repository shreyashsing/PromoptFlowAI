"""
Integration test for LangGraph workflow orchestration system.

This test verifies that the complete workflow orchestration system works
including graph construction, execution, state management, and result collection.
"""
import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.workflow_orchestrator import WorkflowOrchestrator
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, NodePosition
from app.models.execution import ExecutionStatus
from app.models.connector import ConnectorResult
from app.connectors.base import BaseConnector


class MockHTTPConnector(BaseConnector):
    """Mock HTTP connector for testing."""
    
    def _get_category(self) -> str:
        return "http"
    
    def _define_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to request"},
                "method": {"type": "string", "description": "HTTP method", "default": "GET"}
            },
            "required": ["url"]
        }
    
    async def get_auth_requirements(self):
        from app.models.base import AuthType
        from app.models.connector import AuthRequirements
        return AuthRequirements(type=AuthType.NONE)
    
    async def execute(self, parameters: dict, context) -> ConnectorResult:
        """Mock HTTP request execution."""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        url = parameters.get("url", "")
        method = parameters.get("method", "GET")
        
        # Simulate different responses based on URL
        if "error" in url:
            return ConnectorResult(
                success=False,
                data=None,
                error="HTTP 500: Internal Server Error"
            )
        elif "users" in url:
            return ConnectorResult(
                success=True,
                data={
                    "users": [
                        {"id": 1, "name": "John Doe", "email": "john@example.com"},
                        {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
                    ]
                }
            )
        else:
            return ConnectorResult(
                success=True,
                data={"message": f"Success from {method} {url}", "timestamp": datetime.utcnow().isoformat()}
            )


class MockEmailConnector(BaseConnector):
    """Mock email connector for testing."""
    
    def _get_category(self) -> str:
        return "communication"
    
    def _define_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"}
            },
            "required": ["to", "subject", "body"]
        }
    
    async def get_auth_requirements(self):
        from app.models.base import AuthType
        from app.models.connector import AuthRequirements
        return AuthRequirements(type=AuthType.NONE)
    
    async def execute(self, parameters: dict, context) -> ConnectorResult:
        """Mock email sending."""
        await asyncio.sleep(0.05)  # Simulate email sending delay
        
        to = parameters.get("to", "")
        subject = parameters.get("subject", "")
        body = parameters.get("body", "")
        
        if not to or "@" not in to:
            return ConnectorResult(
                success=False,
                data=None,
                error="Invalid email address"
            )
        
        return ConnectorResult(
            success=True,
            data={
                "message_id": f"msg_{uuid4().hex[:8]}",
                "to": to,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent"
            }
        )


async def test_basic_workflow_execution():
    """Test basic workflow execution with two connected nodes."""
    print("Testing basic workflow execution...")
    
    # Create workflow orchestrator
    orchestrator = WorkflowOrchestrator()
    
    # Register mock connectors
    orchestrator.connector_registry.register(MockHTTPConnector)
    orchestrator.connector_registry.register(MockEmailConnector)
    
    # Create a simple workflow
    workflow = WorkflowPlan(
        id=str(uuid4()),
        user_id=str(uuid4()),
        name="Test Integration Workflow",
        description="A test workflow for integration testing",
        nodes=[
            WorkflowNode(
                id="fetch_users",
                connector_name="mockhttp",
                parameters={
                    "url": "https://api.example.com/users",
                    "method": "GET"
                },
                position=NodePosition(x=100, y=100),
                dependencies=[]
            ),
            WorkflowNode(
                id="send_notification",
                connector_name="mockemail",
                parameters={
                    "to": "admin@example.com",
                    "subject": "User Data Retrieved",
                    "body": "Retrieved ${fetch_users.users.0.name} and others"
                },
                position=NodePosition(x=300, y=100),
                dependencies=["fetch_users"]
            )
        ],
        edges=[
            WorkflowEdge(
                id="edge1",
                source="fetch_users",
                target="send_notification"
            )
        ]
    )
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify results
    print(f"Execution Status: {result.status}")
    print(f"Total Duration: {result.total_duration_ms}ms")
    print(f"Node Results: {len(result.node_results)}")
    
    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.node_results) == 2
    assert result.error is None
    
    # Check individual node results
    fetch_result = next((nr for nr in result.node_results if nr.node_id == "fetch_users"), None)
    email_result = next((nr for nr in result.node_results if nr.node_id == "send_notification"), None)
    
    assert fetch_result is not None
    assert fetch_result.status == ExecutionStatus.COMPLETED
    assert "users" in fetch_result.result
    
    assert email_result is not None
    assert email_result.status == ExecutionStatus.COMPLETED
    assert "message_id" in email_result.result
    
    print("✓ Basic workflow execution test passed!")
    return result


async def test_workflow_with_error_handling():
    """Test workflow execution with error handling."""
    print("\nTesting workflow with error handling...")
    
    orchestrator = WorkflowOrchestrator()
    orchestrator.connector_registry.register(MockHTTPConnector)
    orchestrator.connector_registry.register(MockEmailConnector)
    
    # Create workflow with an error-prone node
    workflow = WorkflowPlan(
        id=str(uuid4()),
        user_id=str(uuid4()),
        name="Error Test Workflow",
        description="Workflow to test error handling",
        nodes=[
            WorkflowNode(
                id="error_node",
                connector_name="mockhttp",
                parameters={
                    "url": "https://api.example.com/error",
                    "method": "GET"
                },
                position=NodePosition(x=100, y=100),
                dependencies=[]
            ),
            WorkflowNode(
                id="recovery_node",
                connector_name="mockemail",
                parameters={
                    "to": "admin@example.com",
                    "subject": "Error Occurred",
                    "body": "An error occurred in the workflow"
                },
                position=NodePosition(x=300, y=100),
                dependencies=["error_node"]
            )
        ],
        edges=[
            WorkflowEdge(
                id="edge1",
                source="error_node",
                target="recovery_node"
            )
        ]
    )
    
    result = await orchestrator.execute_workflow(workflow)
    
    print(f"Execution Status: {result.status}")
    print(f"Error: {result.error}")
    
    # Should fail due to error in first node
    assert result.status == ExecutionStatus.FAILED
    assert result.error is not None
    
    # Check that error node failed
    error_node_result = next((nr for nr in result.node_results if nr.node_id == "error_node"), None)
    assert error_node_result is not None
    assert error_node_result.status == ExecutionStatus.FAILED
    assert "500" in error_node_result.error
    
    print("✓ Error handling test passed!")
    return result


async def test_parameter_resolution():
    """Test parameter resolution between nodes."""
    print("\nTesting parameter resolution...")
    
    orchestrator = WorkflowOrchestrator()
    orchestrator.connector_registry.register(MockHTTPConnector)
    orchestrator.connector_registry.register(MockEmailConnector)
    
    workflow = WorkflowPlan(
        id=str(uuid4()),
        user_id=str(uuid4()),
        name="Parameter Resolution Test",
        description="Test parameter resolution between nodes",
        nodes=[
            WorkflowNode(
                id="get_data",
                connector_name="mockhttp",
                parameters={
                    "url": "https://api.example.com/users",
                    "method": "GET"
                },
                position=NodePosition(x=100, y=100),
                dependencies=[]
            ),
            WorkflowNode(
                id="send_email",
                connector_name="mockemail",
                parameters={
                    "to": "${get_data.users.0.email}",
                    "subject": "Hello ${get_data.users.0.name}",
                    "body": "We found ${get_data.users.length} users in the system"
                },
                position=NodePosition(x=300, y=100),
                dependencies=["get_data"]
            )
        ],
        edges=[
            WorkflowEdge(
                id="edge1",
                source="get_data",
                target="send_email"
            )
        ]
    )
    
    result = await orchestrator.execute_workflow(workflow)
    
    print(f"Execution Status: {result.status}")
    
    assert result.status == ExecutionStatus.COMPLETED
    
    # Check parameter resolution
    email_result = next((nr for nr in result.node_results if nr.node_id == "send_email"), None)
    assert email_result is not None
    assert email_result.status == ExecutionStatus.COMPLETED
    
    # The email should have been sent to john@example.com (first user)
    assert email_result.result["to"] == "john@example.com"
    
    print("✓ Parameter resolution test passed!")
    return result


async def main():
    """Run all integration tests."""
    print("Starting LangGraph Workflow Orchestration Integration Tests")
    print("=" * 60)
    
    try:
        # Run tests
        await test_basic_workflow_execution()
        await test_workflow_with_error_handling()
        await test_parameter_resolution()
        
        print("\n" + "=" * 60)
        print("✅ All integration tests passed!")
        print("LangGraph workflow orchestration system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)