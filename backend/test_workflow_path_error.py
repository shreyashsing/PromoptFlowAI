#!/usr/bin/env python3
"""
Test script to reproduce and fix the "Already found path" error in workflow execution.
"""
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from app.models.base import WorkflowPlan, WorkflowNode, NodePosition
from app.services.workflow_orchestrator import WorkflowOrchestrator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_workflow_path_error():
    """Test the workflow execution that's causing the path error."""
    
    # Create a test workflow similar to the one that's failing
    workflow = WorkflowPlan(
        id="test-workflow-id",
        user_id="test-user-id",
        name="Test AI News Workflow",
        description="Test workflow to reproduce path error",
        nodes=[
            WorkflowNode(
                id="perplexity_search",
                connector_name="perplexity_search",
                parameters={
                    "action": "search",
                    "query": "test query",
                    "model": "sonar"
                },
                position=NodePosition(x=100, y=100),
                dependencies=[]
            ),
            WorkflowNode(
                id="google_sheets",
                connector_name="google_sheets",
                parameters={
                    "action": "append",
                    "spreadsheet_id": "test_sheet_id",
                    "values": [["{{perplexity_search.result}}"]]
                },
                position=NodePosition(x=200, y=200),
                dependencies=["perplexity_search"]
            ),
            WorkflowNode(
                id="text_summarizer",
                connector_name="text_summarizer",
                parameters={
                    "text": "{{perplexity_search.result}}",
                    "style": "concise"
                },
                position=NodePosition(x=200, y=300),
                dependencies=["perplexity_search"]
            ),
            WorkflowNode(
                id="gmail_connector",
                connector_name="gmail_connector",
                parameters={
                    "action": "send",
                    "to": "test@example.com",
                    "subject": "Test",
                    "body": "{{text_summarizer.result}}"
                },
                position=NodePosition(x=300, y=400),
                dependencies=["text_summarizer"]
            )
        ],
        edges=[],  # Let dependencies handle the edges
        triggers=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create orchestrator and try to build the graph
    orchestrator = WorkflowOrchestrator()
    
    try:
        logger.info("Testing parallel execution engine...")
        
        # Test the parallel executor directly
        from app.services.parallel_workflow_executor import ParallelWorkflowExecutor
        parallel_executor = ParallelWorkflowExecutor()
        
        # Check if workflow should use parallel execution
        should_use_parallel = parallel_executor.should_use_parallel_execution(workflow)
        logger.info(f"Should use parallel execution: {should_use_parallel}")
        
        if should_use_parallel:
            logger.info("Executing with custom parallel executor...")
            result = await parallel_executor.execute_workflow(workflow)
        else:
            logger.info("Executing with orchestrator (will use parallel if needed)...")
            result = await orchestrator.execute_workflow(workflow)
        
        logger.info(f"Workflow execution completed with status: {result.status}")
        
        if result.status.value == "completed":
            logger.info("SUCCESS: Workflow executed without 'Already found path' error!")
            logger.info(f"Execution took {result.total_duration_ms}ms")
            logger.info(f"Node results: {[nr.node_id for nr in result.node_results]}")
            
            # Show execution details
            for nr in result.node_results:
                logger.info(f"  - {nr.node_id} ({nr.connector_name}): {nr.status.value} in {nr.duration_ms}ms")
        else:
            logger.error(f"Workflow execution failed: {result.error}")
        
    except Exception as e:
        logger.error(f"Error building/compiling graph: {str(e)}")
        
        # Check if it's the specific path error
        if "Already found path" in str(e):
            logger.error("This is the 'Already found path' error we're trying to fix!")
            
            # Let's analyze the workflow structure
            logger.info("Analyzing workflow structure:")
            logger.info(f"Nodes: {[node.id for node in workflow.nodes]}")
            
            for node in workflow.nodes:
                logger.info(f"Node {node.id} dependencies: {node.dependencies}")
            
            # The issue might be in how we're adding edges
            # Let's check for potential duplicate edge scenarios
            
        raise

if __name__ == "__main__":
    asyncio.run(test_workflow_path_error())