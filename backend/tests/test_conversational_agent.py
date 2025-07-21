"""
Tests for the conversational agent system.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.conversational_agent import (
    ConversationalAgent,
    IntentRecognitionResult,
    WorkflowPlanningResult
)
from app.models.conversation import ConversationContext, ChatMessage
from app.models.base import (
    WorkflowPlan, 
    WorkflowNode, 
    WorkflowEdge, 
    NodePosition,
    ConversationState,
    WorkflowStatus
)
from app.models.connector import ConnectorMetadata
from app.core.exceptions import AgentError, PlanningError


class TestConversationalAgent:
    """Test cases for the ConversationalAgent class."""
    
    @pytest.fixture
    def mock_rag_retriever(self):
        """Mock RAG retriever for testing."""
        mock_retriever = AsyncMock()
        mock_retriever.retrieve_connectors.return_value = [
            ConnectorMetadata(
                name="gmail_connector",
                description="Send and receive emails via Gmail",
                category="communication",
                parameter_schema={"to": "string", "subject": "string", "body": "string"},
                auth_type="oauth2",
                usage_count=10
            ),
            ConnectorMetadata(
                name="http_connector",
                description="Make HTTP requests to any API",
                category="data",
                parameter_schema={"url": "string", "method": "string"},
                auth_type="api_key",
                usage_count=5
            )
        ]
        return mock_retriever
    
    @pytest.fixture
    def agent(self, mock_rag_retriever):
        """Create agent instance for testing."""
        agent = ConversationalAgent(mock_rag_retriever)
        agent._initialized = True
        agent._client = AsyncMock()
        return agent
    
    @pytest.mark.asyncio
    async def test_process_initial_prompt_success(self, agent):
        """Test successful processing of initial prompt."""
        # Mock intent recognition response
        intent_response = {
            "intent": "workflow_creation",
            "confidence": 0.9,
            "entities": {"services": ["gmail"], "actions": ["send_email"]},
            "requires_clarification": False,
            "clarification_questions": []
        }
        
        # Mock workflow planning response
        planning_response = {
            "name": "Email Automation",
            "description": "Send automated emails",
            "nodes": [
                {
                    "connector_name": "gmail_connector",
                    "parameters": {"to": "user@example.com", "subject": "Test"},
                    "dependencies": []
                }
            ],
            "triggers": [],
            "reasoning": "Simple email sending workflow",
            "confidence": 0.8
        }
        
        # Mock OpenAI responses
        agent._client.chat.completions.create.side_effect = [
            # Intent recognition response
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(intent_response)))]),
            # Planning response
            MagicMock(choices=[MagicMock(message=MagicMock(function_call=MagicMock(arguments=json.dumps(planning_response))))])
        ]
        
        # Mock database operations
        with patch('app.services.conversational_agent.get_database') as mock_db:
            mock_db.return_value.table.return_value.upsert.return_value.execute.return_value = None
            
            # Test the method
            context, response = await agent.process_initial_prompt(
                prompt="Send an email to user@example.com",
                user_id="test-user-id"
            )
            
            # Assertions
            assert context.user_id == "test-user-id"
            assert context.state == ConversationState.CONFIRMING
            assert context.current_plan is not None
            assert context.current_plan.name == "Email Automation"
            assert len(context.messages) == 2  # User message + assistant response
            assert "Email Automation" in response
    
    @pytest.mark.asyncio
    async def test_process_initial_prompt_needs_clarification(self, agent):
        """Test processing prompt that needs clarification."""
        # Mock intent recognition response requiring clarification
        intent_response = {
            "intent": "workflow_creation",
            "confidence": 0.5,
            "entities": {},
            "requires_clarification": True,
            "clarification_questions": [
                "What service would you like to integrate?",
                "What action should the workflow perform?"
            ]
        }
        
        agent._client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(intent_response)))]
        )
        
        with patch('app.services.conversational_agent.get_database') as mock_db:
            mock_db.return_value.table.return_value.upsert.return_value.execute.return_value = None
            
            context, response = await agent.process_initial_prompt(
                prompt="I want to automate something",
                user_id="test-user-id"
            )
            
            assert context.state == ConversationState.PLANNING
            assert context.current_plan is None
            assert "What service would you like to integrate?" in response
            assert "What action should the workflow perform?" in response
    
    @pytest.mark.asyncio
    async def test_handle_conversation_turn_planning(self, agent):
        """Test handling conversation during planning phase."""
        # Create context in planning state
        context = ConversationContext(
            session_id="test-session",
            user_id="test-user",
            state=ConversationState.PLANNING,
            messages=[
                ChatMessage(id="1", role="user", content="I want to automate emails"),
                ChatMessage(id="2", role="assistant", content="I need more information...")
            ]
        )
        
        # Mock planning response
        planning_response = {
            "name": "Email Workflow",
            "description": "Automated email workflow",
            "nodes": [{"connector_name": "gmail_connector", "parameters": {}, "dependencies": []}],
            "triggers": [],
            "reasoning": "Email automation workflow",
            "confidence": 0.8
        }
        
        agent._client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(function_call=MagicMock(arguments=json.dumps(planning_response))))]
        )
        
        with patch.object(agent, '_load_conversation_context', return_value=context), \
             patch.object(agent, '_save_conversation_context'), \
             patch('app.services.conversational_agent.get_database'):
            
            updated_context, response = await agent.handle_conversation_turn(
                message="create the workflow",
                session_id="test-session"
            )
            
            assert updated_context.state == ConversationState.CONFIRMING
            assert updated_context.current_plan is not None
            assert "Email Workflow" in response
    
    @pytest.mark.asyncio
    async def test_handle_conversation_turn_confirmation_approve(self, agent):
        """Test handling conversation during confirmation phase - approval."""
        # Create workflow plan
        plan = WorkflowPlan(
            id="test-plan-id",
            user_id="test-user",
            name="Test Workflow",
            description="Test workflow description",
            nodes=[],
            edges=[],
            triggers=[]
        )
        
        context = ConversationContext(
            session_id="test-session",
            user_id="test-user",
            state=ConversationState.CONFIRMING,
            current_plan=plan
        )
        
        with patch.object(agent, '_load_conversation_context', return_value=context), \
             patch.object(agent, '_save_conversation_context'), \
             patch.object(agent, '_save_workflow_plan'):
            
            updated_context, response = await agent.handle_conversation_turn(
                message="yes, approve it",
                session_id="test-session"
            )
            
            assert updated_context.state == ConversationState.APPROVED
            assert updated_context.current_plan.status == WorkflowStatus.ACTIVE
            assert "approved" in response.lower()
    
    @pytest.mark.asyncio
    async def test_handle_conversation_turn_confirmation_modify(self, agent):
        """Test handling conversation during confirmation phase - modification request."""
        # Create workflow plan
        plan = WorkflowPlan(
            id="test-plan-id",
            user_id="test-user",
            name="Test Workflow",
            description="Test workflow description",
            nodes=[],
            edges=[],
            triggers=[]
        )
        
        context = ConversationContext(
            session_id="test-session",
            user_id="test-user",
            state=ConversationState.CONFIRMING,
            current_plan=plan
        )
        
        # Mock modification response
        modification_response = {
            "name": "Modified Workflow",
            "description": "Modified workflow description",
            "nodes": [],
            "triggers": [],
            "reasoning": "Modified based on user feedback",
            "confidence": 0.8
        }
        
        agent._client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(function_call=MagicMock(arguments=json.dumps(modification_response))))]
        )
        
        with patch.object(agent, '_load_conversation_context', return_value=context), \
             patch.object(agent, '_save_conversation_context'), \
             patch('app.services.conversational_agent.get_database'):
            
            updated_context, response = await agent.handle_conversation_turn(
                message="change the name to Modified Workflow",
                session_id="test-session"
            )
            
            assert updated_context.current_plan.name == "Modified Workflow"
            assert "Modified Workflow" in response
    
    @pytest.mark.asyncio
    async def test_modify_workflow_plan(self, agent):
        """Test workflow plan modification."""
        from app.models.conversation import PlanModificationRequest
        
        # Create original plan
        original_plan = WorkflowPlan(
            id="test-plan-id",
            user_id="test-user",
            name="Original Workflow",
            description="Original description",
            nodes=[],
            edges=[],
            triggers=[]
        )
        
        context = ConversationContext(
            session_id="test-session",
            user_id="test-user",
            current_plan=original_plan
        )
        
        request = PlanModificationRequest(
            session_id="test-session",
            modification="Change the name to New Workflow",
            current_plan=original_plan
        )
        
        # Mock modification response
        modification_response = {
            "name": "New Workflow",
            "description": "Original description",
            "nodes": [],
            "triggers": [],
            "reasoning": "Changed name as requested",
            "confidence": 0.9
        }
        
        agent._client.chat.completions.create.side_effect = [
            # Modification response
            MagicMock(choices=[MagicMock(message=MagicMock(function_call=MagicMock(arguments=json.dumps(modification_response))))]),
            # Explanation response
            MagicMock(choices=[MagicMock(message=MagicMock(content="Changed the workflow name from 'Original Workflow' to 'New Workflow'"))])
        ]
        
        with patch.object(agent, '_load_conversation_context', return_value=context), \
             patch.object(agent, '_save_conversation_context'):
            
            modified_plan, explanation = await agent.modify_workflow_plan(request)
            
            assert modified_plan.name == "New Workflow"
            assert modified_plan.id == original_plan.id  # ID should be preserved
            assert "Changed the workflow name" in explanation
    
    @pytest.mark.asyncio
    async def test_confirm_workflow_plan_approved(self, agent):
        """Test workflow plan confirmation - approved."""
        from app.models.conversation import PlanConfirmationRequest
        
        plan = WorkflowPlan(
            id="test-plan-id",
            user_id="test-user",
            name="Test Workflow",
            description="Test description",
            nodes=[],
            edges=[],
            triggers=[]
        )
        
        context = ConversationContext(
            session_id="test-session",
            user_id="test-user",
            current_plan=plan
        )
        
        request = PlanConfirmationRequest(
            session_id="test-session",
            plan=plan,
            approved=True
        )
        
        with patch.object(agent, '_load_conversation_context', return_value=context), \
             patch.object(agent, '_save_conversation_context'), \
             patch.object(agent, '_save_workflow_plan'):
            
            updated_context, response = await agent.confirm_workflow_plan(request)
            
            assert updated_context.state == ConversationState.APPROVED
            assert updated_context.current_plan.status == WorkflowStatus.ACTIVE
            assert "approved" in response.lower()
    
    @pytest.mark.asyncio
    async def test_confirm_workflow_plan_rejected(self, agent):
        """Test workflow plan confirmation - rejected."""
        from app.models.conversation import PlanConfirmationRequest
        
        plan = WorkflowPlan(
            id="test-plan-id",
            user_id="test-user",
            name="Test Workflow",
            description="Test description",
            nodes=[],
            edges=[],
            triggers=[]
        )
        
        context = ConversationContext(
            session_id="test-session",
            user_id="test-user",
            current_plan=plan,
            state=ConversationState.CONFIRMING
        )
        
        request = PlanConfirmationRequest(
            session_id="test-session",
            plan=plan,
            approved=False
        )
        
        with patch.object(agent, '_load_conversation_context', return_value=context), \
             patch.object(agent, '_save_conversation_context'):
            
            updated_context, response = await agent.confirm_workflow_plan(request)
            
            assert updated_context.state == ConversationState.PLANNING
            assert "changes you'd like to make" in response
    
    def test_create_workflow_plan_from_data(self, agent):
        """Test creating WorkflowPlan from structured data."""
        plan_data = {
            "name": "Test Workflow",
            "description": "Test description",
            "nodes": [
                {
                    "connector_name": "gmail_connector",
                    "parameters": {"to": "test@example.com"},
                    "dependencies": []
                },
                {
                    "connector_name": "http_connector",
                    "parameters": {"url": "https://api.example.com"},
                    "dependencies": ["gmail_connector"]
                }
            ],
            "triggers": [
                {
                    "type": "schedule",
                    "config": {"interval": "daily"},
                    "enabled": True
                }
            ],
            "reasoning": "Test workflow for automation",
            "confidence": 0.8
        }
        
        plan = agent._create_workflow_plan_from_data(plan_data, "test-user-id")
        
        assert plan.name == "Test Workflow"
        assert plan.description == "Test description"
        assert plan.user_id == "test-user-id"
        assert len(plan.nodes) == 2
        assert len(plan.edges) == 1  # One dependency creates one edge
        assert len(plan.triggers) == 1
        assert plan.status == WorkflowStatus.DRAFT
        
        # Check nodes
        gmail_node = next(n for n in plan.nodes if n.connector_name == "gmail_connector")
        http_node = next(n for n in plan.nodes if n.connector_name == "http_connector")
        
        assert gmail_node.parameters["to"] == "test@example.com"
        assert http_node.parameters["url"] == "https://api.example.com"
        assert "gmail_connector" in http_node.dependencies
        
        # Check edge
        edge = plan.edges[0]
        assert edge.source == gmail_node.id
        assert edge.target == http_node.id
        
        # Check trigger
        trigger = plan.triggers[0]
        assert trigger.type == "schedule"
        assert trigger.config["interval"] == "daily"
        assert trigger.enabled is True
    
    def test_sort_nodes_by_dependencies(self, agent):
        """Test sorting nodes by their dependencies."""
        nodes = [
            WorkflowNode(
                id="3",
                connector_name="node_c",
                parameters={},
                position=NodePosition(x=0, y=0),
                dependencies=["node_a", "node_b"]
            ),
            WorkflowNode(
                id="1",
                connector_name="node_a",
                parameters={},
                position=NodePosition(x=0, y=0),
                dependencies=[]
            ),
            WorkflowNode(
                id="2",
                connector_name="node_b",
                parameters={},
                position=NodePosition(x=0, y=0),
                dependencies=["node_a"]
            )
        ]
        
        sorted_nodes = agent._sort_nodes_by_dependencies(nodes)
        
        # Should be sorted as: node_a, node_b, node_c
        assert sorted_nodes[0].connector_name == "node_a"
        assert sorted_nodes[1].connector_name == "node_b"
        assert sorted_nodes[2].connector_name == "node_c"
    
    @pytest.mark.asyncio
    async def test_error_handling_agent_error(self, agent):
        """Test error handling for agent errors."""
        agent._client.chat.completions.create.side_effect = Exception("OpenAI API error")
        
        with pytest.raises(AgentError):
            await agent.process_initial_prompt(
                prompt="test prompt",
                user_id="test-user"
            )
    
    @pytest.mark.asyncio
    async def test_error_handling_planning_error(self, agent):
        """Test error handling for planning errors."""
        # Mock empty connector list
        agent.rag_retriever.retrieve_connectors.return_value = []
        
        with pytest.raises(PlanningError):
            await agent._generate_workflow_plan("test prompt", ConversationContext(
                session_id="test",
                user_id="test-user"
            ))


if __name__ == "__main__":
    pytest.main([__file__])