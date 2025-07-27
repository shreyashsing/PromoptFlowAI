#!/usr/bin/env python3
"""
Test script to verify the parallel execution fixes.
"""
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from app.models.base import WorkflowPlan, WorkflowNode, NodePosition
from app.services.parallel_workflow_executor import ParallelWorkflowExecutor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_parallel_execution_fixes():
    """Test the parallel execution engine with fixes."""
    
    # Create a test workflow with proper node IDs
    workflow = WorkflowPlan(
        id="test-parallel-workflow",
        user_id=str(uuid4()),  # Use proper UUID format
        name="Test Parallel Execution Fixes",
        description="Test workflow to verify parallel execution fixes",
        nodes=[
            WorkflowNode(
                id="node_perplexity",
                connector_name="perplexity_search",
                parameters={
                    "action": "search",
                    "query": "latest AI news",
                    "model": "sonar"
                },
                position=NodePosition(x=100, y=100),
                dependencies=[]
            ),
            WorkflowNode(
                id="node_sheets",
                connector_name="google_sheets",
                parameters={
                    "action": "append",
                    "spreadsheet_id": "test_sheet_id",
                    "values": [["{{node_perplexity.result}}"]]  # Use node ID
                },
                position=NodePosition(x=200, y=200),
                dependencies=["node_perplexity"]
            ),
            WorkflowNode(
                id="node_summarizer",
                connector_name="text_summarizer",
                parameters={
                    "text": "{{node_perplexity.result}}",  # Use node ID
                    "style": "concise"
                },
                position=NodePosition(x=200, y=300),
                dependencies=["node_perplexity"]
            ),
            WorkflowNode(
                id="node_gmail",
                connector_name="gmail_connector",
                parameters={
                    "action": "send",
                    "to": "test@example.com",
                    "subject": "AI News Summary",
                    "body": "{{node_summarizer.result}}"  # Use node ID
                },
                position=NodePosition(x=300, y=400),
                dependencies=["node_summarizer"]
            )
        ],
        edges=[],
        triggers=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create parallel executor
    parallel_executor = ParallelWorkflowExecutor()
    
    try:
        logger.info("Testing parallel execution with fixes...")
        
        # Check if workflow should use parallel execution
        should_use_parallel = parallel_executor.should_use_parallel_execution(workflow)
        logger.info(f"Should use parallel execution: {should_use_parallel}")
        
        if should_use_parallel:
            logger.info("Executing with parallel executor...")
            result = await parallel_executor.execute_workflow(workflow)
            
            logger.info(f"Workflow execution completed with status: {result.status}")
            logger.info(f"Execution took {result.total_duration_ms}ms")
            
            # Show execution details
            logger.info("Node execution results:")
            for nr in result.node_results:
                status_emoji = "✅" if nr.status.value == "completed" else "❌"
                logger.info(f"  {status_emoji} {nr.node_id} ({nr.connector_name}): {nr.status.value} in {nr.duration_ms}ms")
                if nr.error:
                    logger.info(f"    Error: {nr.error}")
            
            # Test parameter resolution
            logger.info("\nTesting parameter resolution...")
            test_params = {
                "test1": "{{node_perplexity.result}}",
                "test2": "{{perplexity_search.result}}",  # By connector name
                "test3": "Summary: {{node_summarizer.result}}"
            }
            
            # Create mock previous results
            mock_results = {
                "node_perplexity": type('MockResult', (), {
                    'data': {"result": "Test AI news content", "citations": ["source1", "source2"]},
                    'connector_name': 'perplexity_search'
                })(),
                "node_summarizer": type('MockResult', (), {
                    'data': {"result": "Brief AI news summary"},
                    'connector_name': 'text_summarizer'
                })()
            }
            
            resolved_params = await parallel_executor._resolve_node_parameters(test_params, mock_results)
            logger.info("Parameter resolution test results:")
            for key, value in resolved_params.items():
                logger.info(f"  {key}: {value}")
            
            if result.status.value == "completed":
                logger.info("\n🎉 SUCCESS: All fixes working correctly!")
            else:
                logger.info(f"\n⚠️  Workflow completed with status: {result.status.value}")
                if result.error:
                    logger.info(f"Error: {result.error}")
        else:
            logger.info("Workflow doesn't need parallel execution")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_parallel_execution_fixes())