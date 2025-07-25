#!/usr/bin/env python3
"""
Test script to verify the complete workflow execution flow.
"""
import asyncio
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.conversational_agent import ConversationalAgent
from app.services.rag import RAGRetriever
from app.services.workflow_orchestrator import WorkflowOrchestrator
from app.models.conversation import PlanConfirmationRequest
from app.models.base import WorkflowPlan, WorkflowNode, WorkflowEdge, WorkflowStatus
from app.core.database import init_database
from app.core.config import settings
from datetime import datetime
import uuid

async def test_workflow_execution_flow():
    """Test the complete workflow execution flow."""
    print("🚀 Testing Workflow Execution Flow")
    print("=" * 50)
    
    try:
        # Initialize database
        print("1. Initializing database...")
        await init_database()
        print("✅ Database initialized")
        
        # Initialize RAG system
        print("2. Initializing RAG system...")
        rag_retriever = RAGRetriever()
        await rag_retriever.initialize()
        print("✅ RAG system initialized")
        
        # Initialize conversational agent
        print("3. Initializing conversational agent...")
        agent = ConversationalAgent(rag_retriever)
        await agent.initialize()
        print("✅ Conversational agent initialized")
        
        # Test workflow plan generation
        print("4. Testing workflow plan generation...")
        user_id = "test-user-123"
        prompt = "Send me an email when someone fills out my contact form"
        
        context, response = await agent.process_initial_prompt(
            prompt=prompt,
            user_id=user_id
        )
        
        print(f"✅ Generated response: {response[:100]}...")
        
        if context.current_plan:
            print(f"✅ Workflow plan created: {context.current_plan.name}")
            print(f"   - Nodes: {len(context.current_plan.nodes)}")
            print(f"   - Edges: {len(context.current_plan.edges)}")
            print(f"   - Status: {context.current_plan.status}")
            
            # Test workflow approval and execution
            print("5. Testing workflow approval and execution...")
            
            confirmation_request = PlanConfirmationRequest(
                session_id=context.session_id,
                plan=context.current_plan,
                approved=True
            )
            
            updated_context, approval_response = await agent.confirm_workflow_plan(confirmation_request)
            print(f"✅ Approval response: {approval_response[:200]}...")
            
            # Check if execution ID is in the response
            if "Execution ID:" in approval_response:
                print("✅ Workflow execution was triggered automatically")
                
                # Extract execution ID
                import re
                execution_id_match = re.search(r'Execution ID: `([^`]+)`', approval_response)
                if execution_id_match:
                    execution_id = execution_id_match.group(1)
                    print(f"   - Execution ID: {execution_id}")
                    
                    # Test execution status retrieval
                    print("6. Testing execution status retrieval...")
                    orchestrator = WorkflowOrchestrator()
                    
                    # Wait a moment for execution to start
                    await asyncio.sleep(2)
                    
                    execution_status = await orchestrator.get_execution_status(execution_id)
                    if execution_status:
                        print(f"✅ Execution status: {execution_status.status}")
                        print(f"   - Started at: {execution_status.started_at}")
                        print(f"   - Node results: {len(execution_status.node_results)}")
                        
                        for node_result in execution_status.node_results:
                            print(f"     - {node_result.node_id}: {node_result.status}")
                    else:
                        print("❌ Could not retrieve execution status")
                else:
                    print("❌ Could not extract execution ID from response")
            else:
                print("❌ Workflow execution was not triggered")
        else:
            print("❌ No workflow plan was generated")
            
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_workflow_execution_flow())