"""
Conversational Agent System for PromptFlow AI.
Handles prompt parsing, intent recognition, dialogue management, and workflow planning.
"""
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_database
from app.core.exceptions import AgentError, PlanningError
from app.models.conversation import (
    ConversationContext, 
    ChatMessage, 
    PlanModificationRequest,
    PlanConfirmationRequest
)
from app.models.base import (
    WorkflowPlan, 
    WorkflowNode, 
    WorkflowEdge, 
    NodePosition,
    ConversationState,
    WorkflowStatus,
    Trigger
)
from app.models.connector import ConnectorMetadata
from app.services.rag import RAGRetriever

logger = logging.getLogger(__name__)


class IntentRecognitionResult(BaseModel):
    """Result of intent recognition analysis."""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    requires_clarification: bool
    clarification_questions: List[str]


class WorkflowPlanningResult(BaseModel):
    """Result of workflow planning process."""
    plan: WorkflowPlan
    selected_connectors: List[ConnectorMetadata]
    reasoning: str
    confidence: float


class ConversationalAgent:
    """
    Main conversational agent for interactive workflow planning.
    Handles prompt parsing, intent recognition, and dialogue management.
    """
    
    def __init__(self, rag_retriever: RAGRetriever):
        self.rag_retriever = rag_retriever
        self._client: Optional[AsyncAzureOpenAI] = None
        self._initialized = False
        
        # System prompts for different phases
        self.intent_recognition_prompt = self._load_intent_recognition_prompt()
        self.planning_prompt = self._load_planning_prompt()
        self.modification_prompt = self._load_modification_prompt()
    
    async def initialize(self) -> None:
        """Initialize the Azure OpenAI client."""
        if self._initialized:
            return
            
        try:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            self._initialized = True
            logger.info("Conversational agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize conversational agent: {e}")
            raise AgentError(f"Failed to initialize agent: {e}")
    
    async def process_initial_prompt(
        self, 
        prompt: str, 
        user_id: str,
        session_id: Optional[str] = None
    ) -> Tuple[ConversationContext, str]:
        """
        Process initial user prompt and start conversation.
        
        Args:
            prompt: User's natural language prompt
            user_id: ID of the user
            session_id: Optional existing session ID
            
        Returns:
            Tuple of (ConversationContext, response_message)
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Create or get conversation context
            if not session_id:
                session_id = str(uuid.uuid4())
            
            context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                state=ConversationState.INITIAL
            )
            
            # Add user message to context
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="user",
                content=prompt
            )
            context.messages.append(user_message)
            
            # Recognize intent and analyze prompt
            intent_result = await self._recognize_intent(prompt, context)
            
            # Generate response based on intent
            if intent_result.requires_clarification:
                response = await self._handle_clarification_needed(intent_result, context)
                context.state = ConversationState.PLANNING
            else:
                # Proceed directly to workflow planning
                planning_result = await self._generate_workflow_plan(prompt, context)
                response = await self._present_workflow_plan(planning_result, context)
                context.current_plan = planning_result.plan
                context.state = ConversationState.CONFIRMING
            
            # Add assistant response to context
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="assistant",
                content=response
            )
            context.messages.append(assistant_message)
            
            # Save conversation context
            await self._save_conversation_context(context)
            
            logger.info(f"Processed initial prompt for session {session_id}")
            return context, response
            
        except Exception as e:
            logger.error(f"Failed to process initial prompt: {e}")
            raise AgentError(f"Failed to process prompt: {e}")
    
    async def handle_conversation_turn(
        self, 
        message: str, 
        session_id: str
    ) -> Tuple[ConversationContext, str]:
        """
        Handle a conversation turn in an existing session.
        
        Args:
            message: User's message
            session_id: Session ID
            
        Returns:
            Tuple of (updated_context, response_message)
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Load conversation context
            context = await self._load_conversation_context(session_id)
            if not context:
                raise AgentError(f"Session {session_id} not found")
            
            # Add user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="user",
                content=message
            )
            context.messages.append(user_message)
            
            # Handle based on current conversation state
            if context.state == ConversationState.PLANNING:
                response = await self._handle_planning_conversation(message, context)
            elif context.state == ConversationState.CONFIRMING:
                response = await self._handle_confirmation_conversation(message, context)
            else:
                response = "I'm not sure how to help with that. Could you please start over with a new workflow request?"
            
            # Add assistant response
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                role="assistant",
                content=response
            )
            context.messages.append(assistant_message)
            
            # Update timestamp
            context.updated_at = datetime.utcnow()
            
            # Save updated context
            await self._save_conversation_context(context)
            
            logger.info(f"Handled conversation turn for session {session_id}")
            return context, response
            
        except Exception as e:
            logger.error(f"Failed to handle conversation turn: {e}")
            raise AgentError(f"Failed to handle conversation: {e}")
    
    async def modify_workflow_plan(
        self, 
        request: PlanModificationRequest
    ) -> Tuple[WorkflowPlan, str]:
        """
        Modify an existing workflow plan based on user request.
        
        Args:
            request: Plan modification request
            
        Returns:
            Tuple of (modified_plan, explanation)
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Load conversation context
            context = await self._load_conversation_context(request.session_id)
            if not context:
                raise AgentError(f"Session {request.session_id} not found")
            
            # Generate modified plan
            modified_plan = await self._apply_plan_modifications(
                request.modification, 
                request.current_plan, 
                context
            )
            
            # Generate explanation of changes
            explanation = await self._explain_plan_changes(
                request.current_plan, 
                modified_plan, 
                request.modification
            )
            
            # Update context
            context.current_plan = modified_plan
            context.updated_at = datetime.utcnow()
            await self._save_conversation_context(context)
            
            logger.info(f"Modified workflow plan for session {request.session_id}")
            return modified_plan, explanation
            
        except Exception as e:
            logger.error(f"Failed to modify workflow plan: {e}")
            raise PlanningError(f"Failed to modify plan: {e}")
    
    async def confirm_workflow_plan(
        self, 
        request: PlanConfirmationRequest
    ) -> Tuple[ConversationContext, str]:
        """
        Handle workflow plan confirmation.
        
        Args:
            request: Plan confirmation request
            
        Returns:
            Tuple of (updated_context, response_message)
        """
        try:
            # Load conversation context
            context = await self._load_conversation_context(request.session_id)
            if not context:
                raise AgentError(f"Session {request.session_id} not found")
            
            if request.approved:
                # Mark plan as approved and ready for execution
                request.plan.status = WorkflowStatus.ACTIVE
                context.current_plan = request.plan
                context.state = ConversationState.APPROVED
                
                response = (
                    f"Great! I've approved your workflow plan '{request.plan.name}'. "
                    f"The workflow is now ready for execution. You can run it manually "
                    f"or set up triggers for automatic execution."
                )
                
                # Save the approved plan to database
                await self._save_workflow_plan(request.plan)
                
            else:
                # Plan rejected, return to planning state
                context.state = ConversationState.PLANNING
                response = (
                    "No problem! Let me know what changes you'd like to make to the workflow plan, "
                    "or provide additional details about what you're trying to accomplish."
                )
            
            # Update context
            context.updated_at = datetime.utcnow()
            await self._save_conversation_context(context)
            
            logger.info(f"Handled plan confirmation for session {request.session_id}")
            return context, response
            
        except Exception as e:
            logger.error(f"Failed to handle plan confirmation: {e}")
            raise AgentError(f"Failed to confirm plan: {e}")
    
    # Private helper methods
    
    async def _recognize_intent(
        self, 
        prompt: str, 
        context: ConversationContext
    ) -> IntentRecognitionResult:
        """Recognize user intent and extract entities from prompt."""
        try:
            messages = [
                {"role": "system", "content": self.intent_recognition_prompt},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse the structured response
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)
            
            return IntentRecognitionResult(**result_data)
            
        except Exception as e:
            logger.error(f"Failed to recognize intent: {e}")
            # Return default result if parsing fails
            return IntentRecognitionResult(
                intent="workflow_creation",
                confidence=0.5,
                entities={},
                requires_clarification=True,
                clarification_questions=[
                    "Could you provide more details about what you'd like to automate?",
                    "What specific actions should the workflow perform?",
                    "What triggers should start this workflow?"
                ]
            )
    
    async def _generate_workflow_plan(
        self, 
        prompt: str, 
        context: ConversationContext
    ) -> WorkflowPlanningResult:
        """Generate a workflow plan based on user prompt."""
        try:
            # Retrieve relevant connectors using RAG
            connectors = await self.rag_retriever.retrieve_connectors(
                query=prompt,
                limit=15,
                similarity_threshold=0.6
            )
            
            if not connectors:
                raise PlanningError("No suitable connectors found for the requested workflow")
            
            # Prepare connector information for the LLM
            connector_info = []
            for conn in connectors:
                connector_info.append({
                    "name": conn.name,
                    "description": conn.description,
                    "category": conn.category,
                    "parameters": conn.parameter_schema,
                    "auth_type": conn.auth_type.value
                })
            
            # Create planning messages
            messages = [
                {"role": "system", "content": self.planning_prompt},
                {
                    "role": "user", 
                    "content": f"""
                    User Request: {prompt}
                    
                    Available Connectors:
                    {json.dumps(connector_info, indent=2)}
                    
                    Please generate a workflow plan that accomplishes the user's request using the available connectors.
                    """
                }
            ]
            
            # Use function calling to generate structured workflow plan
            functions = [self._get_workflow_planning_function()]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                functions=functions,
                function_call={"name": "generate_workflow_plan"},
                temperature=0.2,
                max_tokens=2000
            )
            
            # Parse function call result
            function_call = response.choices[0].message.function_call
            plan_data = json.loads(function_call.arguments)
            
            # Create WorkflowPlan object
            workflow_plan = self._create_workflow_plan_from_data(
                plan_data, 
                context.user_id
            )
            
            # Filter connectors to only those used in the plan
            used_connector_names = {node.connector_name for node in workflow_plan.nodes}
            selected_connectors = [
                conn for conn in connectors 
                if conn.name in used_connector_names
            ]
            
            return WorkflowPlanningResult(
                plan=workflow_plan,
                selected_connectors=selected_connectors,
                reasoning=plan_data.get("reasoning", ""),
                confidence=plan_data.get("confidence", 0.8)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate workflow plan: {e}")
            raise PlanningError(f"Failed to generate workflow plan: {e}")
    
    async def _handle_clarification_needed(
        self, 
        intent_result: IntentRecognitionResult, 
        context: ConversationContext
    ) -> str:
        """Handle cases where clarification is needed from the user."""
        questions = intent_result.clarification_questions
        
        response = (
            "I'd like to help you create a workflow, but I need a bit more information. "
            "Could you help me understand:\n\n"
        )
        
        for i, question in enumerate(questions, 1):
            response += f"{i}. {question}\n"
        
        response += (
            "\nOnce I have these details, I'll be able to create a detailed workflow plan for you."
        )
        
        return response
    
    async def _present_workflow_plan(
        self, 
        planning_result: WorkflowPlanningResult, 
        context: ConversationContext
    ) -> str:
        """Present the generated workflow plan to the user."""
        plan = planning_result.plan
        
        response = f"I've created a workflow plan called '{plan.name}' for you:\n\n"
        response += f"**Description:** {plan.description}\n\n"
        response += "**Workflow Steps:**\n"
        
        # Sort nodes by dependencies to show logical flow
        sorted_nodes = self._sort_nodes_by_dependencies(plan.nodes)
        
        for i, node in enumerate(sorted_nodes, 1):
            connector = next(
                (c for c in planning_result.selected_connectors if c.name == node.connector_name),
                None
            )
            
            if connector:
                response += f"{i}. **{connector.name.replace('_', ' ').title()}**\n"
                response += f"   - {connector.description}\n"
                
                if node.parameters:
                    response += f"   - Parameters: {self._format_parameters(node.parameters)}\n"
                
                response += "\n"
        
        if plan.triggers:
            response += "**Triggers:**\n"
            for trigger in plan.triggers:
                response += f"- {trigger.type}: {self._format_trigger_config(trigger.config)}\n"
            response += "\n"
        
        response += f"**Reasoning:** {planning_result.reasoning}\n\n"
        response += (
            "Does this workflow plan look good to you? You can:\n"
            "- Approve it by saying 'yes' or 'approve'\n"
            "- Request changes by describing what you'd like modified\n"
            "- Ask questions about any part of the plan"
        )
        
        return response
    
    async def _handle_planning_conversation(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Handle conversation during the planning phase."""
        try:
            # Check if user is providing additional information or requesting a plan
            if any(word in message.lower() for word in ['plan', 'workflow', 'create', 'generate']):
                # Generate new workflow plan with accumulated context
                full_prompt = self._build_full_prompt_from_context(context)
                planning_result = await self._generate_workflow_plan(full_prompt, context)
                
                context.current_plan = planning_result.plan
                context.state = ConversationState.CONFIRMING
                
                return await self._present_workflow_plan(planning_result, context)
            else:
                # Acknowledge the information and ask for more if needed
                return (
                    "Thank you for the additional information. "
                    "Do you have any other requirements or details to add? "
                    "When you're ready, just say 'create the workflow' and I'll generate a plan for you."
                )
                
        except Exception as e:
            logger.error(f"Error in planning conversation: {e}")
            return (
                "I encountered an issue while processing your request. "
                "Could you please rephrase what you'd like the workflow to do?"
            )
    
    async def _handle_confirmation_conversation(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Handle conversation during the confirmation phase."""
        message_lower = message.lower()
        
        # Check for approval
        if any(word in message_lower for word in ['yes', 'approve', 'looks good', 'perfect', 'correct']):
            if context.current_plan:
                context.current_plan.status = WorkflowStatus.ACTIVE
                context.state = ConversationState.APPROVED
                
                # Save the approved plan
                await self._save_workflow_plan(context.current_plan)
                
                return (
                    f"Excellent! I've approved your workflow '{context.current_plan.name}'. "
                    f"The workflow is now active and ready for execution. "
                    f"You can run it manually or set up triggers for automatic execution."
                )
            else:
                return "I don't have a current plan to approve. Let's start over with your workflow request."
        
        # Check for rejection or modification request
        elif any(word in message_lower for word in ['no', 'change', 'modify', 'different', 'wrong']):
            if context.current_plan:
                # Handle modification request
                try:
                    original_plan = context.current_plan
                    modified_plan = await self._apply_plan_modifications(
                        message, 
                        context.current_plan, 
                        context
                    )
                    
                    # Generate explanation of changes
                    explanation = await self._explain_plan_changes(
                        original_plan,
                        modified_plan,
                        message
                    )
                    
                    context.current_plan = modified_plan
                    
                    response = f"I've updated the workflow plan:\n\n{explanation}\n\n"
                    response += await self._present_workflow_plan(
                        WorkflowPlanningResult(
                            plan=modified_plan,
                            selected_connectors=[],  # Will be populated if needed
                            reasoning="Plan modified based on user feedback",
                            confidence=0.8
                        ),
                        context
                    )
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Failed to modify plan: {e}")
                    return (
                        "I had trouble modifying the plan. Could you be more specific about "
                        "what changes you'd like me to make?"
                    )
            else:
                return "I don't have a current plan to modify. Let's start over with your workflow request."
        
        else:
            # Handle questions or unclear responses
            return (
                "I'm not sure how to interpret that. Could you please:\n"
                "- Say 'yes' or 'approve' if the workflow plan looks good\n"
                "- Describe specific changes you'd like me to make\n"
                "- Ask questions about any part of the plan"
            )
    
    async def _apply_plan_modifications(
        self, 
        modification_request: str, 
        current_plan: WorkflowPlan, 
        context: ConversationContext
    ) -> WorkflowPlan:
        """Apply modifications to an existing workflow plan."""
        try:
            # Prepare modification prompt
            messages = [
                {"role": "system", "content": self.modification_prompt},
                {
                    "role": "user",
                    "content": f"""
                    Current Workflow Plan:
                    {json.dumps(current_plan.dict(), indent=2, default=str)}
                    
                    Modification Request:
                    {modification_request}
                    
                    Please modify the workflow plan according to the user's request.
                    """
                }
            ]
            
            # Use function calling for structured modification
            functions = [self._get_workflow_planning_function()]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                functions=functions,
                function_call={"name": "generate_workflow_plan"},
                temperature=0.2,
                max_tokens=2000
            )
            
            # Parse the modified plan
            function_call = response.choices[0].message.function_call
            plan_data = json.loads(function_call.arguments)
            
            # Create modified WorkflowPlan
            modified_plan = self._create_workflow_plan_from_data(
                plan_data, 
                current_plan.user_id
            )
            
            # Preserve original ID and timestamps
            modified_plan.id = current_plan.id
            modified_plan.created_at = current_plan.created_at
            modified_plan.updated_at = datetime.utcnow()
            
            return modified_plan
            
        except Exception as e:
            logger.error(f"Failed to apply plan modifications: {e}")
            raise PlanningError(f"Failed to modify plan: {e}")
    
    async def _explain_plan_changes(
        self, 
        original_plan: WorkflowPlan, 
        modified_plan: WorkflowPlan, 
        modification_request: str
    ) -> str:
        """Generate explanation of changes made to the plan."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant that explains changes made to workflow plans. "
                        "Provide a clear, concise explanation of what was changed and why."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                    Original Plan: {json.dumps(original_plan.dict(), indent=2, default=str)}
                    Modified Plan: {json.dumps(modified_plan.dict(), indent=2, default=str)}
                    User Request: {modification_request}
                    
                    Please explain what changes were made to the workflow plan.
                    """
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to explain plan changes: {e}")
            return "I've updated the workflow plan based on your request."    

    # Database and persistence methods
    
    async def _save_conversation_context(self, context: ConversationContext) -> None:
        """Save conversation context to database."""
        try:
            db = await get_database()
            
            context_data = {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "messages": [msg.dict() for msg in context.messages],
                "current_plan": context.current_plan.dict() if context.current_plan else None,
                "state": context.state.value,
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat()
            }
            
            # Upsert conversation context
            db.table("conversations").upsert(
                context_data,
                on_conflict="session_id"
            ).execute()
            
            logger.debug(f"Saved conversation context for session {context.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save conversation context: {e}")
            # Don't raise error as this is not critical for functionality
    
    async def _load_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Load conversation context from database."""
        try:
            db = await get_database()
            
            result = db.table("conversations").select("*").eq("session_id", session_id).execute()
            
            if not result.data:
                return None
            
            data = result.data[0]
            
            # Reconstruct messages
            messages = [ChatMessage(**msg) for msg in data["messages"]]
            
            # Reconstruct current plan if exists
            current_plan = None
            if data["current_plan"]:
                current_plan = WorkflowPlan(**data["current_plan"])
            
            return ConversationContext(
                session_id=data["session_id"],
                user_id=data["user_id"],
                messages=messages,
                current_plan=current_plan,
                state=ConversationState(data["state"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"])
            )
            
        except Exception as e:
            logger.error(f"Failed to load conversation context: {e}")
            return None
    
    async def _save_workflow_plan(self, plan: WorkflowPlan) -> None:
        """Save workflow plan to database."""
        try:
            db = await get_database()
            
            plan_data = {
                "id": plan.id,
                "user_id": plan.user_id,
                "name": plan.name,
                "description": plan.description,
                "nodes": [node.dict() for node in plan.nodes],
                "edges": [edge.dict() for edge in plan.edges],
                "triggers": [trigger.dict() for trigger in plan.triggers],
                "status": plan.status.value,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat()
            }
            
            # Upsert workflow plan
            db.table("workflows").upsert(
                plan_data,
                on_conflict="id"
            ).execute()
            
            logger.info(f"Saved workflow plan: {plan.name} ({plan.id})")
            
        except Exception as e:
            logger.error(f"Failed to save workflow plan: {e}")
            raise AgentError(f"Failed to save workflow plan: {e}")
    
    # Utility methods
    
    def _create_workflow_plan_from_data(self, plan_data: Dict[str, Any], user_id: str) -> WorkflowPlan:
        """Create WorkflowPlan object from structured data."""
        # Generate unique IDs
        plan_id = str(uuid.uuid4())
        
        # Create nodes
        nodes = []
        for i, node_data in enumerate(plan_data.get("nodes", [])):
            node = WorkflowNode(
                id=str(uuid.uuid4()),
                connector_name=node_data["connector_name"],
                parameters=node_data.get("parameters", {}),
                position=NodePosition(x=i * 200, y=100),  # Simple positioning
                dependencies=node_data.get("dependencies", [])
            )
            nodes.append(node)
        
        # Create edges based on dependencies
        edges = []
        for node in nodes:
            for dep_name in node.dependencies:
                # Find dependency node
                dep_node = next((n for n in nodes if n.connector_name == dep_name), None)
                if dep_node:
                    edge = WorkflowEdge(
                        id=str(uuid.uuid4()),
                        source=dep_node.id,
                        target=node.id
                    )
                    edges.append(edge)
        
        # Create triggers if specified
        triggers = []
        for trigger_data in plan_data.get("triggers", []):
            trigger = Trigger(
                id=str(uuid.uuid4()),
                type=trigger_data["type"],
                config=trigger_data["config"],
                enabled=trigger_data.get("enabled", True)
            )
            triggers.append(trigger)
        
        return WorkflowPlan(
            id=plan_id,
            user_id=user_id,
            name=plan_data.get("name", "Untitled Workflow"),
            description=plan_data.get("description", ""),
            nodes=nodes,
            edges=edges,
            triggers=triggers,
            status=WorkflowStatus.DRAFT
        )
    
    def _sort_nodes_by_dependencies(self, nodes: List[WorkflowNode]) -> List[WorkflowNode]:
        """Sort nodes by their dependencies for logical display order."""
        sorted_nodes = []
        remaining_nodes = nodes.copy()
        
        while remaining_nodes:
            # Find nodes with no unresolved dependencies
            ready_nodes = []
            for node in remaining_nodes:
                resolved_deps = [n.connector_name for n in sorted_nodes]
                if all(dep in resolved_deps or dep == node.connector_name for dep in node.dependencies):
                    ready_nodes.append(node)
            
            if not ready_nodes:
                # If no nodes are ready, just take the first one to avoid infinite loop
                ready_nodes = [remaining_nodes[0]]
            
            # Add ready nodes to sorted list
            for node in ready_nodes:
                sorted_nodes.append(node)
                remaining_nodes.remove(node)
        
        return sorted_nodes
    
    def _format_parameters(self, parameters: Dict[str, Any]) -> str:
        """Format parameters for display."""
        if not parameters:
            return "None"
        
        formatted = []
        for key, value in parameters.items():
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            formatted.append(f"{key}={value}")
        
        return ", ".join(formatted)
    
    def _format_trigger_config(self, config: Dict[str, Any]) -> str:
        """Format trigger configuration for display."""
        if config.get("type") == "schedule":
            return f"Every {config.get('interval', 'hour')}"
        elif config.get("type") == "webhook":
            return f"Webhook URL: {config.get('url', 'TBD')}"
        else:
            return str(config)
    
    def _build_full_prompt_from_context(self, context: ConversationContext) -> str:
        """Build full prompt from conversation context."""
        user_messages = [msg.content for msg in context.messages if msg.role == "user"]
        return " ".join(user_messages)
    
    def _get_workflow_planning_function(self) -> Dict[str, Any]:
        """Get function definition for workflow planning."""
        return {
            "name": "generate_workflow_plan",
            "description": "Generate a structured workflow plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the workflow"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what the workflow does"
                    },
                    "nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "connector_name": {
                                    "type": "string",
                                    "description": "Name of the connector to use"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Parameters for the connector"
                                },
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of connector names this node depends on"
                                }
                            },
                            "required": ["connector_name"]
                        }
                    },
                    "triggers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["schedule", "webhook"]
                                },
                                "config": {
                                    "type": "object",
                                    "description": "Trigger configuration"
                                }
                            },
                            "required": ["type", "config"]
                        }
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation of the workflow design choices"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0-1) in the plan"
                    }
                },
                "required": ["name", "description", "nodes", "reasoning"]
            }
        }
    
    # System prompts
    
    def _load_intent_recognition_prompt(self) -> str:
        """Load system prompt for intent recognition."""
        return """
You are an AI assistant specialized in understanding user intents for workflow automation.
Your task is to analyze user prompts and determine their intent, extract relevant entities, and identify if clarification is needed.

Analyze the user's prompt and respond with a JSON object containing:
- intent: The primary intent (e.g., "workflow_creation", "data_processing", "communication_automation")
- confidence: Confidence score (0-1)
- entities: Extracted entities like services, actions, schedules, etc.
- requires_clarification: Boolean indicating if more information is needed
- clarification_questions: List of specific questions to ask if clarification is needed

Focus on identifying:
1. What the user wants to automate
2. What services/platforms they want to integrate
3. What triggers or schedules they want
4. What data transformations are needed
5. What outputs they expect

If the prompt is vague or missing critical information, set requires_clarification to true and provide specific questions.

Example response:
{
  "intent": "workflow_creation",
  "confidence": 0.8,
  "entities": {
    "services": ["gmail", "google_sheets"],
    "actions": ["send_email", "update_spreadsheet"],
    "schedule": "daily"
  },
  "requires_clarification": false,
  "clarification_questions": []
}
"""
    
    def _load_planning_prompt(self) -> str:
        """Load system prompt for workflow planning."""
        return """
You are an AI workflow planner for PromptFlow AI. Your task is to create detailed, executable workflow plans based on user requests and available connectors.

Guidelines:
1. Analyze the user's request to understand their automation goals
2. Select the most appropriate connectors from the available list
3. Design a logical flow that accomplishes the user's objectives
4. Consider dependencies between steps
5. Include appropriate error handling and validation
6. Suggest reasonable default parameters
7. Explain your reasoning for the design choices

When creating the workflow plan:
- Use only connectors from the provided list
- Ensure proper sequencing of operations
- Include necessary authentication steps
- Consider data flow between connectors
- Add appropriate triggers if mentioned
- Keep the plan focused and efficient

The workflow should be practical, executable, and aligned with the user's stated goals.
Use the generate_workflow_plan function to provide a structured response.
"""
    
    def _load_modification_prompt(self) -> str:
        """Load system prompt for plan modification."""
        return """
You are an AI assistant specialized in modifying existing workflow plans based on user feedback.

Your task is to:
1. Understand the user's modification request
2. Analyze the current workflow plan
3. Apply the requested changes while maintaining workflow integrity
4. Preserve the overall structure where possible
5. Ensure the modified plan still accomplishes the original goals

When modifying plans:
- Make minimal changes that address the user's request
- Maintain proper dependencies and sequencing
- Update parameters as needed
- Add or remove connectors as requested
- Preserve working parts of the original plan
- Ensure the modified plan is still executable

Use the generate_workflow_plan function to provide the modified plan.
"""


# Global agent instance
conversational_agent: Optional[ConversationalAgent] = None


async def get_conversational_agent() -> ConversationalAgent:
    """Dependency to get conversational agent instance."""
    global conversational_agent
    
    if not conversational_agent:
        from app.services.rag import get_rag_retriever
        rag_retriever = await get_rag_retriever()
        conversational_agent = ConversationalAgent(rag_retriever)
        await conversational_agent.initialize()
    
    return conversational_agent


async def init_conversational_agent() -> None:
    """Initialize conversational agent on startup."""
    await get_conversational_agent()