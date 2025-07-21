"""
Integration test for the conversational agent system.
Tests the complete flow from API endpoints to agent processing.
"""
import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.conversational_agent import ConversationalAgent
from app.models.conversation import ConversationContext, ChatMessage
from app.models.base import ConversationState, WorkflowStatus
from app.models.connector import ConnectorMetadata


async def test_conversational_agent_integration():
    """Test the complete conversational agent workflow."""
    print("🤖 Testing Conversational Agent Integration...")
    
    # Mock RAG retriever
    mock_rag_retriever = AsyncMock()
    mock_rag_retriever.retrieve_connectors.return_value = [
        ConnectorMetadata(
            name="gmail_connector",
            description="Send and receive emails via Gmail API",
            category="communication",
            parameter_schema={
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"}
            },
            auth_type="oauth2",
            usage_count=15
        ),
        ConnectorMetadata(
            name="google_sheets_connector",
            description="Read and write data to Google Sheets",
            category="data",
            parameter_schema={
                "spreadsheet_id": {"type": "string", "description": "Google Sheets ID"},
                "range": {"type": "string", "description": "Cell range to read/write"},
                "values": {"type": "array", "description": "Data values"}
            },
            auth_type="oauth2",
            usage_count=12
        ),
        ConnectorMetadata(
            name="http_connector",
            description="Make HTTP requests to any REST API",
            category="data",
            parameter_schema={
                "url": {"type": "string", "description": "API endpoint URL"},
                "method": {"type": "string", "description": "HTTP method"},
                "headers": {"type": "object", "description": "Request headers"},
                "body": {"type": "object", "description": "Request body"}
            },
            auth_type="api_key",
            usage_count=8
        )
    ]
    
    # Create agent instance
    agent = ConversationalAgent(mock_rag_retriever)
    agent._initialized = True
    
    # Mock Azure OpenAI client
    mock_client = AsyncMock()
    agent._client = mock_client
    
    # Test 1: Process initial prompt that requires clarification
    print("\n📝 Test 1: Processing prompt that needs clarification...")
    
    intent_response = {
        "intent": "workflow_creation",
        "confidence": 0.6,
        "entities": {"services": ["email"]},
        "requires_clarification": True,
        "clarification_questions": [
            "What email service would you like to use?",
            "Who should receive the emails?",
            "What should trigger the email sending?"
        ]
    }
    
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps(intent_response)))]
    )
    
    with patch('app.services.conversational_agent.get_database') as mock_db:
        mock_db.return_value.table.return_value.upsert.return_value.execute.return_value = None
        
        context, response = await agent.process_initial_prompt(
            prompt="I want to send emails automatically",
            user_id="test-user-123"
        )
        
        assert context.state == ConversationState.PLANNING
        assert "What email service would you like to use?" in response
        print("✅ Clarification request handled correctly")
    
    # Test 2: Continue conversation with more details
    print("\n💬 Test 2: Continuing conversation with additional details...")
    
    planning_response = {
        "name": "Gmail Notification Workflow",
        "description": "Send automated Gmail notifications based on data updates",
        "nodes": [
            {
                "connector_name": "google_sheets_connector",
                "parameters": {
                    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    "range": "A1:B10"
                },
                "dependencies": []
            },
            {
                "connector_name": "gmail_connector",
                "parameters": {
                    "to": "manager@company.com",
                    "subject": "Daily Report Update",
                    "body": "Please find the updated data in the attached report."
                },
                "dependencies": ["google_sheets_connector"]
            }
        ],
        "triggers": [
            {
                "type": "schedule",
                "config": {"interval": "daily", "time": "09:00"},
                "enabled": True
            }
        ],
        "reasoning": "This workflow reads data from Google Sheets and sends a daily email notification to the manager.",
        "confidence": 0.85
    }
    
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(function_call=MagicMock(arguments=json.dumps(planning_response))))]
    )
    
    # Update context to simulate conversation continuation
    context.messages.append(ChatMessage(
        id="msg-2",
        role="user",
        content="I want to use Gmail to send daily reports to my manager based on Google Sheets data"
    ))
    
    with patch.object(agent, '_load_conversation_context', return_value=context), \
         patch.object(agent, '_save_conversation_context'), \
         patch('app.services.conversational_agent.get_database'):
        
        updated_context, response = await agent.handle_conversation_turn(
            message="create the workflow",
            session_id=context.session_id
        )
        
        assert updated_context.state == ConversationState.CONFIRMING
        assert updated_context.current_plan is not None
        assert updated_context.current_plan.name == "Gmail Notification Workflow"
        assert len(updated_context.current_plan.nodes) == 2
        assert len(updated_context.current_plan.triggers) == 1
        print("✅ Workflow plan generated successfully")
    
    # Test 3: Request plan modification
    print("\n🔧 Test 3: Requesting plan modification...")
    
    modification_response = {
        "name": "Gmail Notification Workflow",
        "description": "Send automated Gmail notifications based on data updates",
        "nodes": [
            {
                "connector_name": "google_sheets_connector",
                "parameters": {
                    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    "range": "A1:B10"
                },
                "dependencies": []
            },
            {
                "connector_name": "gmail_connector",
                "parameters": {
                    "to": "team@company.com",  # Changed recipient
                    "subject": "Weekly Report Update",  # Changed frequency
                    "body": "Please find the updated data in the attached report."
                },
                "dependencies": ["google_sheets_connector"]
            }
        ],
        "triggers": [
            {
                "type": "schedule",
                "config": {"interval": "weekly", "time": "09:00", "day": "monday"},  # Changed to weekly
                "enabled": True
            }
        ],
        "reasoning": "Modified to send weekly reports to the entire team instead of daily reports to manager.",
        "confidence": 0.9
    }
    
    mock_client.chat.completions.create.side_effect = [
        # Modification response
        MagicMock(choices=[MagicMock(message=MagicMock(function_call=MagicMock(arguments=json.dumps(modification_response))))]),
        # Explanation response
        MagicMock(choices=[MagicMock(message=MagicMock(content="I've updated the workflow to send weekly reports to the entire team instead of daily reports to the manager."))])
    ]
    
    from app.models.conversation import PlanModificationRequest
    
    modification_request = PlanModificationRequest(
        session_id=updated_context.session_id,
        modification="Change it to send weekly reports to the entire team instead",
        current_plan=updated_context.current_plan
    )
    
    with patch.object(agent, '_load_conversation_context', return_value=updated_context), \
         patch.object(agent, '_save_conversation_context'):
        
        modified_plan, explanation = await agent.modify_workflow_plan(modification_request)
        
        assert modified_plan.nodes[1].parameters["to"] == "team@company.com"
        assert modified_plan.triggers[0].config["interval"] == "weekly"
        assert "weekly reports to the entire team" in explanation
        print("✅ Plan modification handled successfully")
    
    # Test 4: Approve the final plan
    print("\n✅ Test 4: Approving the final workflow plan...")
    
    from app.models.conversation import PlanConfirmationRequest
    
    confirmation_request = PlanConfirmationRequest(
        session_id=updated_context.session_id,
        plan=modified_plan,
        approved=True
    )
    
    # Update context with modified plan
    updated_context.current_plan = modified_plan
    
    with patch.object(agent, '_load_conversation_context', return_value=updated_context), \
         patch.object(agent, '_save_conversation_context'), \
         patch.object(agent, '_save_workflow_plan'):
        
        final_context, response = await agent.confirm_workflow_plan(confirmation_request)
        
        assert final_context.state == ConversationState.APPROVED
        assert final_context.current_plan.status == WorkflowStatus.ACTIVE
        assert "approved" in response.lower()
        print("✅ Workflow plan approved and saved successfully")
    
    # Test 5: Test utility functions
    print("\n🔧 Test 5: Testing utility functions...")
    
    # Test node sorting
    from app.models.base import WorkflowNode, NodePosition
    
    nodes = [
        WorkflowNode(
            id="node-3",
            connector_name="final_step",
            parameters={},
            position=NodePosition(x=0, y=0),
            dependencies=["first_step", "second_step"]
        ),
        WorkflowNode(
            id="node-1",
            connector_name="first_step",
            parameters={},
            position=NodePosition(x=0, y=0),
            dependencies=[]
        ),
        WorkflowNode(
            id="node-2",
            connector_name="second_step",
            parameters={},
            position=NodePosition(x=0, y=0),
            dependencies=["first_step"]
        )
    ]
    
    sorted_nodes = agent._sort_nodes_by_dependencies(nodes)
    assert sorted_nodes[0].connector_name == "first_step"
    assert sorted_nodes[1].connector_name == "second_step"
    assert sorted_nodes[2].connector_name == "final_step"
    print("✅ Node dependency sorting works correctly")
    
    # Test parameter formatting
    params = {
        "short_param": "value",
        "long_param": "This is a very long parameter value that should be truncated for display purposes",
        "number_param": 42
    }
    
    formatted = agent._format_parameters(params)
    assert "short_param=value" in formatted
    assert "long_param=This is a very long parameter value that should..." in formatted
    assert "number_param=42" in formatted
    print("✅ Parameter formatting works correctly")
    
    print("\n🎉 All conversational agent integration tests passed!")
    
    # Summary
    print("\n📊 Test Summary:")
    print("- ✅ Intent recognition and clarification handling")
    print("- ✅ Workflow plan generation with connector selection")
    print("- ✅ Multi-turn conversation management")
    print("- ✅ Plan modification and explanation")
    print("- ✅ Plan confirmation and approval")
    print("- ✅ Utility functions for data processing")
    print("\n🚀 Conversational agent system is ready for use!")


if __name__ == "__main__":
    asyncio.run(test_conversational_agent_integration())